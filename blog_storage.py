"""File-backed persistence. Production uses a private GitHub repository, not SQL."""
from __future__ import annotations

import base64
import copy
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

CATEGORIES = ("Business Central", "AL Development", "Power Platform", "Resources & Guides")
MAX_PDF_BYTES = 20 * 1024 * 1024


class StorageError(Exception):
    """Safe, user-facing persistence failure."""


class AccessDenied(StorageError):
    pass


class Conflict(StorageError):
    pass


def validate_article(title, summary, category, content):
    title = title.strip()
    if not 1 <= len(title) <= 200:
        raise StorageError("Title must be between 1 and 200 characters.")
    if category not in CATEGORIES:
        raise StorageError("Please select a valid topic.")
    if len(summary) > 2000 or len(content) > 100000:
        raise StorageError("Description or content is too long.")
    return dict(title=title, summary=summary, category=category, content=content)


class ArticleStore:
    def __init__(self, backend):
        self.backend = backend

    def list_articles(self, admin=False):
        _, manifest = self.backend.snapshot()
        rows = manifest.get("articles", [])
        return sorted(
            [copy.deepcopy(a) for a in rows if admin or a.get("public", False)],
            key=lambda a: a["created"], reverse=True,
        )

    def get_article(self, article_id, admin=False):
        return next((a for a in self.list_articles(admin) if a["id"] == article_id), None)

    def get_pdf(self, article_id, admin=False):
        # Re-read visibility immediately before releasing bytes. No public PDF URLs.
        article = self.get_article(article_id, admin)
        if not article:
            raise AccessDenied("This article is unavailable.")
        return article, self.backend.read_blob(article["pdf_sha"])

    def create(self, *, admin, title, summary, category, content, public, filename, pdf):
        if not admin:
            raise AccessDenied("Admin access is required.")
        fields = validate_article(title, summary, category, content)
        if not pdf.startswith(b"%PDF-") or len(pdf) > MAX_PDF_BYTES:
            raise StorageError("Please select a valid PDF up to 20 MB.")
        # Check private-repository configuration BEFORE uploading any document.
        self.backend.snapshot()
        article_id = str(uuid.uuid4())
        pdf_sha = self.backend.write_blob(pdf)
        article = dict(
            **fields, id=article_id, public=bool(public),
            filename=Path(filename.replace("\\", "/")).name[:200] or "document.pdf",
            pdf_sha=pdf_sha, pdf_path=f"pdf/{article_id}.pdf",
            size=len(pdf), created=datetime.now(timezone.utc).isoformat(),
        )
        def add(manifest):
            manifest["articles"].append(article)
        self.backend.mutate(add, [{"path": article["pdf_path"], "sha": pdf_sha}], "Create article")
        return article

    def update(self, article_id, *, admin, **changes):
        if not admin:
            raise AccessDenied("Admin access is required.")
        def edit(manifest):
            for article in manifest["articles"]:
                if article["id"] == article_id:
                    merged = {**article, **changes}
                    fields = validate_article(*(merged[k] for k in ("title", "summary", "category", "content")))
                    article.update(fields, public=bool(merged["public"]))
                    return
            raise StorageError("Article not found. Refresh the library.")
        self.backend.mutate(edit, [], "Update article")

    def delete(self, article_id, *, admin):
        if not admin:
            raise AccessDenied("Admin access is required.")
        article = self.get_article(article_id, True)
        if not article:
            raise StorageError("Article not found.")
        def remove(manifest):
            manifest["articles"] = [a for a in manifest["articles"] if a["id"] != article_id]
        self.backend.mutate(remove, [{"path": article["pdf_path"], "sha": None}], "Remove article")


