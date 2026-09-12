{# dbt's default prefixes the target schema onto a custom one, which would put
   models in "staging_marts". The layer names in ADR 0003 are the only vocabulary
   this project uses, so a model's configured schema is used verbatim. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name | trim if custom_schema_name else target.schema }}
{%- endmacro %}
