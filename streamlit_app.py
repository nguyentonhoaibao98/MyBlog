"""BC Notes: Streamlit entry point for Community Cloud."""
from __future__ import annotations

import html
import os
from pathlib import Path

import streamlit as st

from blog_auth import LoginGuard, is_admin, sign_out
from blog_storage import ArticleStore, CATEGORIES, GitHubFiles, LocalFiles, StorageError

st.set_page_config(page_title="BC Notes | Knowledge library", page_icon="📖", layout="wide")
st.markdown("""<style>
.block-container{max-width:1220px;padding-top:2.6rem;padding-bottom:2rem}
h1,h2,h3{letter-spacing:-.035em}h1{font-family:Georgia,serif;font-weight:400!important}
[data-testid="stSidebar"]{border-right:1px solid #dfe6d8}
[data-testid="stSidebar"] .block-container{padding-top:2rem}
.brand{font-size:30px;font-weight:750;letter-spacing:-1.5px;margin-bottom:30px}
.brand span{font-weight:400}.brand b{color:#a89a6a}
.eyebrow{font-size:10px;letter-spacing:2px;color:#7e9272;margin:10px 0 20px}
.hero-title{font:normal 62px/1.13 Georgia,serif;color:#294c3c;letter-spacing:-2px;margin:24px 0}
.hero-title em{color:#417c60}.intro{font-size:15px;line-height:1.9;color:#83907b;max-width:470px}
.collection{margin-top:40px;border-top:1px solid #dbe3d2;padding-top:22px;font-size:9px;letter-spacing:2px;color:#96a289}
.book{margin:35px 30px;width:200px;height:245px;transform:rotate(-9deg);background:#245f4d;color:#f6f2dd;border-left:9px solid #174835;border-right:5px solid #dedcc4;border-radius:3px 9px 9px 3px;padding:24px;box-shadow:16px 18px 0 #ded3b7,26px 29px 35px #315b3820}
.book small{font-size:7px;letter-spacing:1.4px}.book strong{display:block;font:normal 34px/1.1 Georgia,serif;margin:30px 0 13px}.book span{font-size:9px;opacity:.7}
.welcome{background:#e9f0e0;border:1px solid #dce5d1;border-radius:12px;padding:29px 32px;margin:20px 0 28px}
.welcome h2{font:normal 30px Georgia,serif;margin:10px 0}.welcome p{color:#7b8f6c;font-size:13px;margin-bottom:0}
.tag{display:inline-block;font-size:10px;background:#eaf0e2;color:#698654;padding:5px 9px;border-radius:4px}
.private{background:#eee9db;color:#93845e}.article-heading{font:normal 23px/1.35 Georgia,serif;margin:14px 0 9px}
.summary{font-size:13px;line-height:1.8;color:#829276}.meta{font-size:10px;color:#9aa68e;margin:17px 0}
.empty{text-align:center;padding:45px 20px}.empty h3{font:normal 27px Georgia,serif}.empty p{font-size:13px;color:#92a084;line-height:1.8}
.about{padding:24px;background:#eeeee1;border:1px solid #e0e3d1;border-radius:9px}.about h3{font:normal 24px/1.4 Georgia,serif}.about p{color:#939b82;font-size:12px;line-height:1.9}
.footer{font-size:10px;color:#9ba78d;border-top:1px solid #dfe5d6;margin-top:45px;padding-top:20px;display:flex;justify-content:space-between}
[data-testid="stMetricValue"]{font-family:Georgia,serif;font-weight:400}
[data-testid="stForm"]{border-color:#dfe5d6;border-radius:10px}
@media(max-width:700px){.block-container{padding-top:1.5rem}.hero-title{font-size:43px}.book{display:none}.welcome{padding:20px}.welcome h2{font-size:25px}}
</style>""", unsafe_allow_html=True)


def setting(name, default=""):
    value = os.environ.get(name)
    if value is not None:
        return value
    try:
        return str(st.secrets.get(name, default))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default


@st.cache_resource
def login_guard():
    return LoginGuard()


def admin():
    return is_admin(st.session_state, setting("ADMIN_CODE"))


