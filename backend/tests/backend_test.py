"""Regression tests for Ritme (Kerja Rutin) backend.

Covers:
- Auth: register/login/me
- Task CRUD
- Weekly evaluation (stats + AI insight)
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fall back to reading frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"


# ---------- Fixtures ----------

@pytest.fixture(scope="session")
def user_creds():
    unique = uuid.uuid4().hex[:8]
    return {
        "email": f"regtest_{unique}@ritme.app",
        "password": "testing123",
        "name": f"Reg Tester {unique}",
    }


@pytest.fixture(scope="session")
def auth(user_creds):
    """Register a fresh user and return {token, user, headers}."""
    r = requests.post(f"{API}/auth/register", json=user_creds, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and "user" in data
    return {
        "token": data["token"],
        "user": data["user"],
        "headers": {"Authorization": f"Bearer {data['token']}"},
    }


@pytest.fixture(scope="session")
def created_task_ids():
    return []


# ---------- Auth Tests ----------

class TestAuth:
    def test_register_returns_token_and_user(self, auth, user_creds):
        assert auth["user"]["email"] == user_creds["email"].lower()
        assert auth["user"]["name"] == user_creds["name"]
        assert isinstance(auth["token"], str) and len(auth["token"]) > 20

    def test_register_duplicate_email_returns_400(self, user_creds):
        r = requests.post(f"{API}/auth/register", json=user_creds, timeout=30)
        assert r.status_code == 400
        assert "detail" in r.json()

    def test_login_success(self, user_creds):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": user_creds["email"], "password": user_creds["password"]},
            timeout=30,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["user"]["email"] == user_creds["email"].lower()
        assert body["token"]

    def test_login_wrong_password_401(self, user_creds):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": user_creds["email"], "password": "wrongpass"},
            timeout=30,
        )
        assert r.status_code == 401

    def test_me_returns_profile(self, auth, user_creds):
        r = requests.get(f"{API}/auth/me", headers=auth["headers"], timeout=30)
        assert r.status_code == 200
        assert r.json()["email"] == user_creds["email"].lower()

    def test_me_without_token_401(self):
        r = requests.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 401


# ---------- Task CRUD ----------

def _today_iso():
    from datetime import date
    return date.today().isoformat()


class TestTasks:
    def test_create_task(self, auth, created_task_ids):
        payload = {
            "title": "TEST_Regression task 1",
            "category": "kerja",
            "priority": "tinggi",
            "target_duration": 60,
            "actual_duration": 45,
            "status": "selesai",
            "notes": "regression",
            "task_date": _today_iso(),
        }
        r = requests.post(f"{API}/tasks", json=payload, headers=auth["headers"], timeout=30)
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["title"] == payload["title"]
        assert t["status"] == "selesai"
        assert t["actual_duration"] == 45
        assert t["target_duration"] == 60
        assert "id" in t and t["user_id"] == auth["user"]["id"]
        created_task_ids.append(t["id"])

    def test_create_task_2_and_3(self, auth, created_task_ids):
        for i, (status, tgt, act) in enumerate(
            [("proses", 30, 20), ("belum", 45, 0)]
        ):
            r = requests.post(
                f"{API}/tasks",
                json={
                    "title": f"TEST_Regression task {i+2}",
                    "category": "belajar",
                    "priority": "sedang",
                    "target_duration": tgt,
                    "actual_duration": act,
                    "status": status,
                    "notes": "",
                    "task_date": _today_iso(),
                },
                headers=auth["headers"],
                timeout=30,
            )
            assert r.status_code == 200, r.text
            created_task_ids.append(r.json()["id"])

    def test_list_tasks_includes_created(self, auth, created_task_ids):
        r = requests.get(f"{API}/tasks", headers=auth["headers"], timeout=30)
        assert r.status_code == 200
        ids = [t["id"] for t in r.json()]
        for tid in created_task_ids:
            assert tid in ids

    def test_list_tasks_no_auth_401(self):
        r = requests.get(f"{API}/tasks", timeout=30)
        assert r.status_code == 401

    def test_patch_task_updates_and_persists(self, auth, created_task_ids):
        tid = created_task_ids[0]
        r = requests.patch(
            f"{API}/tasks/{tid}",
            json={"actual_duration": 55, "notes": "updated"},
            headers=auth["headers"],
            timeout=30,
        )
        assert r.status_code == 200
        assert r.json()["actual_duration"] == 55
        # GET to verify persistence
        g = requests.get(f"{API}/tasks", headers=auth["headers"], timeout=30)
        found = next((t for t in g.json() if t["id"] == tid), None)
        assert found is not None
        assert found["actual_duration"] == 55
        assert found["notes"] == "updated"

    def test_delete_task(self, auth, created_task_ids):
        # delete the last-created task
        tid = created_task_ids[-1]
        r = requests.delete(f"{API}/tasks/{tid}", headers=auth["headers"], timeout=30)
        assert r.status_code == 200
        g = requests.get(f"{API}/tasks", headers=auth["headers"], timeout=30)
        ids = [t["id"] for t in g.json()]
        assert tid not in ids
        created_task_ids.pop()


# ---------- Weekly Evaluation ----------

class TestWeeklyEvaluation:
    def test_weekly_summary_shape(self, auth):
        r = requests.get(f"{API}/evaluations/weekly", headers=auth["headers"], timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "week_start" in body and "week_end" in body
        stats = body["stats"]
        for k in [
            "total_tasks", "selesai", "proses", "belum", "completion_rate",
            "total_target_min", "total_actual_min", "efficiency", "score",
            "by_day", "by_category",
        ]:
            assert k in stats, f"missing key {k} in stats"
        assert stats["total_tasks"] >= 2  # from tasks created above

    def test_weekly_summary_401_without_auth(self):
        r = requests.get(f"{API}/evaluations/weekly", timeout=30)
        assert r.status_code == 401

    def test_weekly_insight_ai(self, auth):
        # AI can be slow; longer timeout
        r = requests.post(
            f"{API}/evaluations/weekly/insight",
            json={},
            headers=auth["headers"],
            timeout=120,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "insight" in body
        insight = body["insight"]
        assert isinstance(insight, str)
        assert len(insight) > 100, f"insight too short: {len(insight)}"
        # Should look like markdown with ## headings, in Bahasa Indonesia
        assert "##" in insight
        lower = insight.lower()
        # heuristic: expected Indonesian headings from prompt
        assert any(word in lower for word in ["ringkasan", "kekuatan", "saran", "perbaiki"])
