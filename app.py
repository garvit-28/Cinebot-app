import requests
import streamlit as st

# =============================
# CONFIG
# =============================
API_BASE = "https://movie-recommender-lvie.onrender.com"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

st.set_page_config(page_title="AI Based Movie Recommendation System", page_icon="🎬", layout="wide")

# =============================
# STYLES
# =============================
st.markdown(
    """
<style>
.block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }
.small-muted { color:#6b7280; font-size: 0.92rem; }
.movie-title { font-size: 0.9rem; line-height: 1.15rem; height: 2.3rem; overflow: hidden; }
.card { border: 1px solid rgba(0,0,0,0.08); border-radius: 16px; padding: 14px; background: rgba(255,255,255,0.7); }
</style>
""",
    unsafe_allow_html=True,
)

# =============================
# STATE
# =============================
if "view" not in st.session_state:
    st.session_state.view = "home"

if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None


def goto_home():
    st.session_state.view = "home"
    st.rerun()


def goto_details(tmdb_id: int):
    st.session_state.view = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)
    st.rerun()


# =============================
# API
# =============================
@st.cache_data(ttl=60)
def api_get_json(path: str, params=None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=20)
        return r.json(), None
    except Exception as e:
        return None, str(e)


# =============================
# UI HELPERS
# =============================
def poster_grid(cards, cols=6, key_prefix="grid"):
    if not cards:
        st.info("No movies found")
        return

    rows = (len(cards) + cols - 1) // cols
    idx = 0

    for _ in range(rows):
        colset = st.columns(cols)
        for c in range(cols):
            if idx >= len(cards):
                break

            m = cards[idx]
            idx += 1

            with colset[c]:
                poster = m.get("poster_url") or ""
                if poster and poster.startswith("http"):
                    st.markdown(
                        f"<img src='{poster}' style='width:100%;border-radius:8px;'>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.write("🎬 No Image")

                tmdb_id = m.get("tmdb_id")
                if tmdb_id:
                    if st.button("Open", key=f"{key_prefix}_{idx}"):
                        goto_details(tmdb_id)

                st.caption(m.get("title", ""))


# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.title("🎬 Menu")

    if st.button("🏠 Home"):
        goto_home()

    category = st.selectbox(
        "Category",
        ["trending", "popular", "top_rated", "now_playing", "upcoming"],
    )

    grid_cols = st.slider("Columns", 4, 8, 5)


# =============================
# HEADER
# =============================
st.title("🎬 Movie Recommendation System")
st.caption("Search → Open → Get AI-based recommendations")

# =============================
# HOME PAGE
# =============================
if st.session_state.view == "home":

    query = st.text_input("Search Movie")

    if query:
        data, err = api_get_json("/tmdb/search", {"query": query})

        if data and data.get("results"):

            movies = data.get("results", [])

            # SUGGESTION DROPDOWN
            options = ["-- Select a movie --"]
            movie_map = {}

            for m in movies[:10]:
                title = m.get("title", "Untitled")
                year = (m.get("release_date") or "")[:4]
                label = f"{title} ({year})" if year else title
                options.append(label)
                movie_map[label] = m.get("id")

            selected = st.selectbox("Suggestions", options)

            if selected != "-- Select a movie --":
                goto_details(movie_map[selected])

            # Poster Grid
            cards = []
            for m in movies:
                cards.append(
                    {
                        "tmdb_id": m.get("id"),
                        "title": m.get("title", "Untitled"),
                        "poster_url": f"{TMDB_IMG}{m['poster_path']}"
                        if m.get("poster_path")
                        else None,
                    }
                )

            poster_grid(cards, cols=grid_cols, key_prefix="search")

        else:
            st.warning("No movies found")

    else:
        data, err = api_get_json("/home", {"category": category})

        if data:
            poster_grid(data, cols=grid_cols, key_prefix="home")
        else:
            st.error(f"Home load failed: {err}")


# =============================
# DETAILS PAGE
# =============================
elif st.session_state.view == "details":

    tmdb_id = st.session_state.selected_tmdb_id

    if st.button("← Back"):
        goto_home()

    data, err = api_get_json(f"/movie/id/{tmdb_id}")

    if not data:
        st.error("Failed to load movie")
        st.stop()

    col1, col2 = st.columns([1, 2])

    with col1:
        poster = data.get("poster_url") or ""
        if poster and poster.startswith("http"):
            st.markdown(
                f"<img src='{poster}' style='width:100%;border-radius:12px;'>",
                unsafe_allow_html=True,
            )
        else:
            st.write("🎬 No Image")

    with col2:
        st.subheader(data.get("title", "Untitled"))
        st.write(data.get("overview", "No overview available."))

    # =============================
    # RECOMMENDATIONS
    # =============================
    st.subheader("🎯 Recommendations")

    bundle, _ = api_get_json(
        "/movie/search",
        {"query": data.get("title"), "tfidf_top_n": 10, "genre_limit": 10},
    )

    if bundle:

        tfidf = bundle.get("tfidf_recommendations", [])
        genre = bundle.get("genre_recommendations", [])

        st.markdown("### 🔎 Similar Movies")
        poster_grid(
            [
                {
                    "tmdb_id": x["tmdb"]["tmdb_id"],
                    "title": x["tmdb"]["title"],
                    "poster_url": x["tmdb"]["poster_url"],
                }
                for x in tfidf
                if x.get("tmdb")
            ],
            cols=grid_cols,
            key_prefix="tfidf",
        )

        st.markdown("### 🎭 Same Genre")
        poster_grid(genre, cols=grid_cols, key_prefix="genre")

        st.markdown("### 🤖 AI Insights")

        if len(tfidf) > 0:
            st.success("AI detected similarity using content-based filtering")

        if len(genre) > 0:
            st.info("AI also used genre-based pattern matching")

    else:
        st.warning("No recommendations available")