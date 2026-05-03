"""Point d'entrée du service de simulation."""

import uvicorn
from .config import get_settings


def main():
    """Lance le serveur FastAPI."""
    settings = get_settings()
    
    uvicorn.run(
        "simulation_service.api:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "local"
    )


if __name__ == "__main__":
    main()



