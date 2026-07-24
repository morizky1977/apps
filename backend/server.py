from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta, date
import bcrypt
import jwt
import secrets
import httpx
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
EMERGENT_EMAIL_KEY = os.environ['EMERGENT_EMAIL_KEY']
EMAIL_FROM_NAME = os.environ['EMAIL_FROM_NAME']
EMAIL_BASE_URL = "https://integrations.emergentagent.com"

app = FastAPI()
api_router = APIRouter(prefix="/api")

# ---------- Models ----------
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    created_at: str

class AuthResponse(BaseModel):
    token: str
    user: UserOut

class TaskCreate(BaseModel):
    title: str
    category: str = "umum"
    priority: str = "sedang"  # rendah|sedang|tinggi
    target_duration: int = 0  # minutes
    actual_duration: int = 0
    status: str = "belum"  # belum|proses|selesai
    notes: str = ""
    task_date: str  # YYYY-MM-DD

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    target_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    task_date: Optional[str] = None

class Task(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    category: str
    priority: str
    target_duration: int
    actual_duration: int
    status: str
    notes: str
    task_date: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# ---------- Auth helpers ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Tidak terautentikasi")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token tidak valid")
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Pengguna tidak ditemukan")
    return user

# ---------- Auth Routes ----------
@api_router.post("/auth/register", response_model=AuthResponse)
async def register(payload: UserRegister):
    existing = await db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": user_id,
        "email": payload.email.lower(),
        "name": payload.name,
        "password": hash_password(payload.password),
        "created_at": now,
    }
    await db.users.insert_one(doc)
    token = create_jwt(user_id)
    return AuthResponse(
        token=token,
        user=UserOut(id=user_id, email=payload.email.lower(), name=payload.name, created_at=now),
    )

@api_router.post("/auth/login", response_model=AuthResponse)
async def login(payload: UserLogin):
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password"]):
        raise HTTPException(status_code=401, detail="Email atau kata sandi salah")
    token = create_jwt(user["id"])
    return AuthResponse(
        token=token,
        user=UserOut(id=user["id"], email=user["email"], name=user["name"], created_at=user["created_at"]),
    )

