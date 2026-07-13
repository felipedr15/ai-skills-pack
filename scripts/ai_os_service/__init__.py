"""AI OS protocol-neutral service layer.

Provides a reusable interface to AI OS capabilities with input validation,
structured errors, security boundaries, and deterministic output.
"""

SERVICE_VERSION = "1.0.0"
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
MAX_TRAVERSAL_DEPTH = 5
MAX_EXCERPT_CHARS = 2000
MAX_RESPONSE_ITEMS = 100
