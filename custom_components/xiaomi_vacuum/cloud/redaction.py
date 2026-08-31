"""Helpers that keep cloud session material out of Home Assistant's log."""

from __future__ import annotations

import re

_URL_QUERY_STRING = re.compile(r"\?\S*")


def sanitized_error_text(exception: Exception) -> str:
    """
    Strip URL query strings from upstream error text before it can be logged.

    requests/urllib3 embed the full request URL in their exception messages,
    and the signed cloud calls carry the plaintext ``ssecurity`` session secret
    as a query parameter — without this, a routine connection failure would
    write the credential into Home Assistant's log.
    """
    return _URL_QUERY_STRING.sub("?<redacted>", str(exception))


def response_key_names(body: object) -> str:
    """
    Describe a cloud response by its key names only, never by its values.

    Login responses carry the session secret, the service token and signed
    redirect URLs, so the body itself can never be logged — the key names are
    enough to tell which stage of the QR flow returned an unexpected shape.
    """
    if not isinstance(body, dict):
        return f"<{type(body).__name__}>"
    return ", ".join(sorted(str(key) for key in body)) or "<empty>"
