{% macro safe_current_timestamp() %}
    cast(now() as timestamp)
{% endmacro %}
