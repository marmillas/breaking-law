# Breaking Law — Justfile (monorepo root)
# https://github.com/casey/just

# === launch ===

# Start the full stack: API + Redis + DB + MinIO + workers
launch:
    docker compose up --build -d
    @echo "✅ Breaking Law stack started"
    @echo "   API:      http://localhost:8000"
    @echo "   API docs: http://localhost:8000/docs"
    @echo "   MinIO:    http://localhost:9001"

# Start API in dev mode (no Docker — requires Redis + DB running)
dev:
    cd backend && uvicorn breaking_law.main:app --reload --host 0.0.0.0 --port 8000

# Start Dramatiq workers (requires Redis running)
workers:
    cd backend && dramatiq breaking_law.documents.worker_parse \
                         breaking_law.documents.worker_export \
                         breaking_law.timekeeping.worker_deadline \
                         breaking_law.retention.worker

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
    cd backend && pip install -e ".[dev]"

# Run Alembic migrations
migrate:
    cd backend && alembic upgrade head

# Create a new Alembic migration (usage: just migrate-new "add_foo_table")
migrate-new msg:
    cd backend && alembic revision --autogenerate -m "{{msg}}"

# Drop to psql shell on the dev DB
psql:
    docker compose exec db psql -U legal -d legal_db

# === tests ===

# Run all tests
test:
    cd backend && python -m pytest tests/ -v

# Run tests quietly (CI mode)
test-ci:
    cd backend && python -m pytest tests/ -q

# Run tests with coverage
test-cov:
    cd backend && python -m pytest tests/ --cov=breaking_law --cov-report=term-missing

# Run a single test file (usage: just test-file auth)
test-file name:
    cd backend && python -m pytest tests/test_{{name}}.py -v

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

# Start frontend dev server
web-dev:
    cd frontend && npm run dev

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
