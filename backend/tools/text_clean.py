def clean_text(value):
    """
    PostgreSQL TEXT/VARCHAR cannot contain NUL bytes.
    Also normalizes list -> string.
    """
    if value is None:
        return None

    # If we accidentally have list/tuple of strings
    if isinstance(value, (list, tuple)):
        value = "\n".join([str(x) for x in value if x is not None])

    # Force string
    value = str(value)

    # Remove NUL bytes and normalize whitespace a bit
    value = value.replace("\x00", "")
    return value.strip()
