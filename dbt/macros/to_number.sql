{# Source numbers may carry thousands separators: "1,473,127". Strip, then cast.
   An empty string becomes null rather than zero -- absent is not zero. #}
{% macro to_number(column) -%}
    nullif(replace({{ column }}, ',', ''), '')::numeric
{%- endmacro %}