def active_admin():
    return admin() and not st.session_state.get("public_preview", False)


def storage():
    mode = setting("STORAGE_MODE", "github")
    if mode == "local":
        return ArticleStore(LocalFiles(setting("LOCAL_DATA_DIR", ".local-data")))
    if mode != "github":
        raise StorageError("Choose STORAGE_MODE = 'github' for deployment or 'local' for local preview.")
    return ArticleStore(GitHubFiles(
        setting("DATA_REPOSITORY"), setting("DATA_GITHUB_TOKEN"), setting("DATA_BRANCH", "main"),
    ))


def escape(value):
    return html.escape(str(value))


def go(page, selected=None):
    st.session_state["page"] = page
    st.session_state.pop("editor", None)
    st.session_state.pop("confirm_delete", None)
    st.session_state["selected"] = selected
    st.rerun()


def notify(message):
    st.session_state["notice"] = message


def brand():
    st.markdown('<div class="brand">▧ bc<span>notes</span><b>.</b></div>', unsafe_allow_html=True)


def login_page():
    brand()
    left, _, right = st.columns([1.15, .15, 1], gap="large")
    with left:
        st.markdown("""<div class="eyebrow">YOUR KNOWLEDGE WORKSPACE</div>
<div class="hero-title">Better knowledge.<br>Greater <em>possibilities.</em></div>
<p class="intro">A home for practical insights, useful resources, and everything Dynamics 365 Business Central.</p>
<div class="book"><small>THE KNOWLEDGE COLLECTION</small><strong>Business<br>Central</strong><span>Notes & perspectives</span><br><br>✳</div>
<div class="collection">01 — DISCOVER &nbsp; · &nbsp; 02 — LEARN &nbsp; · &nbsp; 03 — SHARE</div>""", unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            st.markdown("### 🔐")
            st.caption("WELCOME TO BC NOTES")
            st.header("Unlock your next idea.")
            st.write("Enter your access code to manage your workspace, or keep exploring as a guest.")
            configured = bool(setting("ADMIN_CODE"))
            with st.form("login", clear_on_submit=True):
                code = st.text_input("Admin access code", type="password", max_chars=200)
                submitted = st.form_submit_button("Enter admin workspace →", type="primary", use_container_width=True, disabled=not configured)
                if submitted:
                    ok, message = login_guard().verify(code, setting("ADMIN_CODE"), st.session_state)
                    if ok:
                        st.session_state["public_preview"] = False
                        go("library")
                    st.error(message)
            if not configured:
                st.info("The owner must configure ADMIN_CODE in Streamlit Secrets to enable Admin access.")
            st.caption("or")
            if st.button("Explore the public library ↗", use_container_width=True):
                go("library")
            st.caption("Guests can only see content made public by the Admin.")
            st.divider()
            st.caption("● Every great idea starts with a little curiosity.")


def sidebar():
    with st.sidebar:
        brand()
        st.caption("KNOWLEDGE WORKSPACE")
        category = st.radio("Browse topics", ["All articles", *CATEGORIES], label_visibility="collapsed", key="category")
        st.divider()
        st.markdown("#### Knowledge worth sharing.")
        st.caption("A note you save today could be the answer you need tomorrow.")
        st.divider()
        st.caption("ADMIN WORKSPACE" if active_admin() else "PUBLIC LIBRARY")
        if admin():
            preview = st.toggle("Preview public library", key="public_preview")
            if preview and st.session_state.get("editor") is not None:
                st.session_state.pop("editor", None)
            if st.button("Sign out", use_container_width=True):
                sign_out(st.session_state)
                st.session_state.pop("public_preview", None)
                go("login")
        elif st.button("Admin sign in", use_container_width=True):
            go("login")
        if st.button("Refresh library", use_container_width=True):
            st.rerun()
        return category


def setup_help(message):
    st.warning("The library is waiting for its storage connection.")
    if admin():
        st.info(message)
        st.markdown("""**No SQL is required.**

1. Create a **private** GitHub repository and initialize it with a README.
2. Create a fine-grained GitHub token limited to that repository, with **Contents: Read and write**.
3. In Streamlit **App settings → Secrets**, set the following values:""")
        st.code('ADMIN_CODE = "your-admin-code"\nSTORAGE_MODE = "github"\nDATA_REPOSITORY = "your-name/private-data-repo"\nDATA_BRANCH = "main"\nDATA_GITHUB_TOKEN = "your-token"', language="toml")
        st.caption("The data repository must stay private. Never put the token or Admin code in the public source repository.")
    else:
        st.caption("The owner is connecting this library. Please check back soon.")


def editor(store):
    if not active_admin():
        go("library")
    article_id = st.session_state["editor"]
    old = store.get_article(article_id, admin=admin()) if article_id else None
    if article_id and old is None:
        st.warning("Article not found. It may have been removed.")
        if st.button("Back to library"):
            go("library")
        return
    st.caption("KNOWLEDGE STARTS HERE")
    st.header("Edit article" if old else "Create an article from PDF")
    with st.form("article_editor"):
        uploaded = st.file_uploader("Choose your PDF document · up to 20 MB", type=["pdf"]) if not old else None
        title = st.text_input("Article title", value=old["title"] if old else "", max_chars=200, placeholder="Leave blank to use the PDF filename")
        category = st.selectbox("Topic", CATEGORIES, index=CATEGORIES.index(old["category"]) if old else 0)
        summary = st.text_area("Short description", value=old["summary"] if old else "", max_chars=2000)
        content = st.text_area("Additional content", value=old["content"] if old else "", max_chars=100000, height=220)
        public = st.checkbox("Visible to public visitors", value=old["public"] if old else False)
        st.caption("When enabled, anyone visiting the public library can read this article and its PDF.")
        save = st.form_submit_button("Save changes" if old else "Create article", type="primary")
    if save:
        try:
            # Validate authorization again immediately before the write.
            fields = dict(title=title, summary=summary, category=category, content=content, public=public)
            with st.spinner("Saving article…"):
                if old:
                    store.update(article_id, admin=active_admin(), **fields)
                else:
                    if uploaded is None:
                        raise StorageError("Please choose a PDF document.")
                    fields["title"] = title.strip() or Path(uploaded.name).stem.replace("_", " ")
                    store.create(admin=active_admin(), **fields, filename=uploaded.name, pdf=uploaded.getvalue())
            notify("Article saved.")
            go("library")
        except StorageError as error:
            st.error(str(error))
    if st.button("Cancel"):
        go("library")


def article_page(store, article_id):
    if st.button("← Back to library"):
        go("library")
    article = store.get_article(article_id, admin=active_admin())
    if not article:
        st.warning("This article is unavailable.")
        return
    st.caption(article["category"].upper())
    st.title(article["title"])
    st.caption(f'{article["created"][:10]} · {"Public" if article["public"] else "Private"} · PDF document')
    if article["summary"]:
        st.info(article["summary"])
    if article["content"]:
        st.markdown(article["content"], unsafe_allow_html=False)
    st.subheader("PDF document")
    # Use inline viewer bytes, not a public repository URL or globally cached private data.
    if st.button("Open PDF reader", key=f'reader_{article_id}'):
        st.session_state["reader"] = article_id
    if st.session_state.get("reader") == article_id:
        with st.spinner("Loading document…"):
            latest, pdf = store.get_pdf(article_id, admin=active_admin())
        st.pdf(pdf, height=650)
        st.caption(latest["filename"])
    if active_admin():
        st.divider()
        edit, visibility, delete = st.columns(3)
        if edit.button("Edit article", use_container_width=True):
            st.session_state["editor"] = article_id
            st.rerun()
        if visibility.button("Make private" if article["public"] else "Make public", use_container_width=True):
            store.update(article_id, admin=active_admin(), public=not article["public"])
            notify("Article visibility updated.")
            st.rerun()
        if delete.button("Delete article", use_container_width=True):
            st.session_state["confirm_delete"] = article_id
        if st.session_state.get("confirm_delete") == article_id:
            st.warning("Remove this article and its PDF from the library? GitHub retains previous versions in repository history.")
            confirm, cancel = st.columns(2)
            if confirm.button("Confirm removal", type="primary", use_container_width=True):
                store.delete(article_id, admin=active_admin())
                notify("Article removed from the library.")
                go("library")
            if cancel.button("Cancel removal", use_container_width=True):
                st.session_state.pop("confirm_delete", None)
                st.rerun()


def library():
    category = sidebar()
    if setting("STORAGE_MODE", "github") == "local":
        st.warning("Local preview mode: files on Streamlit Community Cloud are temporary. Configure GitHub storage before adding real content.")
    try:
        store = storage()
        articles = store.list_articles(admin=active_admin())
    except StorageError as error:
        st.title("Knowledge library.")
        setup_help(str(error))
        return
    if "editor" in st.session_state and active_admin():
        editor(store)
        return
    selected = st.session_state.get("selected")
    if selected:
        article_page(store, selected)
        return
    heading, action = st.columns([4, 1.3])
    with heading:
        st.caption("THE KNOWLEDGE COLLECTION")
        st.title("Knowledge library." if category == "All articles" else category)
        st.caption("Small notes. Meaningful progress.")
    if active_admin() and action.button("＋ Create from PDF", type="primary", use_container_width=True):
        st.session_state["editor"] = ""
        st.rerun()
    st.markdown("""<div class="welcome"><div class="eyebrow">OPEN KNOWLEDGE, SHARED GROWTH</div>
<h2>Learn today. Do better tomorrow.</h2><p>Practical articles, thoughtful notes, and useful resources for your next step.</p></div>""", unsafe_allow_html=True)
    total, shared, documents = st.columns(3)
    total.metric("Articles in your library", f"{len(articles):02d}")
    shared.metric("Public articles", f"{sum(bool(a['public']) for a in articles):02d}")
    documents.metric("PDF resources", f"{len(articles):02d}")
    st.divider()
    filters, search = st.columns([1, 2])
    visibility = filters.selectbox("Visibility", ["All articles", "Public", "Private"]) if active_admin() else "Public"
    query = search.text_input("Search articles", placeholder="Search articles, topics, content…").casefold()
    rows = [
        a for a in articles
        if (category == "All articles" or a["category"] == category)
        and (visibility == "All articles" or bool(a["public"]) == (visibility == "Public"))
        and query in " ".join([a["title"], a["summary"], a["content"]]).casefold()
    ]
    main, about = st.columns([3, 1], gap="large")
    with main:
        st.caption(f"{len(rows)} ARTICLES · NEWEST FIRST")
        if not rows:
            st.markdown("""<div class="empty"><h3>A new idea starts here.</h3><p>No articles match this view yet.<br>Try another search, or check back for new shared notes.</p></div>""", unsafe_allow_html=True)
        for article in rows:
            with st.container(border=True):
                st.markdown(f'<span class="tag">{escape(article["category"])}</span> <span class="tag {"private" if not article["public"] else ""}">{"Public" if article["public"] else "Private"}</span><div class="article-heading">{escape(article["title"])}</div><p class="summary">{escape(article["summary"])}</p><div class="meta">{escape(article["created"][:10])} · PDF document</div>', unsafe_allow_html=True)
                if st.button("Read article ↗", key="open_" + article["id"]):
                    go("library", article["id"])
    with about:
        st.markdown("""<div class="about"><div class="eyebrow">ABOUT THIS SPACE</div><h3>Take notes to remember.<br>Share ideas to grow.</h3><p>BC Notes brings together practical knowledge from across the Microsoft Dynamics 365 ecosystem.</p></div>""", unsafe_allow_html=True)
        st.caption("KEEP LEARNING, KEEP GROWING ↗")


if "page" not in st.session_state:
    st.session_state["page"] = "login"
if not admin() and ("admin_until" in st.session_state or "admin_fingerprint" in st.session_state):
    sign_out(st.session_state)
if st.session_state.get("notice"):
    st.success(st.session_state.pop("notice"))
try:
    if st.session_state["page"] == "login":
        login_page()
    else:
        library()
except StorageError as error:
    st.error(str(error))
st.markdown('<div class="footer"><span>© 2026 BC Notes</span><span>Keep learning. Keep sharing. ↗</span></div>', unsafe_allow_html=True)
