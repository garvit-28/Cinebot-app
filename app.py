import os
import urllib.parse
import requests
import streamlit as st

# =============================
# CONFIG & SECRETS
# =============================
API_BASE = st.secrets.get("API_BASE", os.getenv("API_BASE", "http://127.0.0.1:8000"))
TMDB_IMG = "https://image.tmdb.org/t/p/w780"

st.set_page_config(
    page_title="Movie Recommender System",
    page_icon="📽️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 4.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px;
    }
    h1 {
        margin-top: 0.5rem !important;
        padding-top: 0rem !important;
        margin-bottom: 0.75rem !important;
    }
    .movie-title { 
        font-size: 0.95rem; 
        line-height: 1.25rem; 
        height: 2.5rem; 
        overflow: hidden; 
        font-weight: 600; 
        margin-top: 6px; 
    }
    .rating-badge { 
        font-size: 0.85rem; 
        font-weight: 600; 
        color: #f59e0b; 
        margin-top: 2px; 
        margin-bottom: 4px; 
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================
# UTILITIES
# =============================
def render_image(image_url):
    """Safely render images across both new and legacy Streamlit versions."""
    try:
        st.image(image_url, use_container_width=True)
    except TypeError:
        st.image(image_url, use_column_width=True)


# =============================
# STATE MANAGEMENT
# =============================
if "view" not in st.session_state:
    st.session_state.view = "home"

if "selected_movie_title" not in st.session_state:
    st.session_state.selected_movie_title = None

if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": "Hi! I am **CineBot** powered by Gemini AI 🎬. Ask for recommendations, streaming availability (*e.g., 'Avatar where can I watch it'*), or plot breakdowns!",
        }
    ]


def set_movie_details(title, tmdb_id=None):
    st.session_state.selected_movie_title = str(title).strip()
    st.session_state.selected_tmdb_id = tmdb_id
    st.session_state.view = "details"


def goto_home():
    st.session_state.view = "home"
    st.session_state.selected_movie_title = None
    st.session_state.selected_tmdb_id = None


def goto_chat():
    st.session_state.view = "chatbot"


# =============================
# API UTILITIES
# =============================
def api_get_json(path: str, params=None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
        return (r.json(), None) if r.status_code == 200 else (None, f"HTTP {r.status_code}")
    except Exception as e:
        return None, str(e)


def api_post_json(path: str, payload=None):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=15)
        return (r.json(), None) if r.status_code == 200 else (None, f"HTTP {r.status_code}")
    except Exception as e:
        return None, str(e)


# =============================
# POSTER GRID COMPONENT
# =============================
def poster_grid(cards, cols=5, key_prefix="grid"):
    if not cards:
        st.info("No movies found.")
        return

    rows = (len(cards) + cols - 1) // cols
    idx = 0
    for _ in range(rows):
        colset = st.columns(cols)
        for c in range(cols):
            if idx >= len(cards):
                break
            movie_item = cards[idx]
            idx += 1
            with colset[c]:
                poster = movie_item.get("poster_url")
                title_text = str(movie_item.get("title", "Untitled")).strip()
                t_id = movie_item.get("tmdb_id")

                if not poster or not str(poster).startswith("http"):
                    clean = urllib.parse.quote(f"{title_text} movie poster")
                    poster = f"https://tse2.mm.bing.net/th?q={clean}&w=500&h=750&c=7&rs=1&p=0"

                render_image(poster)
                st.markdown(f"<div class='movie-title'>{title_text}</div>", unsafe_allow_html=True)
                if movie_item.get("rating"):
                    st.markdown(
                        f"<div class='rating-badge'>⭐ {round(float(movie_item.get('rating')), 1)} / 10</div>",
                        unsafe_allow_html=True,
                    )

                st.button(
                    "Details",
                    key=f"{key_prefix}_{idx}_{title_text}_{t_id}",
                    on_click=set_movie_details,
                    args=(title_text, t_id),
                    use_container_width=True,
                )


# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.title("🎬 Navigation")
    c1, c2 = st.columns(2)
    with c1:
        st.button("🏠 Home", on_click=goto_home, use_container_width=True)
    with c2:
        st.button("💬 AI Bot", on_click=goto_chat, use_container_width=True)

    st.markdown("---")
    category = st.selectbox(
        "Browse Category",
        ["popular", "trending", "top_rated", "now_playing", "upcoming"],
    )

    grid_cols = st.slider("Grid Columns", 4, 6, 5)


# =============================
# PERSISTENT TITLE
# =============================
st.title("🎬 Movie Recommendation System")


