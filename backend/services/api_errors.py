from datetime import datetime, timezone
from typing import Any


def build_error_response(
    code: str,
    message: str,
    details: Any = None,
    path: str | None = None,
) -> dict[str, Any]:
    """Return a consistent API error shape across all endpoints."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "path": path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        # Compatibility field for clients that already read `detail`
        "detail": message,
    }
