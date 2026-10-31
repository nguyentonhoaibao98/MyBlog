import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from blog_auth import LoginGuard, is_admin, sign_out
from blog_storage import AccessDenied, ArticleStore, Conflict, GitHubFiles, LocalFiles, StorageError

PDF = b"%PDF-1.4\n% local test document\n%%EOF"


def create(store, title, public=False, admin=True):
    return store.create(admin=admin, title=title, summary="Useful notes", category="Business Central",
                        content="Article body", public=public, filename="notes.pdf", pdf=PDF)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = ArticleStore(LocalFiles(self.directory.name))

    def tearDown(self):
        self.directory.cleanup()

    def test_private_public_lifecycle_and_reopen(self):
        article = create(self.store, "Private notes")
        self.assertEqual(self.store.list_articles(), [])
        with self.assertRaises(AccessDenied):
            self.store.get_pdf(article["id"])
        reopened = ArticleStore(LocalFiles(self.directory.name))
        self.assertEqual(reopened.get_pdf(article["id"], True)[1], PDF)
        reopened.update(article["id"], admin=True, public=True)
        self.assertEqual(self.store.get_pdf(article["id"])[1], PDF)
        self.store.update(article["id"], admin=True, public=False)
        with self.assertRaises(AccessDenied):
            reopened.get_pdf(article["id"])
        self.store.delete(article["id"], admin=True)
        self.assertEqual(reopened.list_articles(True), [])

    def test_all_writes_require_admin(self):
        with self.assertRaises(AccessDenied):
            create(self.store, "Unauthorized", admin=False)
        article = create(self.store, "Protected")
        with self.assertRaises(AccessDenied):
            self.store.update(article["id"], admin=False, public=True)
        with self.assertRaises(AccessDenied):
            self.store.delete(article["id"], admin=False)
        self.assertFalse(self.store.get_article(article["id"], True)["public"])

    def test_invalid_file_does_not_create_article(self):
        with self.assertRaises(StorageError):
            self.store.create(admin=True, title="Invalid", summary="", category="Business Central",
                              content="", public=False, filename="bad.pdf", pdf=b"<html>not pdf</html>")
        self.assertEqual(self.store.list_articles(True), [])

    def test_public_repository_is_rejected_before_upload(self):
        backend = GitHubFiles("owner/public", "test-token")
        with patch.object(backend, "_request", return_value={"private": False}) as request:
            with self.assertRaisesRegex(StorageError, "PRIVATE"):
                create(ArticleStore(backend), "Hidden")
            self.assertEqual(request.call_count, 1)
            self.assertEqual(request.call_args.args[0], "GET")

    def test_github_commit_retries_against_new_head(self):
        backend = GitHubFiles("owner/private", "test-token")
        snapshots = [
            ({"head": "old", "tree": "old-tree"}, {"version": 1, "articles": []}),
            ({"head": "new", "tree": "new-tree"}, {"version": 1, "articles": [{"id": "concurrent"}]}),
        ]
        calls = []
        def request(method, path, **kwargs):
            calls.append((method, path, kwargs))
            if path == "/git/trees":
                return {"sha": "tree"}
            if path == "/git/commits":
                return {"sha": "commit"}
            if sum(p == "/git/refs/heads/main" for _, p, _ in calls) == 1:
                raise Conflict("Conflict")
            return {}
        with patch.object(backend, "snapshot", side_effect=snapshots), patch.object(backend, "write_blob", return_value="blob") as blob, patch.object(backend, "_request", side_effect=request):
            backend.mutate(lambda m: m["articles"].append({"id": "ours"}), [], "Save")
        final_manifest = blob.call_args.args[0].decode()
        self.assertIn("concurrent", final_manifest)
        self.assertIn("ours", final_manifest)
        self.assertTrue(all(not kwargs["data"]["force"] for _, p, kwargs in calls if "/refs/" in p))


class AuthTests(unittest.TestCase):
    def test_correct_code_expiry_rotation_and_logout(self):
        state = {}
        guard = LoginGuard()
        self.assertFalse(guard.verify("bad", "test-secret", state, now=1000)[0])
        self.assertTrue(guard.verify("test-secret", "test-secret", state, now=1001)[0])
        self.assertTrue(is_admin(state, "test-secret", now=1002))
        self.assertFalse(is_admin(state, "rotated-secret", now=1002))
        self.assertFalse(is_admin(state, "test-secret", now=1001 + 8 * 3600))
        sign_out(state)
        self.assertFalse(is_admin(state, "test-secret", now=1002))

    def test_bruteforce_limit_spans_browser_sessions(self):
        guard = LoginGuard()
        for _ in range(20):
            guard.verify("wrong", "right", {}, now=1000)
        ok, message = guard.verify("right", "right", {}, now=1001)
        self.assertFalse(ok)
        self.assertIn("Too many", message)
        self.assertTrue(guard.verify("right", "right", {}, now=1901)[0])
        self.assertFalse(guard.verify("", "", {}, now=1901)[0])


class StreamlitUITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"ADMIN_CODE": "ui-test-secret", "STORAGE_MODE": "local", "LOCAL_DATA_DIR": self.directory.name})
        self.env.start()
        self.store = ArticleStore(LocalFiles(self.directory.name))
        self.public = create(self.store, "Public tutorial", public=True)
        self.private = create(self.store, "Confidential tutorial")

    def tearDown(self):
        self.env.stop()
        self.directory.cleanup()

    def test_guest_only_sees_public_and_can_open_article(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py")).run()
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label.startswith("Explore the public")).click().run()
        self.assertFalse(app.exception)
        markup = "\n".join(m.value for m in app.markdown)
        self.assertIn("Public tutorial", markup)
        self.assertNotIn("Confidential tutorial", markup)
        next(b for b in app.button if b.label.startswith("Read article")).click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Public tutorial")
        self.assertFalse(any(b.label == "Edit article" for b in app.button))
        app.session_state["selected"] = self.private["id"]
        app.run()
        self.assertIn("unavailable", app.warning[1].value if len(app.warning) > 1 else app.warning[0].value)

    def test_admin_sign_in_edit_and_sign_out(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py")).run()
        app.text_input[0].set_value("ui-test-secret")
        next(b for b in app.button if b.label.startswith("Enter admin")).click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(b.label.startswith("＋ Create") for b in app.button))
        markup = "\n".join(m.value for m in app.markdown)
        self.assertIn("Confidential tutorial", markup)
        app.session_state["selected"] = self.private["id"]
        app.run()
        next(b for b in app.button if b.label == "Edit article").click().run()
        self.assertFalse(app.exception)
        app.text_input[0].set_value("Updated tutorial")
        next(b for b in app.button if b.label == "Save changes").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.store.get_article(self.private["id"], True)["title"], "Updated tutorial")
        next(b for b in app.button if b.label == "Sign out").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(b.label.startswith("Enter admin") for b in app.button))


if __name__ == "__main__":
    unittest.main()

