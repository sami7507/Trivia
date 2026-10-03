# ⚙️ Commands — Triavia

## Check you have the latest files (Windows)
```bat
check_install.bat
```

## Local (Windows)
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
start.bat                      # trains model if needed, starts API + app (demo SMS codes shown on screen)
```
## Local (macOS / Linux)
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
./start.sh
```
## Manual (two terminals)
```bash
python model/train.py                                   # once
uvicorn backend.main:app --reload --port 8000           # terminal A
BACKEND_URL=http://localhost:8000 streamlit run frontend/app.py   # terminal B (Windows: set BACKEND_URL=...)
```
URLs: app → http://localhost:8501 · API docs → http://localhost:8000/docs · health → /api/v1/health

## Docker
```bash
docker compose up --build          # everything: UI :8501, API :8000
docker compose down                # stop (add -v to also delete the database volume)
```

## PostgreSQL (optional)
```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build   # local Postgres
# or point any Postgres at the API:   set DATABASE_URL=postgresql://user:pass@host:5432/dbname
# run the tests on Postgres:           set TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/dbname & pytest tests -v
```

## Read feedback from visitors
```bash
curl http://localhost:8000/api/v1/feedback -H "X-API-Key: <your API_KEY>"     # needs API_KEY set on the backend
```

## Tests
```bash
pip install -r requirements-dev.txt
pytest tests -v
```

## Git
```bash
git init && git add . && git commit -m "feat: Triavia v2"
git branch -M main
git remote add origin https://github.com/<you>/triavia.git
git push -u origin main
```

## Deploy
**Backend → Render:** New → Blueprint (reads `render.yaml`). Then set `CORS_ORIGINS`, `FRONTEND_URL` (your Streamlit URL) and `BACKEND_PUBLIC_URL` (your Render URL). Add `GOOGLE_*` / `TWILIO_*` if you use those sign-ins.

**Frontend → Streamlit Cloud:** main file `frontend/app.py`; Secrets:
```toml
BACKEND_URL = "https://triavia-api.onrender.com"
```

## Notebook
```bash
pip install -r requirements-dev.txt
jupyter notebook notebooks/01_EDA.ipynb
```

## Environment variables
| Variable | Default | Used by |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | frontend |
| `SECRET_KEY` | *(random per start)* — **set in production** | backend |
| `AUTH_REQUIRED` / `ALLOW_GUEST` | `true` / `true` | backend |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | *(empty = Google button hidden)* | backend |
| `SMS_PROVIDER` (+ `TWILIO_*`) | `console` | backend |
| `OTP_DEV_ECHO` | `false` (launchers set `true` locally) | backend |
| `FRONTEND_URL` / `BACKEND_PUBLIC_URL` | localhost URLs | backend |
| `API_KEY` | *(empty)* server-to-server key — also needed to read feedback | backend |
| `GITHUB_URL` / `LINKEDIN_URL` | github.com/sami7507 / linkedin.com/in/sami7507 *(empty = hidden)* | frontend |
| `CORS_ORIGINS` | `*` | backend |
| `RATE_LIMIT_PER_MINUTE` | `60` | backend |
| `DATABASE_URL` | *(empty = SQLite)* PostgreSQL connection string | backend |
| `TRIAVIA_DB_PATH` | `database/data/triavia.db` (SQLite only) | backend |
