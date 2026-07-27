"""Tests for Reset Password via Security Question feature.

Covers:
- GET /api/auth/security-question
- POST /api/auth/register with optional security_answer
- POST /api/auth/security-answer (authenticated set/update)
- POST /api/auth/reset-password-security (correct/wrong/no-answer/rate-limit/validation)
- Regression: email OTP flow still works (light).
"""
import os
import uuid
import secrets
import pytest
import requests
import bcrypt
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"
mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]

SECURITY_QUESTION_TEXT = "Siapa nama Presiden Indonesia yang sedang berkuasa saat ini dan kalian cintai?"


def _random_password(prefix: str = "Pw") -> str:
    """Generate a random password >=6 chars for a test run — no hardcoded secrets."""
    return f"{prefix}{secrets.token_urlsafe(12)}"


def _register(security_answer=None, password=None):
    unique = uuid.uuid4().hex[:8]
    if password is None:
        password = _random_password("Orig")
    body = {
        "email": f"test_sq_{unique}@ritme.app",
        "password": password,
        "name": f"SQ Tester {unique}",
    }
    if security_answer is not None:
        body["security_answer"] = security_answer
    r = requests.post(f"{API}/auth/register", json=body, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    return body, data["token"], data["user"]


def _cleanup(email):
    db.users.delete_many({"email": email})
    db.password_resets.delete_many({"email": email})
    db.security_reset_attempts.delete_many({"email": email})


# ---------- 1. GET security question ----------
def test_get_security_question_returns_indonesian_text():
    r = requests.get(f"{API}/auth/security-question", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data.get("question") == SECURITY_QUESTION_TEXT


# ---------- 2. Register with/without security_answer ----------
def test_register_without_security_answer_has_flag_false():
    creds, _, user = _register(security_answer=None)
    try:
        assert user["has_security_answer"] is False
        # DB should not have hash
        u = db.users.find_one({"email": creds["email"]})
        assert "security_answer_hash" not in u
    finally:
        _cleanup(creds["email"])


def test_register_with_security_answer_stores_bcrypt_hash():
    creds, _, user = _register(security_answer="Prabowo Subianto")
    try:
        assert user["has_security_answer"] is True
        u = db.users.find_one({"email": creds["email"]})
        assert "security_answer_hash" in u
        assert u["security_answer_hash"].startswith("$2")  # bcrypt
        # no plaintext stored
        assert "security_answer" not in u
    finally:
        _cleanup(creds["email"])


# ---------- 3. POST /auth/security-answer (authenticated) ----------
def test_set_security_answer_authenticated_and_me_reflects():
    creds, token, user = _register(security_answer=None)
    try:
        assert user["has_security_answer"] is False
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.post(f"{API}/auth/security-answer",
                          json={"security_answer": "Prabowo Subianto"},
                          headers=headers, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        # GET /auth/me
        me = requests.get(f"{API}/auth/me", headers=headers, timeout=15)
        assert me.status_code == 200
        assert me.json()["has_security_answer"] is True

        # Update it (idempotent update)
        r2 = requests.post(f"{API}/auth/security-answer",
                           json={"security_answer": "prabowo"},
                           headers=headers, timeout=30)
        assert r2.status_code == 200
    finally:
        _cleanup(creds["email"])


def test_set_security_answer_empty_returns_400():
    creds, token, _ = _register(security_answer=None)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.post(f"{API}/auth/security-answer",
                          json={"security_answer": "   "},
                          headers=headers, timeout=15)
        assert r.status_code == 400
        assert "kosong" in r.json().get("detail", "").lower()
    finally:
        _cleanup(creds["email"])


def test_set_security_answer_requires_auth():
    r = requests.post(f"{API}/auth/security-answer",
                      json={"security_answer": "Prabowo"}, timeout=15)
    assert r.status_code == 401


# ---------- 4. Reset via security question - happy path with normalization ----------
def test_reset_password_security_normalized_answer_succeeds():
    creds, _, _ = _register(security_answer="Prabowo Subianto")
    try:
        # Use messy answer: extra spaces + different case
        new_password = _random_password("Brand")
        r = requests.post(f"{API}/auth/reset-password-security", json={
            "email": creds["email"],
            "security_answer": "  prabowo   SUBIANTO  ",
            "new_password": new_password,
        }, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        # Login with new password works
        lr = requests.post(f"{API}/auth/login", json={
            "email": creds["email"], "password": new_password
        }, timeout=30)
        assert lr.status_code == 200

        # Login with old password fails
        olr = requests.post(f"{API}/auth/login", json={
            "email": creds["email"], "password": creds["password"]
        }, timeout=30)
        assert olr.status_code == 401
    finally:
        _cleanup(creds["email"])


# ---------- 5. Wrong answer returns generic 400 ----------
def test_reset_password_security_wrong_answer_generic_400():
    creds, _, _ = _register(security_answer="Prabowo Subianto")
    try:
        r = requests.post(f"{API}/auth/reset-password-security", json={
            "email": creds["email"],
            "security_answer": "Joko Widodo",
            "new_password": "NewPass1234",
        }, timeout=30)
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert "Email atau jawaban keamanan salah" == detail
    finally:
        _cleanup(creds["email"])


# ---------- 6. Wrong email returns same generic 400 (anti-enumeration) ----------
def test_reset_password_security_unknown_email_generic_400():
    r = requests.post(f"{API}/auth/reset-password-security", json={
        "email": f"nope_{uuid.uuid4().hex[:6]}@example.com",
        "security_answer": "anything",
        "new_password": "NewPass1234",
    }, timeout=30)
    assert r.status_code == 400
    assert r.json().get("detail") == "Email atau jawaban keamanan salah"


# ---------- 7. User without security_answer_hash → same generic 400 ----------
def test_reset_password_security_user_without_answer_generic_400():
    creds, _, _ = _register(security_answer=None)
    try:
        r = requests.post(f"{API}/auth/reset-password-security", json={
            "email": creds["email"],
            "security_answer": "anything",
            "new_password": "NewPass1234",
        }, timeout=30)
        assert r.status_code == 400
        assert r.json().get("detail") == "Email atau jawaban keamanan salah"
    finally:
        _cleanup(creds["email"])


# ---------- 8. Rate limit: 5 failed attempts → 6th 429 ----------
def test_reset_password_security_rate_limit():
    creds, _, _ = _register(security_answer="Prabowo Subianto")
    try:
        for i in range(5):
            r = requests.post(f"{API}/auth/reset-password-security", json={
                "email": creds["email"],
                "security_answer": "wrong-answer",
                "new_password": "NewPass1234",
            }, timeout=30)
            assert r.status_code == 400, f"attempt {i+1}: {r.status_code} {r.text}"

        r6 = requests.post(f"{API}/auth/reset-password-security", json={
            "email": creds["email"],
            "security_answer": "wrong-answer",
            "new_password": "NewPass1234",
        }, timeout=30)
        assert r6.status_code == 429
        assert "1 jam" in r6.json().get("detail", "") or "terlalu" in r6.json().get("detail", "").lower()

        # Even a CORRECT answer is blocked while rate-limited
        r_correct = requests.post(f"{API}/auth/reset-password-security", json={
            "email": creds["email"],
            "security_answer": "Prabowo Subianto",
            "new_password": "NewPass1234",
        }, timeout=30)
        assert r_correct.status_code == 429
    finally:
        _cleanup(creds["email"])


# ---------- 9. Short password rejected ----------
def test_reset_password_security_short_password_400():
    creds, _, _ = _register(security_answer="Prabowo Subianto")
    try:
        r = requests.post(f"{API}/auth/reset-password-security", json={
            "email": creds["email"],
            "security_answer": "Prabowo Subianto",
            "new_password": "abc",
        }, timeout=30)
        assert r.status_code == 400
        assert "6" in r.json().get("detail", "") or "minimal" in r.json().get("detail", "").lower()
    finally:
        _cleanup(creds["email"])


# ---------- 10. Empty answer rejected with specific message ----------
def test_reset_password_security_empty_answer_400():
    creds, _, _ = _register(security_answer="Prabowo Subianto")
    try:
        r = requests.post(f"{API}/auth/reset-password-security", json={
            "email": creds["email"],
            "security_answer": "   ",
            "new_password": "NewPass1234",
        }, timeout=30)
        assert r.status_code == 400
        assert "kosong" in r.json().get("detail", "").lower()
    finally:
        _cleanup(creds["email"])


# ---------- 11. Successful security reset invalidates pending email OTPs ----------
def test_security_reset_invalidates_pending_email_otps():
    creds, _, _ = _register(security_answer="Prabowo Subianto")
    try:
        # Inject a pending OTP directly
        user = db.users.find_one({"email": creds["email"]})
        now = datetime.now(timezone.utc)
        otp_hash = bcrypt.hashpw(b"111111", bcrypt.gensalt()).decode()
        rec_id = str(uuid.uuid4())
        db.password_resets.insert_one({
            "id": rec_id,
            "email": creds["email"],
            "user_id": user["id"],
            "otp_hash": otp_hash,
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "created_at": now.isoformat(),
            "used": False,
            "attempts": 0,
        })

        # Reset via security question
        r = requests.post(f"{API}/auth/reset-password-security", json={
            "email": creds["email"],
            "security_answer": "Prabowo Subianto",
            "new_password": "ANewPass999",
        }, timeout=30)
        assert r.status_code == 200

        # The OTP record should now be used=True
        rec = db.password_resets.find_one({"id": rec_id})
        assert rec["used"] is True
    finally:
        _cleanup(creds["email"])


# ---------- 12. Regression: register/login still returns has_security_answer field ----------
def test_login_returns_has_security_answer_field():
    creds, _, _ = _register(security_answer="Prabowo Subianto")
    try:
        lr = requests.post(f"{API}/auth/login", json={
            "email": creds["email"], "password": creds["password"]
        }, timeout=30)
        assert lr.status_code == 200
        data = lr.json()
        assert data["user"]["has_security_answer"] is True
    finally:
        _cleanup(creds["email"])
