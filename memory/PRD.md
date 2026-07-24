# RITME — Pencatat & Evaluasi Kerja Rutin

## Original Problem Statement
"saya ingin membangun web app yang mencatat kerja rutin saya sehingga saya dapat mengevaluasi dan menilai performa kerja rutin yang saya lakukan setiap minggunya."

## User Choices (2026-07-24)
- Pencatatan tugas: **detail** (kategori, prioritas, target vs aktual durasi, catatan)
- Evaluasi: **dashboard statistik + AI insight**
- Auth: **email/password JWT**
- Bahasa: **Bahasa Indonesia**, tema **clean/modern (Neo-Swiss Utility)**
- AI Model: **Claude Sonnet 4.5** via Emergent Universal LLM Key

## Personas
- Profesional / knowledge worker yang ingin melacak rutinitas kerja harian dan mengukur konsistensi tiap minggu.

## Architecture
- **Backend**: FastAPI + Motor (MongoDB), JWT (PyJWT) + bcrypt, emergentintegrations for Claude Sonnet 4.5
- **Frontend**: React 19 + React Router 7 + Tailwind + Shadcn UI + Recharts + Phosphor Icons + Sonner
- **Auth**: Bearer JWT stored in localStorage (`kr_token`), 30d expiry

## Data Models (Mongo Collections)
- `users`: {id, email, name, password (bcrypt), created_at}
- `tasks`: {id, user_id, title, category, priority, target_duration, actual_duration, status, notes, task_date, created_at, updated_at}
- `insight_cache`: {key, user_id, week_start, insight, created_at}

## Implemented (2026-07-24 — MVP v1)
- Register / Login / Me endpoints
- Task CRUD scoped per user
- Weekly evaluation: aggregated stats (total, selesai/proses/belum, completion rate, target vs aktual, efficiency, score, by_day, by_category)
- AI Insight endpoint calling Claude Sonnet 4.5 with cached results
- Frontend: `/masuk` (login/register), `/dasbor`, `/tugas`, `/evaluasi`
- Neo-Swiss design (DM Sans display + Space Grotesk body, International Klein Blue accent)
- Recharts weekly activity bar chart
- Week navigation on evaluation page
- Toast notifications (sonner), Radix Dialog for task create/edit
- Full data-testid coverage
- Testing verified: backend 100%, frontend 100% core flow

## Backlog
- **P1**: Password reset flow, export weekly report to PDF/CSV
- **P1**: Recurring task templates (auto-populate weekly)
- **P2**: Streaks & habit heatmap
- **P2**: Team / shared workspaces
- **P2**: Reminders (email via Resend or in-app)
- **P3**: Mobile PWA install prompt

## Next Actions
- Await user feedback on visual & flow
- Optionally add task tags/filtering by priority
