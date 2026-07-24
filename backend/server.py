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
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']

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
