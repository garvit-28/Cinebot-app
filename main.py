import os
import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# =============================
# ENVIRONMENT & CONFIG
# =============================
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY environment variable is required.")

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
# GEMINI GENERATION ENGINE
# =============================
async def generate_gemini_reply(prompt: str) -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return "⚠️ **Configuration Error**: `GEMINI_API_KEY` is not set in Render environment variables."

    system_prompt = (
        "You are CineBot, an expert cinema AI assistant. Provide concise, enthusiastic, "
        "and accurate film recommendations, where-to-watch streaming guides, cast info, and plot breakdowns."
    )

    # 1. Primary Strategy: Direct REST API (Works across all environments without SDK conflicts)
    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]
    last_error = ""

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": f"{system_prompt}\n\nUser Question: {prompt}"}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800}
        }
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                res = await client.post(url, json=payload)
                data = res.json()

                if res.status_code == 200:
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]

                error_obj = data.get("error", {})
                last_error = error_obj.get("message", f"HTTP {res.status_code}")
                
                if "RESOURCE_EXHAUSTED" in last_error or "quota" in last_error.lower():
                    return "⚠️ **Gemini Free Quota Limit Reached**: Your API key has temporarily exceeded its rate/token limit. Please wait 60 seconds or generate a fresh key on [Google AI Studio](https://aistudio.google.com/)."
                if "API_KEY_INVALID" in last_error or "unregistered" in last_error.lower():
                    return "⚠️ **Invalid Gemini Key**: The `GEMINI_API_KEY` provided is invalid. Please verify it in your Render settings."

        except Exception as ex:
            last_error = str(ex)
            continue

    return f"⚠️ **AI Service Notice:** {last_error}"


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


@app.post("/chat")
async def chat_endpoint(payload: ChatRequest):
    # Always returns HTTP 200 with text explanation (never crashes with 500)
    reply_text = await generate_gemini_reply(payload.message)
    return {"reply": reply_text}