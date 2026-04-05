from fastapi import FastAPI, status
from fastapi.requests import Request
from rich.console import Console
from rich.text import Text
import logging
import time
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

logger = logging.getLogger("uvicorn.access")
logger.disabled = True

console = Console()


def register_middleware(app: FastAPI):
    # 在这里注册你的中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "unknown"

        console.print(
            Text(text="INFO", style="bold white on green"),
            f"[bold]{method}[/bold] {path} from {client}",
        )

        response = await call_next(request)
        duration = time.time() - start_time

        console.print(
            Text(text="INFO", style="bold white on green"),
            f"[bold]{method}[/bold] {path} -> [bold]{response.status_code}[/bold] in {duration:.2f}s",
        )
        return response

    # @app.middleware("http")
    # async def authorization_middleware(request: Request, call_next):
    #     if "Authorization" not in request.headers:
    #         return JSONResponse(
    #             content={
    #                 "message": "Authorization header is missing",
    #                 "code": "authorization_header_missing",
    #                 "resolution": "Please include the Authorization header with a valid token in your request.",
    #             },
    #             status_code=status.HTTP_401_UNAUTHORIZED,
    #         )
    #     response = await call_next(request)
    #     return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])
