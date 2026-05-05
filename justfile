# Breaking Law — Justfile (monorepo root)
# https://github.com/casey/just

# === launch ===

# Start the full stack with Docker: API + Redis + DB + MinIO + workers
launch:
    docker compose up --build -d
    @echo "✅ Breaking Law stack started"
    @echo "   API:      http://localhost:8000"
    @echo "   API docs: http://localhost:8000/docs"
    @echo "   MinIO:    http://localhost:9001"

# Start infra services only (DB + Redis + MinIO) — for native dev mode
services:
    docker compose up -d db redis minio
    @echo "✅ Infra services running (DB, Redis, MinIO)"
    @echo "   Ready for: just dev-full"

# Start API in dev mode with hot reload (no Docker)
dev:
    cd backend && LOG_LEVEL=DEBUG poetry run uvicorn breaking_law.main:app --reload --env-file .env --host 0.0.0.0 --port 8000

# Start Dramatiq workers (requires Redis)
workers:
    cd backend && poetry run dramatiq breaking_law.documents.worker_parse \
                                    breaking_law.documents.worker_export \
                                    breaking_law.timekeeping.worker_deadline \
                                    breaking_law.retention.worker

# Start frontend dev server
web-dev:
    cd frontend && npm start

# 🔥 Start EVERYTHING in native dev mode (no Docker for API/frontend)
# Run `just services` first to bring up DB + Redis + MinIO
dev-full:
    @echo "▶  Starting: API (8000) + Workers + Frontend (4200)"
    cd backend && LOG_LEVEL=DEBUG poetry run uvicorn breaking_law.main:app --reload --env-file .env --host 0.0.0.0 --port 8000 &
    cd backend && poetry run dramatiq breaking_law.documents.worker_parse breaking_law.documents.worker_export breaking_law.timekeeping.worker_deadline breaking_law.retention.worker &
    cd frontend && npm start &
    @echo ""
    @echo "✅ Dev stack running:"
    @echo "   Frontend:  http://localhost:4200"
    @echo "   API:       http://localhost:8000"
    @echo "   API docs:  http://localhost:8000/docs"
    @echo ""
    @echo "   Press Ctrl+C to stop all"
    wait

# === docker ===

# Stop all services
down:
    docker compose down

# View logs
logs:
    docker compose logs -f

# Rebuild and restart
rebuild:
    docker compose up --build --force-recreate -d

# === backend ===

# Install backend dependencies
install:
    cd backend && poetry install

# Run Alembic migrations
migrate:
    cd backend && poetry run alembic upgrade head

# Create a new Alembic migration (usage: just migrate-new "add_foo_table")
migrate-new msg:
    cd backend && poetry run alembic revision --autogenerate -m "{{msg}}"

# Drop to psql shell on the dev DB
psql:
    docker compose exec db psql -U legal -d legal_db

# === setup ===

# Run migrations and show seed instructions
seed:
    cd backend && poetry run alembic upgrade head
    @echo ""
    @echo "✅ Migrations applied. Create dev user:"
    @echo ""
    @echo "   1️⃣  Create law firm:"
    @echo "   curl -X POST http://localhost:8000/auth/law-firms \\"
    @echo "     -H 'Content-Type: application/json' \\"
    @echo "     -d '{\"name\":\"BreakingLaw\",\"timezone\":\"Europe/Madrid\"}'"
    @echo ""
    @echo "   2️⃣  Register user (replace FIRM_ID):"
    @echo "   curl -X POST http://localhost:8000/auth/register \\"
    @echo "     -H 'Content-Type: application/json' \\"
    @echo "     -d '{\"email\":\"abogado@test.com\",\"password\":\"Test1234!\",\"full_name\":\"Manuel Armillas\",\"law_firm_id\":\"FIRM_ID\",\"role\":\"owner\"}'"

# === tests ===

# Run all tests
test:
    cd backend && poetry run pytest tests/ -v

# Run tests quietly (CI mode)
test-ci:
    cd backend && poetry run pytest tests/ -q

# Run tests with coverage
test-cov:
    cd backend && poetry run pytest tests/ --cov=breaking_law --cov-report=term-missing

# Run a single test file (usage: just test-file auth)
test-file name:
    cd backend && poetry run pytest tests/test_{{name}}.py -v

# === quality ===

# Run linting
lint:
    cd backend && bash scripts/lint.sh

# Run lint + tests (CI gate)
check: lint test-ci

# === frontend ===

# Install frontend dependencies
web-install:
    cd frontend && npm install

# Build frontend for production
web-build:
    cd frontend && npm run build

# === cleanup ===

# Remove all Docker volumes (⚠️ DESTROYS local data)
clean-db:
    docker compose down -v
    @echo "⚠️  All local database and storage data removed"

# Full reset: down, clean volumes, rebuild
reset: clean-db
    docker compose up --build -d
