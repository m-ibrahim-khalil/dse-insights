-- A read-only role for Grafana. A dashboard should never be able to write to
-- the warehouse, and the completeness queries only ever read.
--
-- psql does not substitute :variables inside a dollar-quoted block, so the
-- statements are built with format() and run through \gexec instead.

select format('create role grafana_ro login password %L', :'grafana_password')
where not exists (select 1 from pg_roles where rolname = 'grafana_ro')
\gexec

select format('alter role grafana_ro login password %L', :'grafana_password')
\gexec

grant connect on database dse to grafana_ro;
grant usage on schema marts, staging, raw to grafana_ro;
grant select on all tables in schema marts, staging, raw to grafana_ro;
alter default privileges in schema marts, staging, raw grant select on tables to grafana_ro;