class GitHubFiles:
    """Atomic manifest + PDF commits with non-force ref updates and conflict retries."""
    def __init__(self, repository, token, branch="main"):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise StorageError("Set DATA_REPOSITORY to owner/private-repository.")
        if not token:
            raise StorageError("Set DATA_GITHUB_TOKEN in Streamlit Secrets.")
        self.base = f"https://api.github.com/repos/{repository}"
        self.branch = quote(branch, safe="")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _request(self, method, path, *, data=None, raw=False, allow_missing=False):
        headers = dict(self.headers)
        if raw:
            headers["Accept"] = "application/vnd.github.raw+json"
        try:
            response = requests.request(
                method, self.base + path, headers=headers, json=data, timeout=45,
                allow_redirects=False,
            )
        except requests.RequestException:
            raise StorageError("Cannot reach the data repository. Please try again.") from None
        if allow_missing and response.status_code == 404:
            return None
        if response.status_code in (409, 422):
            raise Conflict("The library changed while saving. Please retry.")
        if response.status_code in (401, 403, 404):
            raise StorageError("Check the private data repository and token permissions (Contents: read and write).")
        if not response.ok or response.is_redirect:
            raise StorageError("GitHub storage is unavailable. Please try again later.")
        return response.content if raw else response.json()

    def snapshot(self):
        metadata = self._request("GET", "")
        if not metadata.get("private"):
            raise StorageError("The data repository must be PRIVATE to protect unpublished articles and PDFs.")
        head = self._request("GET", f"/git/ref/heads/{self.branch}", allow_missing=True)
        if head is None:
            raise StorageError("Initialize the private data repository with a README, and check DATA_BRANCH.")
        sha = head["object"]["sha"]
        commit = self._request("GET", f"/git/commits/{sha}")
        raw = self._request("GET", f"/contents/index.json?ref={sha}", raw=True, allow_missing=True)
        try:
            manifest = json.loads(raw) if raw else {"version": 1, "articles": []}
            if manifest.get("version") != 1 or not isinstance(manifest.get("articles"), list):
                raise ValueError()
        except (ValueError, AttributeError):
            raise StorageError("The data manifest is invalid. Restore index.json from repository history.") from None
        return {"head": sha, "tree": commit["tree"]["sha"]}, manifest

    def read_blob(self, sha):
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise StorageError("Invalid document reference.")
        data = self._request("GET", f"/git/blobs/{sha}")
        return base64.b64decode(data["content"])

    def write_blob(self, content):
        result = self._request("POST", "/git/blobs", data={
            "content": base64.b64encode(content).decode("ascii"), "encoding": "base64",
        })
        return result["sha"]

    def mutate(self, change, file_entries, message):
        for attempt in range(3):
            state, manifest = self.snapshot()
            change(manifest)
            index_sha = self.write_blob(json.dumps(manifest, ensure_ascii=False, indent=2).encode())
            tree = self._request("POST", "/git/trees", data={
                "base_tree": state["tree"],
                "tree": [
                    {"path": "index.json", "mode": "100644", "type": "blob", "sha": index_sha},
                    *[{"mode": "100644", "type": "blob", **e} for e in file_entries],
                ],
            })
            commit = self._request("POST", "/git/commits", data={
                "message": message, "tree": tree["sha"], "parents": [state["head"]],
            })
            try:
                self._request("PATCH", f"/git/refs/heads/{self.branch}", data={"sha": commit["sha"], "force": False})
                return
            except Conflict:
                if attempt == 2:
                    raise


class LocalFiles:
    """Explicit local-development mode only; not durable on Community Cloud."""
    _lock = threading.RLock()

    def __init__(self, directory):
        self.root = Path(directory)
        (self.root / "blobs").mkdir(parents=True, exist_ok=True)

    def snapshot(self):
        with self._lock:
            path = self.root / "index.json"
            return None, json.loads(path.read_text("utf-8")) if path.exists() else {"version": 1, "articles": []}

    def write_blob(self, content):
        import hashlib
        sha = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        (self.root / "blobs" / sha).write_bytes(content)
        return sha

    def read_blob(self, sha):
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise StorageError("Invalid document reference.")
        return (self.root / "blobs" / sha).read_bytes()

    def mutate(self, change, file_entries, message):
        with self._lock:
            _, manifest = self.snapshot()
            change(manifest)
            temporary = self.root / f"index-{uuid.uuid4()}.tmp"
            temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
            os.replace(temporary, self.root / "index.json")
