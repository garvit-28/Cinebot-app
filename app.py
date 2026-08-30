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
    page_title="CineBot - Next-Gen Film Discovery",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================
# ULTRA-MODERN ADAPTIVE CSS
# =============================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Bebas+Neue&display=swap');

    /* Global Container */
    .main .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 3.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 1400px;
    }

    /* Ambient Hero Header */
    .hero-banner {
        background: radial-gradient(circle at 50% 0%, rgba(229, 9, 20, 0.14) 0%, transparent 70%),
                    var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 18px;
        padding: 2.2rem 1.4rem;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.12);
        backdrop-filter: blur(12px);
    }

    .hero-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 1.6px;
        text-transform: uppercase;
        padding: 5px 14px;
        border-radius: 9999px;
        background: rgba(229, 9, 20, 0.12);
        color: #e50914;
        border: 1px solid rgba(229, 9, 20, 0.35);
        margin-bottom: 0.8rem;
    }

    .hero-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: clamp(2.6rem, 6.5vw, 4.2rem);
        letter-spacing: 2px;
        line-height: 1;
        margin: 0;
        background: linear-gradient(135deg, #e50914 0%, #f59e0b 60%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: clamp(0.85rem, 1.8vw, 1.05rem);
        color: var(--text-color);
        opacity: 0.8;
        font-weight: 500;
        max-width: 620px;
        margin: 0.6rem auto 0 auto;
        line-height: 1.5;
    }

    /* Cinematic Poster Cards */
    [data-testid="stImage"] img {
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.18);
        transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), 
                    box-shadow 0.3s ease, 
                    border-color 0.3s ease;
    }
    [data-testid="stImage"] img:hover {
        transform: translateY(-6px) scale(1.02);
        box-shadow: 0 14px 28px rgba(229, 9, 20, 0.22), 0 0 15px rgba(245, 158, 11, 0.12);
        border-color: #e50914;
    }

    /* Movie Titles */
    .movie-title { 
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.92rem; 
        line-height: 1.3rem; 
        height: 2.6rem; 
        overflow: hidden; 
        font-weight: 700; 
        color: var(--text-color);
        margin-top: 8px; 
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }

    /* Rating Badge */
    .rating-badge { 
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 0.8rem; 
        font-weight: 800; 
        color: #d97706;
        background: rgba(245, 158, 11, 0.14);
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid rgba(245, 158, 11, 0.35);
        margin: 4px 0 8px 0;
    }

    /* Segmented Controls & Pills */
    div[data-testid="stSegmentedControl"] button[aria-checked="true"],
    div[data-testid="stPills"] button[aria-checked="true"] {
        background: linear-gradient(135deg, #e50914 0%, #b80710 100%) !important;
        color: #ffffff !important;
        border-color: #e50914 !important;
        box-shadow: 0 4px 14px rgba(229, 9, 20, 0.35) !important;
        font-weight: 700 !important;
    }

    /* Full-Width Cinema Video Player Frame */
    .video-container {
        position: relative;
        width: 100%;
        max-width: 900px;
        padding-bottom: 56.25%;
        height: 0;
        overflow: hidden;
        border-radius: 14px;
        border: 1px solid rgba(128, 128, 128, 0.22);
        background: #000;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
        margin-top: 0.5rem;
    }
    .video-container iframe {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border: 0;
    }

    /* Clean Chat Messages */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background: var(--secondary-background-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        border-left: 4px solid #e50914 !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: rgba(128, 128, 128, 0.08) !important;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
    }

    /* Mobile Breakpoint */
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
# UTILITIES & OTT LOGO RENDERER
# =============================
def render_image(image_url):
    """Safely render images responsively across Streamlit versions."""
    try:
        st.image(image_url, use_container_width=True)
    except Exception:
        try:
            st.image(image_url, width="stretch")
        except Exception:
            st.image(image_url)


def format_provider_badges(providers_list):
    """Renders streaming platform logos, handling both string & dict API formats."""
    if not providers_list:
        return "<div style='opacity: 0.7; font-size: 0.86rem; padding: 4px 0;'>Check local rights on Netflix, Prime Video, Disney+ Hotstar, or JioCinema.</div>"

    brand_rules = [
        {"keywords": ["netflix"], "icon": "https://cdn.simpleicons.org/netflix/white", "bg": "#E50914"},
        {"keywords": ["prime video", "amazon prime"], "icon": "https://cdn.jsdelivr.net/npm/simple-icons@v10/icons/primevideo.svg", "bg": "#00A8E1"},
        {"keywords": ["amazon video", "amazon"], "icon": "https://cdn.simpleicons.org/amazon/white", "bg": "#FF9900"},
        {"keywords": ["disney", "hotstar"], "icon": "https://cdn.jsdelivr.net/npm/simple-icons@v10/icons/disneyplus.svg", "bg": "#113CCF"},
        {"keywords": ["apple tv", "apple tv plus", "itunes"], "icon": "https://cdn.simpleicons.org/apple/white", "bg": "#1C1C1E"},
        {"keywords": ["jiocinema", "jio cinema", "jio"], "icon": "https://cdn.jsdelivr.net/npm/simple-icons@v10/icons/airplayvideo.svg", "bg": "#E11D48"},
        {"keywords": ["youtube"], "icon": "https://cdn.simpleicons.org/youtube/white", "bg": "#FF0000"},
        {"keywords": ["google play"], "icon": "https://cdn.jsdelivr.net/npm/simple-icons@v10/icons/googleplay.svg", "bg": "#01875F"},
        {"keywords": ["hulu"], "icon": "https://cdn.simpleicons.org/hulu/white", "bg": "#1CE783"},
        {"keywords": ["max", "hbo"], "icon": "https://cdn.simpleicons.org/max/white", "bg": "#002BE7"},
        {"keywords": ["zee5", "zee"], "icon": "https://cdn.simpleicons.org/zdf/white", "bg": "#8230C6"},
        {"keywords": ["sony", "sonyliv", "sony liv"], "icon": "https://cdn.simpleicons.org/sony/white", "bg": "#0085FF"},
    ]

    badges = []
    for item in providers_list:
        if isinstance(item, dict):
            name = item.get("name", "Unknown")
            tmdb_logo = item.get("logo_url")
        else:
            name = str(item)
            tmdb_logo = None

        raw_clean = name.lower().strip()
        matched_rule = next((r for r in brand_rules if any(k in raw_clean for k in r["keywords"])), None)

        bg_color = matched_rule["bg"] if matched_rule else "#1e293b"

        if tmdb_logo and str(tmdb_logo).startswith("http"):
            icon_tag = f'<img src="{tmdb_logo}" width="20" height="20" style="border-radius: 4px; vertical-align: middle; margin-right: 8px; object-fit: cover; display: inline-block;" />'
        elif matched_rule and matched_rule.get("icon"):
            icon_tag = f'<img src="{matched_rule["icon"]}" width="16" height="16" style="vertical-align: middle; margin-right: 8px; filter: brightness(0) invert(1); display: inline-block;" />'
        else:
            icon_tag = '<span style="margin-right: 6px; font-size: 0.85rem;">📺</span>'

        badges.append(
            f"""<span style="
                display: inline-flex;
                align-items: center;
                background-color: {bg_color};
                color: #ffffff !important;
                font-weight: 700;
                font-size: 0.78rem;
                padding: 5px 12px;
                border-radius: 8px;
                margin-right: 8px;
                margin-bottom: 8px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                box-shadow: 0 3px 8px rgba(0, 0, 0, 0.25);
            ">{icon_tag}{name}</span>"""
        )

    return f"<div style='display: flex; flex-wrap: wrap; align-items: center; margin-top: 6px;'>{''.join(badges)}</div>"


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
            "content": "Hi! I am **CineBot** powered by Gemini AI 🎬. Ask for recommendations, streaming availability, or deep plot breakdowns!",
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
# API HELPERS
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
# SIDEBAR NAVIGATION
# =============================
with st.sidebar:
    st.markdown("### 🎬 **Navigation**")
    c1, c2 = st.columns(2)
    with c1:
        st.button("🏠 Home", on_click=goto_home, use_container_width=True)
    with c2:
        st.button("💬 AI Bot", on_click=goto_chat, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 🧠 **Gemini AI Engine**")
    
    model_options = {
        "⚡ Gemini 3.6 Flash (Fastest)": "gemini-3.6-flash",
        "🪶 Gemini 3.6 Lite (Ultra-Low Latency)": "gemini-3.6-lite",
        "🚀 Gemini 2.5 Flash": "gemini-2.5-flash",
        "💡 Gemini 2.0 Flash": "gemini-2.0-flash",
        "💎 Gemini 1.5 Pro (Deep Reasoning)": "gemini-1.5-pro",
    }
    
    selected_model_label = st.selectbox(
        "Active Model",
        options=list(model_options.keys()),
        index=0,
        label_visibility="collapsed",
    )
    active_gemini_model = model_options[selected_model_label]

    st.markdown("---")
    st.markdown("#### 🍿 **Browse Feed**")

    category_map = {
        "🔥 Popular": "popular",
        "⚡ Trending Today": "trending",
        "⭐ Top Rated": "top_rated",
        "🎬 In Theaters": "now_playing",
        "⏳ Upcoming": "upcoming",
    }

    try:
        chosen_cat_label = st.pills(
            "Feed Selection",
            options=list(category_map.keys()),
            default="🔥 Popular",
            label_visibility="collapsed",
        ) or "🔥 Popular"
    except Exception:
        chosen_cat_label = st.selectbox(
            "Feed Selection",
            options=list(category_map.keys()),
            index=0,
            label_visibility="collapsed",
        )

    category = category_map[chosen_cat_label]

    st.markdown("---")
    st.markdown("#### 📐 **Display Density**")

    try:
        grid_cols = st.segmented_control(
            "Desktop Grid Density",
            options=[2, 3, 4, 5],
            default=4,
            label_visibility="collapsed",
            help="Number of posters displayed per row on wide screens",
        ) or 4
    except Exception:
        grid_cols = st.radio(
            "Desktop Grid Density",
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
        "🔍 Discover any movie:",
        placeholder="Type a title like Inception, Oppenheimer, 3 Idiots, or Dune...",
    )

    st.markdown("<p style='font-size: 0.85rem; font-weight: 700; margin: 8px 0 4px 0; opacity: 0.85;'>🎭 Instant Vibe Search:</p>", unsafe_allow_html=True)
    vibe_cols = st.columns(4)
    vibes = [
        ("🧠 Mind-Bending", "Inception"),
        ("🚀 Space Sci-Fi", "Interstellar"),
        ("😂 Feel-Good Comedy", "3 Idiots"),
        ("🔥 Non-Stop Action", "Mad Max Fury Road"),
    ]
    for col, (label, movie_target) in zip(vibe_cols, vibes):
        with col:
            if st.button(label, key=f"vibe_{label}", use_container_width=True):
                set_movie_details(movie_target)
                st.rerun()

    if search_query:
        bundle, _ = api_get_json("/movie/search", {"query": search_query, "tfidf_top_n": 10})
        similar_titles = bundle.get("recommendation_titles", []) if bundle else []

        if similar_titles:
            dropdown_choices = [f"-- Related movies to '{search_query}' --"] + similar_titles
            picked_similar = st.selectbox(
                f"🎯 Quick Jump to Recommendations:",
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
        st.markdown("---")
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
    st.subheader(f"💬 CineBot Assistant ({selected_model_label.split('(')[0].strip()})")
    st.caption("Ask for film recommendations, actor filmographies, streaming availability, or plot breakdowns.")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask CineBot (e.g. 'Best Hindi mystery thrillers', 'Where to watch Inception')..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("CineBot is analyzing..."):
                res, err = api_post_json("/chat", {"message": prompt, "model": active_gemini_model})
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

    poster = data.get("poster_url") if data else None
    if not poster or not str(poster).startswith("http"):
        clean = urllib.parse.quote(f"{movie_title} movie poster")
        poster = f"https://tse2.mm.bing.net/th?q={clean}&w=500&h=750&c=7&rs=1&p=0"

    # Frosted-Glass Hero Header
    st.markdown(
        f"""
        <div style="
            position: relative;
            height: clamp(140px, 24vw, 190px);
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(128, 128, 128, 0.22);
            background: #000;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);
        ">
            <div style="
                position: absolute;
                inset: -20px;
                background-image: url('{poster}');
                background-size: cover;
                background-position: center;
                filter: blur(28px) brightness(0.42);
            "></div>
            <div style="
                position: absolute;
                inset: 0;
                display: flex;
                align-items: center;
                padding-left: 2rem;
                background: linear-gradient(90deg, rgba(0,0,0,0.88) 0%, transparent 100%);
            ">
                <h1 style="color: #ffffff; margin: 0; font-size: clamp(1.6rem, 4vw, 2.6rem); font-weight: 800; letter-spacing: -0.5px;">{movie_title}</h1>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2-Column Responsive Split
    col1, col2 = st.columns([1, 2])

    with col1:
        render_image(poster)

    with col2:
        if data and data.get("rating"):
            st.markdown(f"<div class='rating-badge'>⭐ {round(float(data['rating']), 1)} / 10</div>", unsafe_allow_html=True)
        st.write(data.get("overview", "No overview available.") if data else "")

        providers = data.get("providers", {}) if data else {}
        stream = providers.get("flatrate", [])

        # Safe dictionary deduplication
        combined_rent_buy = providers.get("rent", []) + providers.get("buy", [])
        seen_names = set()
        rent_buy = []
        for item in combined_rent_buy:
            p_name = item.get("name") if isinstance(item, dict) else str(item)
            if p_name not in seen_names:
                seen_names.add(p_name)
                rent_buy.append(item)

        st.markdown("#### 📺 Where to Watch")
        if stream:
            st.markdown(f"**Stream Subscription:**{format_provider_badges(stream)}", unsafe_allow_html=True)
        if rent_buy:
            st.markdown(f"**Rent / Purchase:**{format_provider_badges(rent_buy)}", unsafe_allow_html=True)
        if not stream and not rent_buy:
            st.markdown(format_provider_badges([]), unsafe_allow_html=True)

    # Full-Width Trailer Player
    st.write("")
    st.markdown("#### 🎬 Official Trailer")
    trailer_key = data.get("trailer_key") if data else None

    if trailer_key:
        embed_html = f"""
        <div class="video-container">
            <iframe src="https://www.youtube-nocookie.com/embed/{trailer_key}?rel=0&modestbranding=1" allowfullscreen></iframe>
        </div>
        """
        st.components.v1.html(embed_html, height=520)
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