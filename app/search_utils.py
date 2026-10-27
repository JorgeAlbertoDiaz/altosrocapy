"""Input normalization helpers for socio searches."""


def normalize_doc_query(query):
    """Return digits when the query looks like a DNI; otherwise return it as-is.

    Accepts common human formats such as "30.541.150", "30 541 150",
    "30-541-150" or "(30) 541-150". Text queries (names) are untouched.
    """
    q = (query or "").strip()
    if not q:
        return ""
    looks_like_doc = all(
        ch.isdigit() or ch.isspace() or ch in ".-()" for ch in q
    )
    if looks_like_doc:
        digits = "".join(ch for ch in q if ch.isdigit())
        if digits:
            return digits
    return q
