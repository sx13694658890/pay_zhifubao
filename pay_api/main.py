from __future__ import annotations

import sys
from pathlib import Path


def _ensure_project_root_on_path() -> None:
    """在 `pay_api` 目录下执行 `python main.py` 时，把上一级目录加入 sys.path，才能 `import pay_api.*`。"""
    here = Path(__file__).resolve().parent
    if here.name != "pay_api":
        return
    root = str(here.parent)
    if root not in sys.path:
        sys.path.insert(0, root)


_ensure_project_root_on_path()

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pay_api.db import close_pool, open_pool
from pay_api.routes import router as pay_router
from pay_api.settings import get_settings
@asynccontextmanager
async def lifespan(_app: FastAPI):
    s = get_settings()
    await open_pool(s.database_url)
    yield
    await close_pool()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="pay-zhifubao", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(pay_router, prefix="/api")
    return app


app = create_app()


def _uvicorn_app_import_str() -> str:
    """本地 `python main.py` 用 main:app；安装后以 pay_api.main 导入时用 pay_api.main:app。"""
    if __name__ == "__main__":
        return "main:app"
    return f"{__name__}:app"


def main() -> None:
    s = get_settings()
    uvicorn.run(
        _uvicorn_app_import_str(),
        host=s.host,
        port=s.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
