import os
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types

# =============================
# ENVIRONMENT & CONFIG
# =============================
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY environment variable is required.")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required.")

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="CineBot Recommendation & Film Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w780"
TMDB_LOGO_BASE = "https://image.tmdb.org/t/p/w154"
INDIAN_LANGUAGES = {"hi", "ta", "te", "ml", "kn", "bn", "mr", "pa", "gu"}


# =============================
# TMDB API HELPERS
# =============================
async def tmdb_get(endpoint: str, params: dict = None):
    p = params.copy() if params else {}
    p["api_key"] = TMDB_API_KEY
    async with httpx.AsyncClient(timeout=15.0) as http_client:
        r = await http_client.get(f"{TMDB_BASE}{endpoint}", params=p)
        if r.status_code != 200:
            return {}
        return r.json()


def img(path: str):
    return f"{TMDB_IMG}{path}" if path else None


async def fetch_trailer_key(tmdb_id: int):
    if not tmdb_id:
        return None
    data = await tmdb_get(f"/movie/{tmdb_id}/videos")
    for v in data.get("results", []):
        if v.get("site") == "YouTube" and v.get("type") in ["Trailer", "Teaser"]:
            return v.get("key")
    return None


async def fetch_watch_providers(tmdb_id: int, original_language: str = None, origin_country: list = None):
    if not tmdb_id:
        return {}

    data = await tmdb_get(f"/movie/{tmdb_id}/watch/providers")
    results = data.get("results", {})
    if not results:
        return {}

    is_indian = (
        (original_language and original_language.lower() in INDIAN_LANGUAGES)
        or (origin_country and any(c.upper() == "IN" for c in origin_country))
    )

    region = results.get("IN") if is_indian else (results.get("IN") or results.get("US"))
    if not region and results:
        region = results.get("US") or next(iter(results.values()), {})

    def extract(items):
        extracted = []
        for p in items:
            name = p.get("provider_name")
            logo_path = p.get("logo_path")
            if name:
                extracted.append({
                    "name": name,
                    "logo_url": f"{TMDB_LOGO_BASE}{logo_path}" if logo_path else None,
                })
        return extracted

    return {
        "flatrate": extract(region.get("flatrate", [])),
        "rent": extract(region.get("rent", [])),
        "buy": extract(region.get("buy", [])),
    }


# =============================
# ROUTES
# =============================
@app.get("/")
def root():
    return {"message": "CineBot Backend API is running."}


@app.get("/home")
async def home_feed(category: str = Query("popular")):
    valid_categories = ["popular", "top_rated", "now_playing", "upcoming", "trending"]
    if category not in valid_categories:
        category = "popular"

    if category == "trending":
        data = await tmdb_get("/trending/movie/day")
    else:
        data = await tmdb_get(f"/movie/{category}")

    movies = []
    for m in data.get("results", []):
        if m.get("title") and m.get("poster_path"):
            movies.append({
                "tmdb_id": m.get("id"),
                "title": m.get("title"),
                "poster_url": img(m.get("poster_path")),
                "rating": float(m.get("vote_average", 7.5)),
            })
    return movies


@app.get("/tmdb/search")
async def tmdb_search(query: str = Query(...)):
    data = await tmdb_get("/search/movie", {"query": query})
    return data


@app.get("/movie/search")
async def movie_search(query: str = Query(...), tfidf_top_n: int = Query(8)):
    search_res = await tmdb_get("/search/movie", {"query": query})
    results = search_res.get("results", [])
    if not results:
        return {"recommendation_titles": [], "tfidf_recommendations": []}

    target_id = results[0].get("id")
    recs_res = await tmdb_get(f"/movie/{target_id}/recommendations")
    recs_list = recs_res.get("results", [])

    if not recs_list:
        similar_res = await tmdb_get(f"/movie/{target_id}/similar")
        recs_list = similar_res.get("results", [])

    titles = []
    tfidf_recs = []
    for r in recs_list[:tfidf_top_n]:
        t = r.get("title")
        if t:
            titles.append(t)
            tfidf_recs.append({
                "title": t,
                "tmdb": {
                    "tmdb_id": r.get("id"),
                    "title": t,
                    "poster_url": img(r.get("poster_path")),
                    "rating": float(r.get("vote_average", 7.5)),
                },
            })

    return {
        "recommendation_titles": titles,
        "tfidf_recommendations": tfidf_recs,
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

    orig_lang = data_res.get("original_language", "")
    prod_countries = [c.get("iso_3166_1", "") for c in data_res.get("production_countries", [])]

    providers = await fetch_watch_providers(
        tmdb_id=final_id,
        original_language=orig_lang,
        origin_country=prod_countries,
    )
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


class ChatRequest(BaseModel):
    message: str
    model: str = "gemini-3.6-flash"


@app.post("/chat")
async def chat_endpoint(payload: ChatRequest):
    chosen_model = payload.model or "gemini-3.6-flash"
    try:
        sys_instruction = (
            "You are CineBot, an expert cinema AI assistant. Provide concise, enthusiastic, "
            "and accurate film recommendations, where-to-watch streaming guides, cast info, and plot breakdowns."
        )
        response = client.models.generate_content(
            model=chosen_model,
            contents=payload.message,
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                temperature=0.7,
            ),
        )
        return {"reply": response.text, "model_used": chosen_model}
    except Exception as primary_error:
        fallback_models = ["gemini-3.6-lite", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        for fb in fallback_models:
            if fb == chosen_model:
                continue
            try:
                response = client.models.generate_content(
                    model=fb,
                    contents=payload.message,
                    config=types.GenerateContentConfig(
                        system_instruction="You are CineBot, an expert cinema AI assistant.",
                        temperature=0.7,
                    ),
                )
                return {"reply": response.text, "model_used": f"{fb} (fallback)"}
            except Exception:
                continue
        
        print(f"Chat error across all models: {primary_error}")
        raise HTTPException(status_code=500, detail=str(primary_error))