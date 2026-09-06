# Local development. See README.md.
#
# Postgres runs in a container so its version is pinned per project and teardown
# is one command. This is the database only -- dockerising the platform's own
# services is deliberately deferred (PLAN.md section 4, step 5).

include .env
export

PG_CONTAINER := dse-postgres
PG_IMAGE     := postgres:16-alpine

.PHONY: db-up db-down db-shell dbt-debug dbt-build test fmt

db-up:  ## Start the warehouse and wait for it to accept connections
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

test:
	@uv run pytest -q