# =============================
# VIEW 1: HOME BROWSER
# =============================
if st.session_state.view == "home":
    search_query = st.text_input(
        "🔍 Search any movie (e.g. Inception, Avatar, Titanic, The Dark Knight):",
        placeholder="Type movie name and press Enter...",
    )

    if search_query:
        bundle, _ = api_get_json("/movie/search", {"query": search_query, "tfidf_top_n": 10})
        similar_titles = bundle.get("recommendation_titles", []) if bundle else []

        if similar_titles:
            dropdown_choices = [f"-- Similar movies to '{search_query}' (Click to view) --"] + similar_titles
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                picked_similar = st.selectbox(
                    f"🎯 Movies Similar to '{search_query}':",
                    options=dropdown_choices,
                    index=0,
                    key="search_similar_dropdown",
                )
            with col_btn:
                st.write("")
                st.write("")
                if picked_similar != dropdown_choices[0]:
                    st.button(
                        "🚀 Open Selected",
                        type="primary",
                        on_click=set_movie_details,
                        args=(picked_similar,),
                        use_container_width=True,
                    )

        st.markdown("---")
        st.subheader(f"Search Results for *'{search_query}'*")
        data, _ = api_get_json("/tmdb/search", {"query": search_query})
        if data and data.get("results"):
            movies = [
                {
                    "tmdb_id": m.get("id"),
                    "title": m.get("title") or "Untitled",
                    "poster_url": f"{TMDB_IMG}{m['poster_path']}" if m.get("poster_path") else None,
                    "rating": float(m.get("vote_average", 7.5)),
                }
                for m in data.get("results", [])
                if m.get("title")
            ]
            poster_grid(movies, cols=grid_cols, key_prefix="search_results")
        else:
            st.warning(f"No results found for '{search_query}'.")

    else:
        st.subheader(f"{category.replace('_', ' ').title()} Movies")
        data, err = api_get_json("/home", {"category": category})
        if data:
            poster_grid(data, cols=grid_cols, key_prefix=f"home_{category}")
        else:
            st.error(f"Failed to load catalog: {err}")


# =============================
# VIEW 2: AI CHATBOT
# =============================
elif st.session_state.view == "chatbot":
    st.subheader("💬 CineBot: AI Movie Assistant")
    st.caption("Ask anything about films, actors, where to stream, or custom recommendations.")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask CineBot (e.g. 'Avatar where can I watch it', 'Best Sci-Fi movies')..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("CineBot is thinking..."):
                res, _ = api_post_json("/chat", {"message": prompt})
                bot_reply = res.get("reply") if res else "Could not connect to CineBot service."
                st.markdown(bot_reply)

        st.session_state.chat_messages.append({"role": "assistant", "content": bot_reply})


# =============================
# VIEW 3: DETAILS & RECOMMENDATIONS
# =============================
elif st.session_state.view == "details":
    nav_col1, _ = st.columns([1.5, 4.5])
    with nav_col1:
        st.button("⬅️ Back to Browse", type="primary", on_click=goto_home, use_container_width=True)

    st.write("")

    selected_title = st.session_state.selected_movie_title
    selected_tmdb_id = st.session_state.selected_tmdb_id

    data, _ = api_get_json("/movie/detail", {"title": selected_title, "tmdb_id": selected_tmdb_id})
    movie_title = data.get("title", selected_title) if data else selected_title

    col1, col2 = st.columns([1, 2.5])

    with col1:
        poster = data.get("poster_url") if data else None
        if not poster or not str(poster).startswith("http"):
            clean = urllib.parse.quote(f"{movie_title} movie poster")
            poster = f"https://tse2.mm.bing.net/th?q={clean}&w=500&h=750&c=7&rs=1&p=0"
        render_image(poster)

    with col2:
        st.header(movie_title)
        if data and data.get("rating"):
            st.markdown(f"⭐ **Rating:** `{round(float(data['rating']), 1)} / 10`")
        st.write(data.get("overview", "No overview available.") if data else "")

        providers = data.get("providers", {}) if data else {}
        stream = providers.get("flatrate", [])
        rent_buy = list(set(providers.get("rent", []) + providers.get("buy", [])))

        st.markdown("#### 📺 Where to Watch")
        if stream:
            st.success(f"**Stream On:** {', '.join(stream)}")
        if rent_buy:
            st.info(f"**Rent / Buy:** {', '.join(rent_buy)}")
        if not stream and not rent_buy:
            st.caption("Check JustWatch, Netflix, Disney+ Hotstar, or Prime Video for regional licenses.")

    # In-Page Official Trailer Player (Zero Redirection)
    st.write("")
    st.markdown("#### 🎬 Official Trailer")
    trailer_key = data.get("trailer_key") if data else None

    if trailer_key:
        embed_url = f"https://www.youtube-nocookie.com/embed/{trailer_key}?rel=0&modestbranding=1"
        st.components.v1.iframe(src=embed_url, height=450, scrolling=False)
    else:
        st.info("Trailer is currently not available for this title.")

    st.divider()
    st.subheader(f"🎯 More Movies Similar to '{movie_title}'")

    with st.spinner("Finding recommendations..."):
        bundle, _ = api_get_json("/movie/search", {"query": movie_title, "tfidf_top_n": 10})

    if bundle and bundle.get("tfidf_recommendations"):
        cards = [
            {
                "tmdb_id": r.get("tmdb", {}).get("tmdb_id"),
                "title": r.get("tmdb", {}).get("title") or r.get("title"),
                "poster_url": r.get("tmdb", {}).get("poster_url"),
                "rating": r.get("tmdb", {}).get("rating", 7.5),
            }
            for r in bundle["tfidf_recommendations"]
        ]
        poster_grid(cards, cols=grid_cols, key_prefix="recs")
    else:
        st.warning("No recommendations available for this title.")