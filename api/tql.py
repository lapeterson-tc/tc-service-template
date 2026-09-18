"""Safe construction of ThreatConnect TQL string literals.

Every TQL query an endpoint builds by hand interpolates user-supplied
text (an indicator summary, a tag name, a type name, an attribute value, a
free-text filter) into a double-quoted TQL literal. Escaping only the double
quote is NOT enough: a trailing backslash in the input (e.g. ``a\\"``) escapes
the escape and leaves a *live* closing quote, breaking out of the literal. The
backslash MUST be doubled before the quote is escaped.

Use ``tql_quote`` for the inner text and interpolate the result inside the
surrounding quotes, e.g. ``f'summary = "{tql_quote(value)}"'``. Prefer the
tcex ``filter.*(TqlOperator.EQ, value)`` API where a v3 collection object is
already in hand — it parameterizes safely and needs no manual quoting.
"""


def tql_quote(value: str | None) -> str:
    """Escape ``value`` for safe inclusion inside a double-quoted TQL literal.

    Escapes backslash first, then the double quote, so a trailing backslash in
    the input cannot neutralize the closing-quote escape. Returns the inner
    text only — the caller supplies the surrounding quotes.
    """
    return (value or '').replace('\\', '\\\\').replace('"', '\\"')
