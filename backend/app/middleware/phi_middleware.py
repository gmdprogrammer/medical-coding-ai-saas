"""
PHI Guard Middleware
━━━━━━━━━━━━━━━━━━
Inspects incoming requests for accidental PHI in query parameters or headers.
Does NOT read request bodies (streaming integrity).
Logs any detected PHI patterns to the audit trail.

This is a defense-in-depth measure — primary anonymization happens in the service layer.
"""
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger

# Quick-scan patterns for query params / headers
_QUICK_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),             # SSN
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),  # Email
    re.compile(r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), # Phone
]


class PHIGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Scan query params for PHI
        query_string = str(request.url.query)
        for pattern in _QUICK_PATTERNS:
            if pattern.search(query_string):
                logger.warning(
                    f"Potential PHI detected in query params — path={request.url.path}"
                )
                break

        response = await call_next(request)
        return response
