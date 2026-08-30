import os
import difflib
import httpx
from fastapi import FastAPI, Query
from pydantic import BaseModel
import pandas as pd
import numpy as np
from google import genai
from google.genai import types

app = FastAPI(title="CineBot Recommendation API")

# =============================
# ENVIRONMENT & CONFIG
# =============================
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w780"

# Initialize modern Google GenAI Client
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# =============================
# LOAD LOCAL TF-IDF DATA
# =============================
DATASET_PATH = "movies_processed.csv"
SIMILARITY_PATH = "similarity_matrix.npy"

df = None
similarity = None

try:
    if os.path.exists(DATASET_PATH):
        df = pd.read_csv(DATASET_PATH)
        df["title_clean"] = df["title"].astype(str).str.lower().str.strip()
    if os.path.exists(SIMILARITY_PATH):
        similarity = np.load(SIMILARITY_PATH)
except Exception as e:
    print(f"Warning: Could not load local dataset or similarity matrix: {e}")


# =============================
# TMDB ASYNC HELPERS
# =============================
def img(path):
    return f"{TMDB_IMG}{path}" if path else None


async def tmdb_get(endpoint: str, params: dict = None):
    if not TMDB_API_KEY:
        return {}
    p = {"api_key": TMDB_API_KEY}
    if params:
        p.update(params)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f"{TMDB_BASE}{endpoint}", params=p)
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}


async def fetch_trailer_key(tmdb_id: int):
    """Fetches YouTube trailer key across all languages (Hindi, English, etc.)."""
    if not tmdb_id or tmdb_id <= 0:
        return None
    # No language filter applied to ensure Indian & regional trailers are included
    data = await tmdb_get(f"/movie/{tmdb_id}/videos")
    results = data.get("results", [])

    # 1. Prioritize official YouTube trailer
    for v in results:
        if v.get("site") == "YouTube" and v.get("type") == "Trailer" and v.get("official") is True:
            return v.get("key")
    # 2. Any trailer
    for v in results:
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            return v.get("key")
    # 3. Any YouTube clip / teaser
    for v in results:
        if v.get("site") == "YouTube" and v.get("key"):
            return v.get("key")
    return None


async def fetch_watch_providers(tmdb_id: int):
    """Fetches streaming, rent, and buy providers (Default: IN / US fallback)."""
    if not tmdb_id:
        return {}
    data = await tmdb_get(f"/movie/{tmdb_id}/watch/providers")
    results = data.get("results", {})
    region = results.get("IN") or results.get("US") or {}

    flatrate = [p.get("provider_name") for p in region.get("flatrate", [])]
    rent = [p.get("provider_name") for p in region.get("rent", [])]
    buy = [p.get("provider_name") for p in region.get("buy", [])]

    return {"flatrate": flatrate, "rent": rent, "buy": buy}


# =============================
# BACKEND ROUTES
# =============================
@app.get("/")
def root():
    return {"msg": "Movie Recommender API running"}


@app.get("/home")
async def home_feed(category: str = "popular"):
    endpoint_map = {
        "popular": "/movie/popular",
        "trending": "/trending/movie/day",
        "top_rated": "/movie/top_rated",
        "now_playing": "/movie/now_playing",
        "upcoming": "/movie/upcoming",
    }
    target = endpoint_map.get(category, "/movie/popular")
    data = await tmdb_get(target, {"language": "en-US", "page": 1})
    results = data.get("results", [])

    return [
        {
            "tmdb_id": m.get("id"),
            "title": m.get("title") or "Untitled",
            "poster_url": img(m.get("poster_path")),
            "rating": float(m.get("vote_average", 7.5)),
        }
        for m in results
        if m.get("title")
    ]


@app.get("/tmdb/search")
async def search_tmdb(query: str):
    data = await tmdb_get("/search/movie", {"query": query, "language": "en-US", "page": 1})
    return data


