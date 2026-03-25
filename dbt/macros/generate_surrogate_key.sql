{% macro generate_surrogate_key(field) %}
    md5(cast(coalesce({{ field }}, '') as varchar))
{% endmacro %}
