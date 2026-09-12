# Local development. See README.md.
#
# The whole platform runs under docker compose: the warehouse, Airflow and (from
# ticket 06) the metrics stack. Six services is exactly the point at which
# written setup instructions stop being reliable, which is the trigger PLAN.md
# named for adopting Docker.

-include .env
export

.PHONY: env up down destroy ps logs warehouse db-shell dbt-build test api reload

env:  ## Create .env and generate local secrets. Safe to re-run.
	@./scripts/make-env.sh

up: env  ## Build if needed and start the whole platform
	@docker compose up -d --build
	@printf 'waiting for airflow'
	@until curl -sf "http://localhost:$(AIRFLOW_PORT)/api/v2/version" >/dev/null 2>&1; do printf '.'; sleep 2; done
	@echo ' ready'
	@echo "Airflow  http://localhost:$(AIRFLOW_PORT)  (user: $(AIRFLOW_ADMIN_USER))"
	@echo "Password is in .env as AIRFLOW_ADMIN_PASSWORD"

down:  ## Stop the platform. Data survives.
	@docker compose down

destroy:  ## Stop the platform AND delete the warehouse and Airflow history.
	@docker compose down -v

ps:
	@docker compose ps

logs:  ## Follow logs, e.g. make logs SERVICE=airflow-scheduler
	@docker compose logs -f $(SERVICE)

warehouse: env  ## Start only the warehouse, for running tests without Airflow
	@docker compose up -d warehouse
	@until docker compose exec -T warehouse pg_isready -U $(DSE_PG_USER) -q; do sleep 1; done
	@echo "warehouse ready on localhost:$(DSE_PG_PORT)"

db-shell:
	@docker compose exec -e PGPASSWORD=$(DSE_PG_PASSWORD) warehouse \
		psql -U $(DSE_PG_USER) -d $(DSE_PG_DATABASE)

dbt-build:
	@cd dbt && uv run dbt build

test: warehouse  ## Run the full suite. Creates and drops its own database.
	@uv run pytest -q

api:  ## Serve the read-only price API on :8000
	@uv run uvicorn api.main:app --reload --port 8000

reload:  ## Rebuild the warehouse from everything already landed
	@uv run python -m ingestion.load_day_end --landing landing/dse/day_end
	@cd dbt && uv run dbt build
