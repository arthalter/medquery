from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from medquery.api import create_api_router
from medquery.config import Settings, get_settings
from medquery.drugs import DrugRegistry
from medquery.grok import GrokChatClient
from medquery.recognition import DrugRecognizer
from medquery.runtime import create_lifespan
from medquery.session import InMemorySessionStore


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    sessions = InMemorySessionStore()
    registry = DrugRegistry.load(
        runtime_settings.data_dir / "processed" / "drugs.json"
    )
    recognizer = DrugRecognizer(GrokChatClient(runtime_settings), registry)
    app = FastAPI(
        title=runtime_settings.app_name,
        version="0.1.0",
        lifespan=create_lifespan(runtime_settings),
    )

    app.state.settings = runtime_settings
    app.state.sessions = sessions
    app.include_router(
        create_api_router(runtime_settings, sessions, registry, recognizer)
    )
    app.mount(
        "/",
        StaticFiles(
            directory=runtime_settings.frontend_dir,
            html=True,
            check_dir=False,
        ),
        name="frontend",
    )
    return app


app = create_app()
