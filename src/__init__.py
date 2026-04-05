from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from src.books.routes import book_router
from src.auth.routes import auth_router
from src.reviews.routes import reviews_router
from src.db.main import init_db
from src.middleware import register_middleware
from src.errors import register_all_errors

from contextlib import asynccontextmanager
from rich import traceback, print, pretty

traceback.install()
pretty.install()


@asynccontextmanager
async def life_span(app: FastAPI):
    print("app is starting ...")
    await init_db()
    # yield is used to separate the startup and shutdown code in the lifespan function. The code before yield will be executed when the app starts, and the code after yield will be executed when the app shuts down.
    yield
    print("app is shutting down ...")


version = "v1"

app = FastAPI(
    title="Bookly",
    description="a CRUD service for book review",
    version=version,
    # lifespan=life_span,
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/license/mit/",
    },
    contact={"name": "TJ", "email": "1153695045@qq.com"},
    docs_url=f"/api/{version}/docs",
    openapi_url=f"/api/{version}/openapi.json",
)


register_all_errors(app)
register_middleware(app)

app.include_router(book_router, prefix=f"/api/{version}/books", tags=["books"])
app.include_router(auth_router, prefix=f"/api/{version}/auth", tags=["auth"])
app.include_router(reviews_router, prefix=f"/api/{version}/reviews", tags=["review"])