@api_router.get("/auth/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return UserOut(**current_user)

# ---------- Forgot Password (OTP via Email) ----------
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

def build_otp_email_html(name: str, otp: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background-color:#F9F9F8;font-family:Arial,Helvetica,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F9F9F8;padding:40px 0;">
  <tr><td align="center">
    <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border:1px solid #0A0A0A;">
      <tr><td style="padding:32px 32px 8px 32px;">
        <p style="margin:0;font-size:11px;letter-spacing:3px;color:#525252;text-transform:uppercase;font-weight:700;">Ritme · Reset Kata Sandi</p>
        <h1 style="margin:16px 0 0 0;font-size:28px;line-height:1.1;letter-spacing:-1px;color:#0A0A0A;font-weight:900;">Halo {name},</h1>
      </td></tr>
      <tr><td style="padding:8px 32px 24px 32px;">
        <p style="margin:0;font-size:14px;line-height:1.6;color:#525252;">
          Kami menerima permintaan untuk mereset kata sandi akun Anda. Gunakan kode OTP di bawah ini untuk melanjutkan.
        </p>
      </td></tr>
      <tr><td style="padding:0 32px 24px 32px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0A0A0A;">
          <tr><td align="center" style="padding:24px;">
            <p style="margin:0;font-size:11px;letter-spacing:3px;color:#a1a1aa;text-transform:uppercase;font-weight:700;">Kode OTP</p>
            <p style="margin:8px 0 0 0;font-size:38px;letter-spacing:12px;color:#ffffff;font-weight:900;font-family:'Courier New',monospace;">{otp}</p>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="padding:0 32px 24px 32px;">
        <p style="margin:0;font-size:13px;line-height:1.6;color:#525252;">
          Kode ini berlaku selama <strong style="color:#0A0A0A;">1 jam</strong>. Jangan bagikan kode ini kepada siapa pun.
        </p>
        <p style="margin:12px 0 0 0;font-size:13px;line-height:1.6;color:#525252;">
          Jika Anda tidak meminta reset kata sandi, abaikan email ini — kata sandi Anda tetap aman.
        </p>
      </td></tr>
      <tr><td style="padding:20px 32px;border-top:1px solid #E5E5E5;">
        <p style="margin:0;font-size:11px;color:#a1a1aa;">Ritme — Pencatat & Evaluasi Kerja Rutin</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
""".strip()

async def send_otp_email(to_email: str, name: str, otp: str) -> None:
    payload = {
        "to": [to_email],
        "subject": "Kode OTP Reset Kata Sandi — Ritme",
        "html": build_otp_email_html(name, otp),
        "from_name": EMAIL_FROM_NAME,
    }
    async with httpx.AsyncClient(timeout=30) as http_client:
        resp = await http_client.post(
            f"{EMAIL_BASE_URL}/api/v1/email/send",
            headers={"X-Email-Key": EMERGENT_EMAIL_KEY},
            json=payload,
        )
        resp.raise_for_status()

@api_router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    # Always return the same message to prevent user enumeration
    generic_ok = {"ok": True, "message": "Jika email terdaftar, kode OTP telah dikirim."}
    if not user:
        return generic_ok

    otp = f"{secrets.randbelow(1000000):06d}"
    otp_hash = bcrypt.hashpw(otp.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)

    # Invalidate previous unused OTPs for this email
    await db.password_resets.update_many(
        {"email": email, "used": False},
        {"$set": {"used": True, "invalidated_at": now.isoformat()}},
    )
    await db.password_resets.insert_one({
        "id": str(uuid.uuid4()),
        "email": email,
        "user_id": user["id"],
        "otp_hash": otp_hash,
        "expires_at": expires_at.isoformat(),
        "created_at": now.isoformat(),
        "used": False,
        "attempts": 0,
    })

    try:
        await send_otp_email(email, user.get("name", "Pengguna"), otp)
    except Exception as e:
        logger.exception("Failed to send OTP email")
        raise HTTPException(status_code=502, detail="Gagal mengirim email OTP")

    return generic_ok

@api_router.post("/auth/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Kata sandi minimal 6 karakter")

    email = payload.email.lower()
    record = await db.password_resets.find_one(
        {"email": email, "used": False},
        sort=[("created_at", -1)],
    )
    if not record:
        raise HTTPException(status_code=400, detail="Kode OTP tidak valid atau sudah kedaluwarsa")

    expires_at = datetime.fromisoformat(record["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await db.password_resets.update_one({"id": record["id"]}, {"$set": {"used": True}})
        raise HTTPException(status_code=400, detail="Kode OTP sudah kedaluwarsa")

    if record.get("attempts", 0) >= 5:
        await db.password_resets.update_one({"id": record["id"]}, {"$set": {"used": True}})
        raise HTTPException(status_code=429, detail="Terlalu banyak percobaan. Minta kode baru.")

    if not bcrypt.checkpw(payload.otp.encode("utf-8"), record["otp_hash"].encode("utf-8")):
        await db.password_resets.update_one(
            {"id": record["id"]}, {"$inc": {"attempts": 1}}
        )
        raise HTTPException(status_code=400, detail="Kode OTP salah")

    # Update password
    await db.users.update_one(
        {"id": record["user_id"]},
        {"$set": {"password": hash_password(payload.new_password)}},
    )
    await db.password_resets.update_one({"id": record["id"]}, {"$set": {"used": True}})
    return {"ok": True, "message": "Kata sandi berhasil direset. Silakan masuk."}

# ---------- Task Routes ----------
@api_router.post("/tasks", response_model=Task)
async def create_task(payload: TaskCreate, current_user=Depends(get_current_user)):
    task = Task(user_id=current_user["id"], **payload.model_dump())
    await db.tasks.insert_one(task.model_dump())
    return task

@api_router.get("/tasks", response_model=List[Task])
async def list_tasks(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    query = {"user_id": current_user["id"]}
    if start_date and end_date:
        query["task_date"] = {"$gte": start_date, "$lte": end_date}
    elif start_date:
        query["task_date"] = {"$gte": start_date}
    elif end_date:
        query["task_date"] = {"$lte": end_date}
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    docs = await db.tasks.find(query, {"_id": 0}).sort("task_date", -1).to_list(1000)
    return [Task(**d) for d in docs]

@api_router.patch("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, payload: TaskUpdate, current_user=Depends(get_current_user)):
    existing = await db.tasks.find_one({"id": task_id, "user_id": current_user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Tugas tidak ditemukan")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.tasks.update_one({"id": task_id}, {"$set": updates})
    updated = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    return Task(**updated)

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user=Depends(get_current_user)):
    res = await db.tasks.delete_one({"id": task_id, "user_id": current_user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tugas tidak ditemukan")
    return {"ok": True}

# ---------- Weekly Evaluation ----------
def week_bounds(week_start_iso: Optional[str]) -> tuple[str, str]:
    """Return (monday, sunday) ISO date strings for the week that contains the given date."""
    if week_start_iso:
        d = date.fromisoformat(week_start_iso)
    else:
        d = date.today()
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()

def compute_stats(tasks: list[dict]) -> dict:
    total = len(tasks)
    done = sum(1 for t in tasks if t["status"] == "selesai")
    in_progress = sum(1 for t in tasks if t["status"] == "proses")
    not_started = sum(1 for t in tasks if t["status"] == "belum")
    total_target = sum(t.get("target_duration", 0) for t in tasks)
    total_actual = sum(t.get("actual_duration", 0) for t in tasks)
    completion_rate = round((done / total) * 100, 1) if total > 0 else 0.0
    efficiency = round((total_actual / total_target) * 100, 1) if total_target > 0 else 0.0

    # Score: 60% completion + 40% efficiency (capped)
    eff_score = min(efficiency, 120) if efficiency > 0 else 0
    # penalize over-time (>100% actual means slower). ideal ~100
    eff_normalized = max(0, 100 - abs(100 - eff_score)) if total_target > 0 else 0
    score = round(completion_rate * 0.6 + eff_normalized * 0.4, 1)

    # by day
    by_day: dict[str, dict] = {}
    for t in tasks:
        d = t["task_date"]
        if d not in by_day:
            by_day[d] = {"date": d, "total": 0, "selesai": 0, "target": 0, "aktual": 0}
        by_day[d]["total"] += 1
        by_day[d]["target"] += t.get("target_duration", 0)
        by_day[d]["aktual"] += t.get("actual_duration", 0)
        if t["status"] == "selesai":
            by_day[d]["selesai"] += 1

    # by category
    by_cat: dict[str, dict] = {}
    for t in tasks:
        c = t.get("category", "umum")
        if c not in by_cat:
            by_cat[c] = {"category": c, "total": 0, "selesai": 0}
        by_cat[c]["total"] += 1
        if t["status"] == "selesai":
            by_cat[c]["selesai"] += 1

    return {
        "total_tasks": total,
        "selesai": done,
        "proses": in_progress,
        "belum": not_started,
        "completion_rate": completion_rate,
        "total_target_min": total_target,
        "total_actual_min": total_actual,
        "efficiency": efficiency,
        "score": score,
        "by_day": sorted(by_day.values(), key=lambda x: x["date"]),
        "by_category": sorted(by_cat.values(), key=lambda x: -x["total"]),
    }

@api_router.get("/evaluations/weekly")
async def weekly_summary(week: Optional[str] = None, current_user=Depends(get_current_user)):
    start, end = week_bounds(week)
    docs = await db.tasks.find(
        {"user_id": current_user["id"], "task_date": {"$gte": start, "$lte": end}}, {"_id": 0}
    ).to_list(1000)
    stats = compute_stats(docs)
    return {"week_start": start, "week_end": end, "stats": stats}

@api_router.post("/evaluations/weekly/insight")
async def weekly_ai_insight(payload: dict, current_user=Depends(get_current_user)):
    week = payload.get("week")
    start, end = week_bounds(week)
    docs = await db.tasks.find(
        {"user_id": current_user["id"], "task_date": {"$gte": start, "$lte": end}}, {"_id": 0}
    ).to_list(1000)
    stats = compute_stats(docs)

    # Check cache
    cache_key = f"{current_user['id']}:{start}:{stats['total_tasks']}:{stats['selesai']}:{stats['total_actual_min']}"
    cached = await db.insight_cache.find_one({"key": cache_key}, {"_id": 0})
    if cached:
        return {"week_start": start, "week_end": end, "insight": cached["insight"], "stats": stats}

    # Build prompt
    tasks_summary_lines = []
    for t in docs[:40]:
        tasks_summary_lines.append(
            f"- [{t['status']}] {t['title']} (kategori: {t.get('category','umum')}, "
            f"prioritas: {t.get('priority','sedang')}, target: {t.get('target_duration',0)} menit, "
            f"aktual: {t.get('actual_duration',0)} menit)"
        )
    tasks_block = "\n".join(tasks_summary_lines) if tasks_summary_lines else "(tidak ada tugas minggu ini)"

    system_msg = (
        "Anda adalah pelatih produktivitas profesional yang memberi wawasan singkat, "
        "praktis, dan personal dalam Bahasa Indonesia. Jawaban harus terstruktur dan mudah dibaca."
    )
    user_prompt = f"""Berikut adalah data kerja rutin pengguna untuk minggu {start} sampai {end}:

Statistik agregat:
- Total tugas: {stats['total_tasks']}
- Selesai: {stats['selesai']}
- Proses: {stats['proses']}
- Belum: {stats['belum']}
- Tingkat penyelesaian: {stats['completion_rate']}%
- Total target durasi: {stats['total_target_min']} menit
- Total durasi aktual: {stats['total_actual_min']} menit
- Efisiensi (aktual/target): {stats['efficiency']}%
- Skor performa: {stats['score']}/100

Daftar tugas (maks 40):
{tasks_block}

Berikan evaluasi ringkas dengan format berikut (gunakan markdown ringan, tanpa emoji):

## Ringkasan Performa
(2-3 kalimat menilai performa keseluruhan)

## Kekuatan
- (2-3 poin bullet)

## Perlu Diperbaiki
- (2-3 poin bullet)

## Saran Konkret untuk Minggu Depan
- (3-4 langkah spesifik dan dapat dijalankan)"""

    insight_text = ""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"insight-{current_user['id']}-{start}",
            system_message=system_msg,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        response = await chat.send_message(UserMessage(text=user_prompt))
        insight_text = response if isinstance(response, str) else str(response)
    except Exception as e:
        logger.exception("AI insight failed")
        raise HTTPException(status_code=500, detail=f"Gagal menghasilkan wawasan AI: {e}")

    await db.insight_cache.insert_one({
        "key": cache_key,
        "user_id": current_user["id"],
        "week_start": start,
        "insight": insight_text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"week_start": start, "week_end": end, "insight": insight_text, "stats": stats}

# ---------- Root ----------
@api_router.get("/")
async def root():
    return {"message": "Kerja Rutin API"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
