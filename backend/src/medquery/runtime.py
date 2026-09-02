from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI
from pymilvus import MilvusClient

from medquery.config import Settings


def open_milvus(settings: Settings) -> MilvusClient:
    settings.milvus_uri.parent.mkdir(parents=True, exist_ok=True)
    return MilvusClient(uri=str(settings.milvus_uri))


def create_lifespan(
    settings: Settings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        milvus = open_milvus(settings)
        app.state.milvus = milvus
        try:
            yield
        finally:
            milvus.close()

    return lifespan
