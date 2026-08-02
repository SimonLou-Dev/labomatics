# labomatics/api/middlewares/auth_middleware.py


import secrets

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_403_FORBIDDEN

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware de gestion de du CSRF."""

    def __init__(
        self,
        app,
        allowed_origins: set[str],
        cookie_name: str = "csrf_token",
        header_name: str = "x-csrf-token",
        exclude_prefixes: tuple[str, ...] = ("/docs", "/openapi.json"),
    ) -> None:
        super().__init__(app)
        self.allowed_origins = allowed_origins
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.exclude_prefixes = exclude_prefixes

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if request.method == "OPTIONS":
            return await call_next(request)

        if any(path.startswith(p) for p in self.exclude_prefixes):
            return await call_next(request)

        if request.method in UNSAFE_METHODS:
            origin = request.headers.get("origin")
            if not origin or origin not in self.allowed_origins:
                return JSONResponse(
                    status_code=HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF blocked (bad origin)"},
                )

            csrf_cookie = request.cookies.get(self.cookie_name)
            csrf_header = request.headers.get(self.header_name)

            if csrf_header:
                # Header present → must match the cookie (if cookie exists)
                if csrf_cookie and csrf_cookie != csrf_header:
                    return JSONResponse(
                        status_code=HTTP_403_FORBIDDEN,
                        content={"detail": "CSRF blocked (token mismatch)"},
                    )
                # Header present without cookie, or header matches cookie → allow
                # The custom header itself proves this is an XHR from our app
                # (browsers block cross-origin custom headers on simple requests).
            elif csrf_cookie:
                # Cookie present but no header → reject (must send header)
                return JSONResponse(
                    status_code=HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF blocked (missing token header)"},
                )
            # Neither cookie nor header → allow on first request

        response = await call_next(request)

        # Expose the CSRF token via a response header so that cross-origin
        # frontends can capture it (document.cookie cannot read cookies set
        # on a different domain, even without HttpOnly).
        csrf_cookie = request.cookies.get(self.cookie_name)
        if not csrf_cookie:
            # Générer un nouveau token s'il n'en existe pas
            csrf_cookie = secrets.token_urlsafe(32)
            response.set_cookie(
                self.cookie_name,
                csrf_cookie,
                httponly=True,
                samesite="lax",
                max_age=3600,  # 1 hour
            )

        response.headers["X-CSRF-Token"] = csrf_cookie

        return response
