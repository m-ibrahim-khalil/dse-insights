-- Created once, when the warehouse volume is first initialised.
-- These five names are the project's only layer vocabulary (ADR 0003).
create schema if not exists raw;
create schema if not exists staging;
create schema if not exists intermediate;
create schema if not exists marts;
