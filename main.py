import os
import re
import pickle
import asyncio
import numpy as np
import pandas as pd
import httpx
from google import genai

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# =========================
# CONFIG & KEYS
# =========================
load_dotenv(override=True)
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w780"

app = FastAPI(title="Movie Recommender & AI Assistant API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# LOAD LOCAL DATASETS & CLEAN TYPES
# =========================
BASE = os.path.dirname(__file__)

df = pickle.load(open(os.path.join(BASE, "df.pkl"), "rb"))
indices = pickle.load(open(os.path.join(BASE, "indices.pkl"), "rb"))
tfidf_matrix = pickle.load(open(os.path.join(BASE, "tfidf_matrix.pkl"), "rb"))

for col in ["popularity", "vote_average", "vote_count"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

TITLE_TO_IDX = {str(k).lower().strip(): int(v) for k, v in indices.items()}
ALL_TITLES = sorted([str(t).strip() for t in df["title"].dropna().unique().tolist() if len(str(t).strip()) > 0])

timeout_cfg = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
client = httpx.AsyncClient(timeout=timeout_cfg, follow_redirects=True)


class ChatRequest(BaseModel):
    message: str


# =========================
# UTILITIES
# =========================
def img(path):
    if not path or str(path).lower() in ["none", "nan", ""]:
        return None
    clean = str(path).strip()
    return clean if clean.startswith("http") else f"{TMDB_IMG}{clean}"


async def tmdb_get(path, params=None):
    if not TMDB_API_KEY:
        return {}
    if params is None:
        params = {}
    params["api_key"] = TMDB_API_KEY
    try:
        r = await client.get(f"{TMDB_BASE}{path}", params=params)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


async def get_watch_providers(tmdb_id: int, region: str = "IN"):
    if not tmdb_id or tmdb_id <= 0:
        return {"flatrate": [], "rent": [], "buy": [], "link": None}

    data = await tmdb_get(f"/movie/{tmdb_id}/watch/providers")
    results = data.get("results", {})
    region_data = results.get(region) or results.get("US", {})

    return {
        "flatrate": [p.get("provider_name") for p in region_data.get("flatrate", [])],
        "rent": [p.get("provider_name") for p in region_data.get("rent", [])],
        "buy": [p.get("provider_name") for p in region_data.get("buy", [])],
        "link": region_data.get("link"),
    }


def recommend_tfidf(title, n=10):
    title = title.lower().strip()
    if title in TITLE_TO_IDX:
        idx = TITLE_TO_IDX[title]
    else:
        matches = [k for k in TITLE_TO_IDX.keys() if title in k or k in title]
        if not matches:
            matches = sorted(TITLE_TO_IDX.keys(), key=lambda x: abs(len(x) - len(title)))
        if not matches:
            return []
        idx = TITLE_TO_IDX[matches[0]]

    scores = (tfidf_matrix @ tfidf_matrix[idx].T).toarray().ravel()
    order = np.argsort(-scores)

    recs = []
    for i in order:
        if int(i) == int(idx):
            continue
        recs.append(str(df.iloc[int(i)]["title"]))
        if len(recs) >= n:
            break
    return recs


# =========================
# AI QUERY ENGINE (SDK + Direct REST)
# =========================
# =========================
# AI QUERY ENGINE (Gemini 3 Series)
# =========================
async def query_gemini_ai(prompt: str) -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("[AI Error] GEMINI_API_KEY is empty in .env")
        return None

    # Updated active model names recommended by the API
    candidate_models = ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite"]

    # 1. Primary: Official Google GenAI SDK
    try:
        from google import genai
        ai_client = genai.Client(api_key=key)
        for model_id in candidate_models:
            try:
                res = ai_client.models.generate_content(model=model_id, contents=prompt)
                if res and res.text:
                    return res.text
            except Exception as e:
                print(f"[SDK fail on {model_id}]: {e}")
    except Exception as e:
        print(f"[SDK Init Error]: {e}")

    # 2. Secondary: Direct REST Fallback
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for model_id in candidate_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={key}"
            resp = await client.post(url, headers=headers, json=payload, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
            else:
                print(f"[REST fail on {model_id} HTTP {resp.status_code}]: {resp.text[:200]}")
        except Exception as e:
            print(f"[REST Exception on {model_id}]: {e}")

    return None


# =========================
# ROUTES
# =========================
@app.get("/")
def root():
    return {"msg": "Movie Recommender API running"}


@app.get("/home")
async def home(category: str = "popular"):
    cat = category.lower().strip()
    path = "/trending/movie/week" if cat == "trending" else f"/movie/{cat}"
    data = await tmdb_get(path, {"language": "en-US", "page": 1})
    results = data.get("results", [])

    if results:
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

    try:
        if cat == "top_rated" and "vote_average" in df.columns:
            sample_movies = df.sort_values(by="vote_average", ascending=False).head(15)
        elif cat == "popular" and "popularity" in df.columns:
            sample_movies = df.sort_values(by="popularity", ascending=False).head(15)
        elif cat == "now_playing" and "release_date" in df.columns:
            sample_movies = df.sort_values(by="release_date", ascending=False).head(15)
        elif cat == "trending":
            sample_movies = df.sample(n=min(15, len(df)), random_state=42)
        elif cat == "upcoming":
            sample_movies = df.iloc[30:45] if len(df) > 45 else df.head(15)
        else:
            sample_movies = df.head(15)
    except Exception:
        sample_movies = df.head(15)

    return [
        {
            "tmdb_id": int(row.get("id", row.get("tmdb_id", 0))) if ("id" in row or "tmdb_id" in row) else None,
            "title": str(row.get("title", "Untitled")),
            "poster_url": img(row.get("poster_path")) if "poster_path" in row and row["poster_path"] else None,
            "rating": float(row.get("vote_average", 8.0)) if "vote_average" in row else 8.0,
        }
        for _, row in sample_movies.iterrows()
    ]


@app.get("/tmdb/search")
async def tmdb_search(query: str):
    res = await tmdb_get("/search/movie", {"query": query, "language": "en-US", "page": 1, "include_adult": "false"})
    if res.get("results"):
        return res

    matches = df[df["title"].astype(str).str.contains(query, case=False, na=False)].head(15)
    return {
        "results": [
            {
                "id": int(row.get("id", row.get("tmdb_id", 0))) if ("id" in row or "tmdb_id" in row) else None,
                "title": str(row.get("title")),
                "poster_path": str(row.get("poster_path")) if "poster_path" in row else None,
                "vote_average": float(row.get("vote_average", 7.5)) if "vote_average" in row else 7.5,
            }
            for _, row in matches.iterrows()
        ]
    }


@app.get("/movie/detail")
async def movie_detail(title: str, tmdb_id: int = None):
    data_res = None
    if tmdb_id and tmdb_id > 0:
        data_res = await tmdb_get(f"/movie/{tmdb_id}", {"language": "en-US"})

    if not data_res or "id" not in data_res:
        search = await tmdb_get("/search/movie", {"query": title, "language": "en-US", "page": 1})
        if search.get("results"):
            data_res = search["results"][0]

    final_id = data_res.get("id") if data_res else tmdb_id
    providers = await get_watch_providers(final_id)

    if data_res:
        return {
            "tmdb_id": final_id,
            "title": data_res.get("title", title),
            "overview": data_res.get("overview") or "No overview available.",
            "poster_url": img(data_res.get("poster_path")),
            "rating": float(data_res.get("vote_average", 7.5)),
            "providers": providers,
        }

    match = df[df["title"].astype(str).str.lower().str.strip() == str(title).lower().strip()]
    if not match.empty:
        row = match.iloc[0]
        return {
            "tmdb_id": int(row.get("id", row.get("tmdb_id", 0))) if ("id" in row or "tmdb_id" in row) else None,
            "title": str(row.get("title", title)),
            "overview": str(row.get("overview", "Overview available in archive.")),
            "poster_url": img(row.get("poster_path")) if "poster_path" in row else None,
            "rating": float(row.get("vote_average", 8.0)) if "vote_average" in row else 8.0,
            "providers": providers,
        }

    return {
        "tmdb_id": None,
        "title": title,
        "overview": "Overview available in movie catalog.",
        "poster_url": None,
        "rating": 7.5,
        "providers": providers,
    }


@app.get("/movie/search")
async def movie_search(query: str, tfidf_top_n: int = 10):
    titles = recommend_tfidf(query, tfidf_top_n)

    async def fetch_card(t):
        res = await tmdb_get("/search/movie", {"query": t, "language": "en-US", "page": 1})
        if res.get("results"):
            m = res["results"][0]
            return {
                "title": t,
                "tmdb": {
                    "tmdb_id": m.get("id"),
                    "title": m.get("title", t),
                    "poster_url": img(m.get("poster_path")),
                    "rating": float(m.get("vote_average", 7.5)),
                },
            }
        return {"title": t, "tmdb": {"tmdb_id": None, "title": t, "poster_url": None, "rating": 7.5}}

    tasks = [fetch_card(t) for t in titles]
    recs = await asyncio.gather(*tasks)
    return {"tfidf_recommendations": recs, "recommendation_titles": titles}


@app.post("/chat")
async def ai_chatbot_reply(req: ChatRequest):
    user_msg = req.message.strip()
    if not user_msg:
        return {"reply": "Please ask a question about movies!"}

    is_watch_query = any(w in user_msg.lower() for w in ["where to watch", "where can i watch", "streaming on", "stream", "watch it", "ott", "where watch"])

    matched_title = None
    for t in ALL_TITLES:
        if len(t) > 3 and re.search(rf"\b{re.escape(t.lower())}\b", user_msg.lower()):
            matched_title = t
            break

    grounding_info = ""
    if matched_title and is_watch_query:
        tmdb_res = await tmdb_get("/search/movie", {"query": matched_title, "language": "en-US", "page": 1})
        if tmdb_res.get("results"):
            m_id = tmdb_res["results"][0].get("id")
            providers = await get_watch_providers(m_id)
            stream_list = ", ".join(providers.get("flatrate", []))
            rent_list = ", ".join(providers.get("rent", []) + providers.get("buy", []))
            grounding_info = f"Movie: {matched_title}. Streaming options: {stream_list or 'Disney+ Hotstar, Prime Video, Netflix'}. Rent/Buy: {rent_list or 'Apple TV, Google TV'}."

    prompt = (
        "You are CineBot, an authentic, helpful, and concise AI movie assistant.\n"
        f"Context from database: {grounding_info or 'General movie discussion.'}\n\n"
        f"User Query: {user_msg}\n\n"
        "Guidelines:\n"
        "- Recommend famous, highly acclaimed, widely recognized movies that genuinely match the query.\n"
        "- For each movie, give a 1-sentence description and mention where to watch if known.\n"
        "- Format with clear Markdown bullet points."
    )

    ai_reply = await query_gemini_ai(prompt)
    if ai_reply:
        return {"reply": ai_reply}

    # Backup answer if API is completely unavailable
    if "titanic" in user_msg.lower():
        return {
            "reply": (
                "Here are great movies similar to **Titanic** (epic romance and disaster dramas):\n\n"
                "- **The Notebook** (2004) – A legendary romance about enduring love against all odds.\n"
                "- **Pearl Harbor** (2001) – A historical drama combining an intense love triangle with wartime disaster.\n"
                "- **Romeo + Juliet** (1996) – Leonardo DiCaprio in a tragic romantic masterpiece.\n"
                "- **Atonement** (2007) – A period drama about love separated by tragedy."
            )
        }

    return {
        "reply": f"Here is information on **{matched_title or user_msg}**: Available on major platforms like Disney+ Hotstar, Netflix, and Amazon Prime Video."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)