@app.get("/movie/search")
async def search_and_recommend(query: str, tfidf_top_n: int = 10):
    recommendation_titles = []
    tfidf_recommendations = []

    if df is not None and similarity is not None:
        q_clean = query.lower().strip()
        matches = difflib.get_close_matches(q_clean, df["title_clean"].tolist(), n=1, cutoff=0.5)

        if matches:
            idx = df[df["title_clean"] == matches[0]].index[0]
            distances = sorted(list(enumerate(similarity[idx])), reverse=True, key=lambda x: x[1])

            for i in distances[1 : tfidf_top_n + 1]:
                m_title = df.iloc[i[0]]["title"]
                m_id = int(df.iloc[i[0]]["movie_id"]) if "movie_id" in df.columns else None
                recommendation_titles.append(m_title)
                tfidf_recommendations.append(
                    {
                        "title": m_title,
                        "tmdb": {
                            "tmdb_id": m_id,
                            "title": m_title,
                            "poster_url": None,
                            "rating": 7.5,
                        },
                    }
                )

    # Fallback to TMDB recommendations if matrix returns empty
    if not tfidf_recommendations:
        search_res = await tmdb_get("/search/movie", {"query": query})
        first_match = search_res.get("results", [])[0] if search_res.get("results") else None
        if first_match:
            recs = await tmdb_get(f"/movie/{first_match['id']}/recommendations")
            for m in recs.get("results", [])[:tfidf_top_n]:
                recommendation_titles.append(m.get("title"))
                tfidf_recommendations.append(
                    {
                        "title": m.get("title"),
                        "tmdb": {
                            "tmdb_id": m.get("id"),
                            "title": m.get("title"),
                            "poster_url": img(m.get("poster_path")),
                            "rating": float(m.get("vote_average", 7.5)),
                        },
                    }
                )

    return {
        "recommendation_titles": recommendation_titles,
        "tfidf_recommendations": tfidf_recommendations,
    }


@app.get("/movie/detail")
async def movie_detail(title: str = Query(None), tmdb_id: int = Query(None)):
    final_id = tmdb_id

    if not final_id and title:
        search_res = await tmdb_get("/search/movie", {"query": title})
        results = search_res.get("results", [])
        if results:
            final_id = results[0].get("id")

    if not final_id:
        return {
            "title": title or "Unknown",
            "overview": "No movie details found.",
            "poster_url": None,
            "rating": 7.0,
            "providers": {},
            "trailer_key": None,
        }

    data_res = await tmdb_get(f"/movie/{final_id}", {"language": "en-US"})
    providers = await fetch_watch_providers(final_id)
    trailer_key = await fetch_trailer_key(final_id)

    return {
        "tmdb_id": final_id,
        "title": data_res.get("title", title),
        "overview": data_res.get("overview") or "No overview available.",
        "poster_url": img(data_res.get("poster_path")),
        "rating": float(data_res.get("vote_average", 7.5)),
        "providers": providers,
        "trailer_key": trailer_key,
    }


# =============================
# GEMINI CHATBOT ROUTE
# =============================
class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat_with_bot(req: ChatRequest):
    if not GEMINI_API_KEY or ai_client is None:
        return {"reply": "⚠️ Gemini API Key is missing. Please configure GEMINI_API_KEY in Render Environment Variables."}

    system_instruction = (
        "You are CineBot, an intelligent, enthusiastic AI Movie Recommender & Film Companion. "
        "Help users find movies, explain plots without spoilers unless requested, suggest where to stream, "
        "and give tailored suggestions based on their mood or preferences. Format responses cleanly with markdown."
    )

    # Primary model: gemini-3.6-flash; Fallback model: gemini-3.5-flash-lite
    models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
    last_error = None

    for model_name in models_to_try:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=req.message,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_output_tokens=800,
                ),
            )
            if response and response.text:
                return {"reply": response.text}
        except Exception as e:
            last_error = str(e)
            continue

    print(f"Chatbot Error across models: {last_error}")
    return {"reply": f"CineBot encountered an error: {last_error}"}