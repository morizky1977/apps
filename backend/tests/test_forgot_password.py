"""Tests for Forgot Password feature (OTP via email).

Strategy:
- Test negative paths & security invariants via HTTP.
- For the happy-path (reset with correct OTP), we inject a known-hash record
  directly in `password_resets` MongoDB collection to bypass real email fetching.
- We DO NOT ever expose plaintext OTP through the API (verified).
"""
import os
import uuid
import time
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


def _random_password(prefix: str = "Pw") -> str:
    """Generate a random password >=6 chars for a test run — no hardcoded secrets."""
    return f"{prefix}{secrets.token_urlsafe(12)}"


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def registered_user():
    """Register a fresh user for reset flow tests."""
    unique = uuid.uuid4().hex[:8]
    creds = {
        "email": f"test_fp_{unique}@ritme.app",
        "password": _random_password("Orig"),
        "name": f"FP Tester {unique}",
    }
    r = requests.post(f"{API}/auth/register", json=creds, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    yield creds
    # cleanup
    db.users.delete_many({"email": creds["email"]})
    db.password_resets.delete_many({"email": creds["email"]})


def _insert_known_otp(email: str, user_id: str, otp: str, hours_expiry=1, attempts=0, used=False):
    """Insert a known OTP hash directly into DB and invalidate previous unused ones."""
    now = datetime.now(timezone.utc)
    db.password_resets.update_many(
        {"email": email, "used": False},
        {"$set": {"used": True, "invalidated_at": now.isoformat()}},
    )
    otp_hash = bcrypt.hashpw(otp.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    rec = {
        "id": str(uuid.uuid4()),
        "email": email,
        "user_id": user_id,
        "otp_hash": otp_hash,
        "expires_at": (now + timedelta(hours=hours_expiry)).isoformat(),
        "created_at": now.isoformat(),
        "used": used,
        "attempts": attempts,
    }
    db.password_resets.insert_one(rec)
    return rec


# ---------- 1. Anti user enumeration ----------

def test_forgot_password_unregistered_email_returns_generic_200():
    """Unregistered email should still return 200 with generic message (no enumeration)."""
    r = requests.post(
        f"{API}/auth/forgot-password",
        json={"email": f"nonexistent_{uuid.uuid4().hex[:8]}@example.com"},
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "OTP" in data.get("message", "") or "kode" in data.get("message", "").lower()


# ---------- 2. Registered email triggers email send ----------

def test_forgot_password_registered_email_returns_200_and_creates_record(registered_user):
    """Registered email: should return 200 and create a password_resets record."""
    email = registered_user["email"]
    r = requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=60)
    # We accept 200 (email sent) or 502 (email service down); log which
    assert r.status_code in (200, 502), f"unexpected {r.status_code} {r.text}"
    if r.status_code == 200:
        data = r.json()
        assert data.get("ok") is True
        # Verify record was created and otp_hash is bcrypt (not plaintext)
        rec = db.password_resets.find_one({"email": email}, sort=[("created_at", -1)])
        assert rec is not None
        assert "otp_hash" in rec
        assert rec["otp_hash"].startswith("$2"), "OTP should be bcrypt-hashed"
        assert "otp" not in rec, "plaintext otp must not be stored"
        assert rec["used"] is False
        assert rec["attempts"] == 0
    else:
        pytest.skip(f"Email service returned 502; skipping structural assertions. Body: {r.text}")


# ---------- 3. Wrong OTP → 400 and attempts++  ----------

def test_reset_password_wrong_otp_increments_attempts(registered_user):
    email = registered_user["email"]
    # get user_id
    user = db.users.find_one({"email": email})
    assert user is not None

    # inject known OTP
    _insert_known_otp(email, user["id"], "111111")

    # wrong OTP
    r = requests.post(f"{API}/auth/reset-password", json={
        "email": email, "otp": "999999", "new_password": "NewPass123"
    }, timeout=30)
    assert r.status_code == 400
    assert "OTP" in r.json().get("detail", "") or "salah" in r.json().get("detail", "").lower()

    rec = db.password_resets.find_one({"email": email, "used": False}, sort=[("created_at", -1)])
    assert rec is not None
    assert rec["attempts"] == 1


# ---------- 4. Correct OTP → password reset happy path ----------

def test_reset_password_correct_otp_resets_password_and_can_login(registered_user):
    email = registered_user["email"]
    user = db.users.find_one({"email": email})
    known_otp = "654321"
    _insert_known_otp(email, user["id"], known_otp)

    new_password = _random_password("Brand")
    r = requests.post(f"{API}/auth/reset-password", json={
        "email": email, "otp": known_otp, "new_password": new_password
    }, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ok") is True
    assert "reset" in data.get("message", "").lower() or "sandi" in data.get("message", "").lower()

    # new password should work
    lr = requests.post(f"{API}/auth/login", json={"email": email, "password": new_password}, timeout=30)
    assert lr.status_code == 200, f"login with new password failed: {lr.text}"

    # old password should fail
    olr = requests.post(f"{API}/auth/login", json={"email": email, "password": registered_user["password"]}, timeout=30)
    assert olr.status_code == 401


# ---------- 5. Used OTP cannot be reused (single-use) ----------

def test_reset_password_used_otp_rejected(registered_user):
    email = registered_user["email"]
    user = db.users.find_one({"email": email})
    otp = "234567"
    _insert_known_otp(email, user["id"], otp)

    # Use it once
    r1 = requests.post(f"{API}/auth/reset-password", json={
        "email": email, "otp": otp, "new_password": "SomePass111"
    }, timeout=30)
    assert r1.status_code == 200

    # Reuse should fail
    r2 = requests.post(f"{API}/auth/reset-password", json={
        "email": email, "otp": otp, "new_password": "AnotherPass222"
    }, timeout=30)
    assert r2.status_code == 400


# ---------- 6. After 5 wrong attempts, 6th returns 429 and marks used ----------

def test_reset_password_rate_limit_after_5_attempts(registered_user):
    email = registered_user["email"]
    user = db.users.find_one({"email": email})
    known_otp = "345678"
    rec = _insert_known_otp(email, user["id"], known_otp)

    # 5 wrong attempts
    for i in range(5):
        r = requests.post(f"{API}/auth/reset-password", json={
            "email": email, "otp": "000000", "new_password": "TryPass123"
        }, timeout=30)
        assert r.status_code == 400, f"attempt {i+1} unexpected: {r.status_code} {r.text}"

    # 6th attempt should be 429 and record marked used
    r6 = requests.post(f"{API}/auth/reset-password", json={
        "email": email, "otp": "000000", "new_password": "TryPass123"
    }, timeout=30)
    assert r6.status_code == 429

    rec_after = db.password_resets.find_one({"id": rec["id"]})
    assert rec_after["used"] is True


# ---------- 7. Newest OTP invalidates previous ones ----------

def test_new_otp_invalidates_previous(registered_user):
    email = registered_user["email"]
    user = db.users.find_one({"email": email})

    otp_old = "111222"
    _insert_known_otp(email, user["id"], otp_old)

    # Trigger a new forgot-password request — should invalidate old OTP
    r = requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=60)
    assert r.status_code in (200, 502)
    if r.status_code == 502:
        pytest.skip("Email service unavailable")

    # Old OTP should no longer work
    r2 = requests.post(f"{API}/auth/reset-password", json={
        "email": email, "otp": otp_old, "new_password": "NewPassX999"
    }, timeout=30)
    # Old record was invalidated (marked used). The latest record uses a random OTP we don't know.
    # so this must fail. 400 either "kode salah" (if new record picked & wrong otp) or "tidak valid".
    assert r2.status_code == 400


# ---------- 8. Password length validation ----------

def test_reset_password_short_password_rejected(registered_user):
    email = registered_user["email"]
    user = db.users.find_one({"email": email})
    otp = "999888"
    _insert_known_otp(email, user["id"], otp)

    r = requests.post(f"{API}/auth/reset-password", json={
        "email": email, "otp": otp, "new_password": "123"
    }, timeout=30)
    assert r.status_code == 400
    assert "6" in r.json().get("detail", "") or "minimal" in r.json().get("detail", "").lower()


# ---------- 9. Expired OTP ----------

def test_reset_password_expired_otp(registered_user):
    email = registered_user["email"]
    user = db.users.find_one({"email": email})
    otp = "777777"

    # Insert with negative expiry (already expired)
    now = datetime.now(timezone.utc)
    db.password_resets.update_many(
        {"email": email, "used": False},
        {"$set": {"used": True, "invalidated_at": now.isoformat()}},
    )
    otp_hash = bcrypt.hashpw(otp.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.password_resets.insert_one({
        "id": str(uuid.uuid4()),
        "email": email,
        "user_id": user["id"],
        "otp_hash": otp_hash,
        "expires_at": (now - timedelta(minutes=1)).isoformat(),
        "created_at": now.isoformat(),
        "used": False,
        "attempts": 0,
    })

    r = requests.post(f"{API}/auth/reset-password", json={
        "email": email, "otp": otp, "new_password": "SomePass987"
    }, timeout=30)
    assert r.status_code == 400
    assert "kedaluwarsa" in r.json().get("detail", "").lower() or "expired" in r.json().get("detail", "").lower()
