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
    page_title="CineBot - Movie Recommender System",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =============================
# THEME-ADAPTIVE CINEMA CSS
# =============================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Bebas+Neue&display=swap');

    /* Global Container */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 1400px;
    }

    /* Hero Banner: Adapts seamlessly to Light & Dark Modes */
    .hero-banner {
        background: radial-gradient(circle at 50% 0%, rgba(229, 9, 20, 0.12) 0%, transparent 75%),
                    var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 16px;
        padding: 2rem 1.2rem;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }

    .hero-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        padding: 4px 12px;
        border-radius: 9999px;
        background: rgba(229, 9, 20, 0.12);
        color: #e50914;
        border: 1px solid rgba(229, 9, 20, 0.3);
        margin-bottom: 0.6rem;
    }

    .hero-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: clamp(2.4rem, 6vw, 3.8rem);
        letter-spacing: 1.5px;
        line-height: 1.1;
        margin: 0;
        background: linear-gradient(135deg, #e50914 0%, #f59e0b 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: clamp(0.85rem, 1.8vw, 1rem);
        color: var(--text-color);
        opacity: 0.75;
        font-weight: 500;
        max-width: 600px;
        margin: 0.5rem auto 0 auto;
        line-height: 1.4;
    }

    /* Poster Card Hover Effects */
    [data-testid="stImage"] img {
        border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    }
    [data-testid="stImage"] img:hover {
        transform: translateY(-5px) scale(1.02);
        box-shadow: 0 10px 25px rgba(229, 9, 20, 0.25);
        border-color: #e50914;
    }

    /* Movie Title */
    .movie-title { 
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.9rem; 
        line-height: 1.25rem; 
        height: 2.5rem; 
        overflow: hidden; 
        font-weight: 700; 
        color: var(--text-color);
        margin-top: 6px; 
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }

    /* Rating Badge */
    .rating-badge { 
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.78rem; 
        font-weight: 700; 
        color: #d97706;
        background: rgba(245, 158, 11, 0.12);
        padding: 2px 7px;
        border-radius: 6px;
        border: 1px solid rgba(245, 158, 11, 0.3);
        margin: 3px 0 6px 0;
    }

    /* Active Segmented Control & Radio Styling */
    div[data-testid="stSegmentedControl"] button[aria-checked="true"],
    div[data-testid="stPills"] button[aria-checked="true"] {
        background: linear-gradient(135deg, #e50914 0%, #b80710 100%) !important;
        color: #ffffff !important;
        border-color: #e50914 !important;
        box-shadow: 0 4px 12px rgba(229, 9, 20, 0.35) !important;
    }

    /* Responsive YouTube Player */
    .video-container {
        position: relative;
        padding-bottom: 56.25%;
        height: 0;
        overflow: hidden;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        background: #000;
    }
    .video-container iframe {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border: 0;
    }

    /* Mobile Adaptations */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        [data-testid="column"] {
            min-width: 140px !important;
            flex: 1 1 45% !important;
            margin-bottom: 0.8rem !important;
        }
    }
    </style>

    <div class="hero-banner">
        <div class="hero-pill">⚡ Powered by Gemini AI & TMDB</div>
        <h1 class="hero-title">🎬 CINEBOT</h1>
        <p class="hero-subtitle">Intelligent Film Discovery, Semantic Search & Instant Streaming Guides</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================
# UTILITIES
# =============================
def render_image(image_url):
    """Safely render images responsively across Streamlit versions."""
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
            "content": "Hi! I am **CineBot** powered by Gemini AI 🎬. Ask for recommendations, streaming availability, or plot breakdowns!",
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
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=15)
        return (r.json(), None) if r.status_code == 200 else (None, f"HTTP {r.status_code}")
    except Exception as e:
        return None, str(e)


def api_post_json(path: str, payload=None):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=45)
        return (r.json(), None) if r.status_code == 200 else (None, f"HTTP {r.status_code}")
    except Exception as e:
        return None, str(e)


# =============================
# RESPONSIVE POSTER GRID
# =============================
def poster_grid(cards, cols=4, key_prefix="grid"):
    if not cards:
        st.info("No movies found.")
        return

    actual_cols = min(cols, 5)
    rows = (len(cards) + actual_cols - 1) // actual_cols
    idx = 0

    for _ in range(rows):
        colset = st.columns(actual_cols)
        for c in range(actual_cols):
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
                    "View Details",
                    key=f"{key_prefix}_{idx}_{title_text}_{t_id}",
                    on_click=set_movie_details,
                    args=(title_text, t_id),
                    use_container_width=True,
                )


# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.markdown("### 🎬 **Navigation**")
    c1, c2 = st.columns(2)
    with c1:
        st.button("🏠 Home", on_click=goto_home, use_container_width=True)
    with c2:
        st.button("💬 AI Bot", on_click=goto_chat, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 🍿 **Browse Catalog**")
    
    category_map = {
        "🔥 Popular": "popular",
        "⚡ Trending Today": "trending",
        "⭐ Top Rated": "top_rated",
        "🎬 In Theaters": "now_playing",
        "⏳ Upcoming": "upcoming",
    }
    
    # Attractive Category Selector (falls back gracefully if pills not supported)
    try:
        chosen_cat_label = st.pills(
            "Select Feed",
            options=list(category_map.keys()),
            default="🔥 Popular",
            label_visibility="collapsed",
        ) or "🔥 Popular"
    except Exception:
        chosen_cat_label = st.selectbox(
            "Select Feed",
            options=list(category_map.keys()),
            index=0,
            label_visibility="collapsed",
        )

    category = category_map[chosen_cat_label]

    st.markdown("---")
    st.markdown("#### 📐 **Poster Density**")
    
    # Segmented Desktop Density Picker
    try:
        grid_cols = st.segmented_control(
            "Desktop Columns",
            options=[2, 3, 4, 5],
            default=4,
            label_visibility="collapsed",
            help="Choose how many movie cards display per row on desktop",
        ) or 4
    except Exception:
        grid_cols = st.radio(
            "Desktop Columns",
            options=[2, 3, 4, 5],
            index=2,
            horizontal=True,
            label_visibility="collapsed",
        )


# =============================
# VIEW 1: HOME BROWSER
# =============================
if st.session_state.view == "home":
    search_query = st.text_input(
        "🔍 Search any movie (e.g. Inception, Avatar, 3 Idiots):",
        placeholder="Type movie name and press Enter...",
    )

    if search_query:
        bundle, _ = api_get_json("/movie/search", {"query": search_query, "tfidf_top_n": 10})
        similar_titles = bundle.get("recommendation_titles", []) if bundle else []

        if similar_titles:
            dropdown_choices = [f"-- Similar movies to '{search_query}' --"] + similar_titles
            picked_similar = st.selectbox(
                f"🎯 Quick Jump to Similar Movies:",
                options=dropdown_choices,
                index=0,
                key="search_similar_dropdown",
            )
            if picked_similar != dropdown_choices[0]:
                st.button(
                    f"🚀 Open '{picked_similar}'",
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
        st.subheader(f"{chosen_cat_label} Movies")
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
    st.caption("Ask anything about films, actors, streaming platforms, or mood-based suggestions.")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask CineBot (e.g. 'Best Hindi horror movies', 'Where to watch Inception')..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("CineBot is thinking..."):
                res, err = api_post_json("/chat", {"message": prompt})
                if res and "reply" in res:
                    bot_reply = res["reply"]
                else:
                    bot_reply = f"⚠️ Connection Error: {err or 'Unable to fetch reply'}"
                st.markdown(bot_reply)

        st.session_state.chat_messages.append({"role": "assistant", "content": bot_reply})


# =============================
# VIEW 3: DETAILS & RECOMMENDATIONS
# =============================
elif st.session_state.view == "details":
    st.button("⬅️ Back to Browse", type="primary", on_click=goto_home, use_container_width=True)
    st.write("")

    selected_title = st.session_state.selected_movie_title
    selected_tmdb_id = st.session_state.selected_tmdb_id

    data, _ = api_get_json("/movie/detail", {"title": selected_title, "tmdb_id": selected_tmdb_id})
    movie_title = data.get("title", selected_title) if data else selected_title

    # Adaptive 2-column layout (stacks cleanly on phones)
    col1, col2 = st.columns([1, 2])

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
            st.caption("Check JustWatch, Netflix, Disney+ Hotstar, or Prime Video for local rights.")

    # Responsive YouTube Player
    st.write("")
    st.markdown("#### 🎬 Official Trailer")
    trailer_key = data.get("trailer_key") if data else None

    if trailer_key:
        embed_html = f"""
        <div class="video-container">
            <iframe src="https://www.youtube-nocookie.com/embed/{trailer_key}?rel=0&modestbranding=1" allowfullscreen></iframe>
        </div>
        """
        st.components.v1.html(embed_html, height=320)
    else:
        st.caption("Direct trailer unavailable. Search trailer on YouTube:")
        trailer_query = urllib.parse.quote(f"{movie_title} official trailer")
        st.link_button(
            f"▶️ Search '{movie_title}' Trailer on YouTube",
            f"https://www.youtube.com/results?search_query={trailer_query}",
            use_container_width=True,
        )

    st.divider()
    st.subheader(f"🎯 More Movies Similar to '{movie_title}'")

    with st.spinner("Finding recommendations..."):
        bundle, _ = api_get_json("/movie/search", {"query": movie_title, "tfidf_top_n": 8})

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