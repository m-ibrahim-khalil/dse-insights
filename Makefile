# Local development. See README.md.
#
# Postgres runs in a container so its version is pinned per project and teardown
# is one command. This is the database only -- dockerising the platform's own
# services is deliberately deferred (PLAN.md section 4, step 5).

-include .env
export

# Defaults, so every target works on a fresh clone before .env exists. Anything
# set in .env wins. `include` is resolved when make parses this file, so a target
# that creates .env cannot affect the run that created it -- hence ?= here.
DSE_PG_HOST ?= localhost
DSE_PG_PORT ?= 55432
DSE_PG_DATABASE ?= dse
DSE_PG_USER ?= dse
DSE_PG_PASSWORD ?= dse_local_dev

PG_CONTAINER := dse-postgres
PG_IMAGE     := postgres:16-alpine

.PHONY: env db-up db-down db-shell dbt-debug dbt-build test api

env:  ## Create .env from the example if it does not exist
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example")

db-up: env  ## Start the warehouse and wait for it to accept connections
	@docker start $(PG_CONTAINER) 2>/dev/null || docker run -d \
		--name $(PG_CONTAINER) \
		-e POSTGRES_DB=$(DSE_PG_DATABASE) \
		-e POSTGRES_USER=$(DSE_PG_USER) \
		-e POSTGRES_PASSWORD=$(DSE_PG_PASSWORD) \
		-p $(DSE_PG_PORT):5432 \
		$(PG_IMAGE)
	@printf 'waiting for postgres'
	@until docker exec $(PG_CONTAINER) pg_isready -U $(DSE_PG_USER) -q 2>/dev/null; do \
		printf '.'; sleep 1; done
	@echo ' ready'
	@$(MAKE) --no-print-directory db-schemas

db-schemas:
	@docker exec -e PGPASSWORD=$(DSE_PG_PASSWORD) $(PG_CONTAINER) \
		psql -U $(DSE_PG_USER) -d $(DSE_PG_DATABASE) -q -c \
		"create schema if not exists raw; \
		 create schema if not exists staging; \
		 create schema if not exists intermediate; \
		 create schema if not exists marts;"

db-down:  ## Stop and remove the warehouse, discarding all data
	@docker rm -f $(PG_CONTAINER) 2>/dev/null || true

db-shell:
	@docker exec -it -e PGPASSWORD=$(DSE_PG_PASSWORD) $(PG_CONTAINER) \
		psql -U $(DSE_PG_USER) -d $(DSE_PG_DATABASE)

dbt-debug:
	@cd dbt && uv run dbt debug

dbt-build:
	@cd dbt && uv run dbt build

test:  ## Run the full suite. Requires the warehouse to be up.
	@uv run pytest -q

api:  ## Serve the read-only price API on :8000
	@uv run uvicorn api.main:app --reload --port 8000
