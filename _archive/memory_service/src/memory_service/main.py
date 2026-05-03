"""Point d'entrée exécutable pour uvicorn."""

import uvicorn

from .api import create_app


def run() -> None:
    """Démarre le serveur FastAPI."""

    uvicorn.run(
        "memory_service.api:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    run()

