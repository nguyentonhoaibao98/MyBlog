"""Server-side session validation and a process-wide brute-force limit."""
import hashlib
import hmac
import threading
import time


def fingerprint(code):
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def is_admin(state, code, now=None):
    now = time.time() if now is None else now
    return bool(
        code and state.get("admin_until", 0) > now
        and hmac.compare_digest(str(state.get("admin_fingerprint", "")), fingerprint(code))
    )


def sign_out(state):
    state.pop("admin_until", None)
    state.pop("admin_fingerprint", None)
    state.pop("selected", None)
    state.pop("editor", None)


class LoginGuard:
    def __init__(self):
        self.lock = threading.Lock()
        self.failures = []

    def verify(self, supplied, expected, state, now=None):
        now = time.time() if now is None else now
        if not expected:
            return False, "Admin access has not been configured."
        with self.lock:
            self.failures = [t for t in self.failures if t > now - 900]
            # Shared across browser sessions, so refreshing cannot reset the limit.
            if len(self.failures) >= 20:
                return False, "Too many attempts. Please try again in 15 minutes."
            if not hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")):
                self.failures.append(now)
                return False, "Incorrect access code. Please try again."
            state["admin_until"] = now + 8 * 3600
            state["admin_fingerprint"] = fingerprint(expected)
            return True, ""
