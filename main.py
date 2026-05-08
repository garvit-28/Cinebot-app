import os
import pickle
import numpy as np
import httpx

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# =========================
# ENV
# =========================
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

app = FastAPI(title="Movie Recommender API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# LOAD DATA
# =========================
BASE = os.path.dirname(__file__)

df = pickle.load(open(os.path.join(BASE, "df.pkl"), "rb"))
indices = pickle.load(open(os.path.join(BASE, "indices.pkl"), "rb"))
tfidf_matrix = pickle.load(open(os.path.join(BASE, "tfidf_matrix.pkl"), "rb"))

TITLE_TO_IDX = {str(k).lower().strip(): int(v) for k, v in indices.items()}


# =========================
# UTILS
# =========================
def img(path):
    return f"{TMDB_IMG}{path}" if path else None


async def tmdb_get(path, params=None):
    if params is None:
        params = {}

    params["api_key"] = TMDB_API_KEY

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(f"{TMDB_BASE}{path}", params=params)

    if r.status_code != 200:
        raise Exception(f"TMDB ERROR {r.status_code}: {r.text}")

    return r.json()


# =========================
# ROUTES
# =========================
@app.get("/")
def root():
    return {"msg": "API running"}


@app.get("/tmdb/search")
async def tmdb_search(query: str):
    try:
        return await tmdb_get(
            "/search/movie",
            {
                "query": query,
                "language": "en-US",
                "page": 1,
                "include_adult": "false",
            },
        )
    except Exception as e:
        print("SEARCH ERROR:", e)
        return {"results": []}


@app.get("/movie/id/{tmdb_id}")
async def movie_details(tmdb_id: int):
    try:
        data = await tmdb_get(
            f"/movie/{tmdb_id}",
            {"language": "en-US"},
        )

        return {
            "tmdb_id": data.get("id"),
            "title": data.get("title", "Untitled"),
            "overview": data.get("overview") or "No overview available.",
            "poster_url": img(data.get("poster_path")),
        }

    except Exception as e:
        print("DETAIL ERROR:", e)
        return {
            "tmdb_id": tmdb_id,
            "title": "Movie Details Not Available",
            "overview": "Could not load movie details.",
            "poster_url": None,
        }


# =========================
# TF-IDF RECOMMENDATION
# =========================
def recommend(title, n=10):
    title = title.lower().strip()

    if title in TITLE_TO_IDX:
        idx = TITLE_TO_IDX[title]
    else:
        matches = [k for k in TITLE_TO_IDX.keys() if title in k or k in title]

        if not matches:
            matches = sorted(
                TITLE_TO_IDX.keys(),
                key=lambda x: abs(len(x) - len(title)),
            )

        if not matches:
            return []

        idx = TITLE_TO_IDX[matches[0]]

    scores = (tfidf_matrix @ tfidf_matrix[idx].T).toarray().ravel()
    order = np.argsort(-scores)

    recs = []

    for i in order:
        if int(i) == int(idx):
            continue

        movie_title = str(df.iloc[int(i)]["title"])
        recs.append(movie_title)

        if len(recs) >= n:
            break

    return recs


@app.get("/movie/search")
async def movie_search(
    query: str,
    tfidf_top_n: int = 10,
    genre_limit: int = 10,
):
    titles = recommend(query, tfidf_top_n)

    # fallback if TF-IDF dataset does not contain selected movie
    if not titles:
        fallback = await tmdb_search(query)
        titles = [
            m.get("title")
            for m in fallback.get("results", [])
            if m.get("title")
        ][:tfidf_top_n]

    tfidf_recommendations = []

    for t in titles:
        try:
            res = await tmdb_get(
                "/search/movie",
                {
                    "query": t,
                    "language": "en-US",
                    "page": 1,
                    "include_adult": "false",
                },
            )

            results = res.get("results", [])

            if results:
                m = results[0]
                tfidf_recommendations.append(
                    {
                        "title": t,
                        "tmdb": {
                            "tmdb_id": m.get("id"),
                            "title": m.get("title") or t,
                            "poster_url": img(m.get("poster_path")),
                        },
                    }
                )
            else:
                tfidf_recommendations.append(
                    {
                        "title": t,
                        "tmdb": None,
                    }
                )

        except Exception:
            tfidf_recommendations.append(
                {
                    "title": t,
                    "tmdb": None,
                }
            )

    # simple fallback recommendations from TMDB search
    try:
        res = await tmdb_get(
            "/search/movie",
            {
                "query": query,
                "language": "en-US",
                "page": 1,
                "include_adult": "false",
            },
        )

        genre_recommendations = [
            {
                "tmdb_id": m.get("id"),
                "title": m.get("title") or "Untitled",
                "poster_url": img(m.get("poster_path")),
            }
            for m in res.get("results", [])[:genre_limit]
            if m.get("id")
        ]

    except Exception:
        genre_recommendations = []

    return {
        "tfidf_recommendations": tfidf_recommendations,
        "genre_recommendations": genre_recommendations,
    }