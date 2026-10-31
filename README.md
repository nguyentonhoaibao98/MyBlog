# BC Notes — Streamlit

An English-language Business Central knowledge library, ready for **Streamlit Community Cloud**.

## Features

- Admin access code, expiring server-side sessions, and a shared login attempt limit.
- Public visitors only see articles explicitly marked public.
- Create an article by uploading a PDF (up to 20 MB).
- Edit titles, descriptions, categories, notes, and public/private visibility.
- Read PDFs inside the article.
- Persistent JSON and PDF files in a **private GitHub repository**. **No SQL database is required.**

The public source repository and private content repository are separate. The app refuses a public repository as its data store. Previously shared/downloaded content cannot be recalled. Removed content remains in the private repository's Git history.

## Deploy on Streamlit Community Cloud

1. Create a private GitHub repository, for example `MyBlog-data`, and initialize it with a README. Keep it private.
2. Create a fine-grained GitHub personal access token:
   - Repository access: only `MyBlog-data`.
   - Repository permissions: **Contents → Read and write**.
   - Keep the token in Streamlit Secrets, never in this public repository.
3. In [Streamlit Community Cloud](https://share.streamlit.io/), choose **Create app**:
   - Repository: `nguyentonhoaibao98/MyBlog`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - Python version: **3.12**
4. Open **Advanced settings → Secrets** and supply:

```toml
ADMIN_CODE = "your-admin-access-code"
STORAGE_MODE = "github"
DATA_REPOSITORY = "nguyentonhoaibao98/MyBlog-data"
DATA_BRANCH = "main"
DATA_GITHUB_TOKEN = "your-fine-grained-token"
```

5. Deploy the app. In its sharing settings, allow public visitors.
6. Sign in with your Admin code, upload a PDF, and enable **Visible to public visitors** when you want to publish the article.

Guests can use **Explore the public library** without the Admin code. New articles are private by default.

If storage is not configured, the app opens safely and Admin sees setup instructions. It does not silently fall back to temporary storage on the cloud.

No Node.js build, Cloudflare D1, R2, SQL server, or database migration is required for the Streamlit version.

## Local development

Requires Python 3.12.

```sh
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Create `.streamlit/secrets.toml` locally using `.streamlit/secrets.example.toml`. For file-only local preview:

```toml
ADMIN_CODE = "a-local-test-code"
STORAGE_MODE = "local"
LOCAL_DATA_DIR = ".local-data"
```

Local mode stores JSON/PDF blobs in `.local-data/`. That directory and real secrets are ignored by Git. Do not use local mode for real content on Community Cloud: its filesystem is temporary.

## Storage and privacy

- Metadata is stored in `index.json`, PDF files in `pdf/`.
- PDF and metadata changes are committed together. Non-force updates and conflict retries preserve concurrent edits to other articles.
- The private data repository must be initialized and its branch must exist.
- The GitHub token is used server-side; it is never included in browser links.
- PDFs are only fetched after checking current article visibility.
- GitHub API and repository limits apply; this storage design suits a modest personal knowledge library.
- PDF content is embedded for reading; it is not automatically rewritten into a blog post.
- Old Cloudflare-hosted content is not automatically migrated. Re-upload any existing documents into this Streamlit app.

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests cover authentication, expiry, code rotation, cross-session rate limiting, private/public access, file validation, persistence, rejecting public data repositories, concurrent saves, and Streamlit UI navigation/editing.

Live GitHub storage requires your own private repository and token; automated tests mock its API contract.

## Earlier web version

The existing `app/`, `db/`, `worker/`, and Node.js files belong to the earlier Vinext/Cloudflare version. They are retained for reference and are not imported by `streamlit_app.py`. The previously deployed Sites app remains separate; this change prepares the GitHub app for Streamlit.

See [DEPLOY_STREAMLIT.md](DEPLOY_STREAMLIT.md) for Vietnamese setup instructions.

