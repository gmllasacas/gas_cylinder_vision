import os
import uvicorn
from app.core import settings, logger

if __name__ == "__main__":
    uvicorn_kwargs = {
        "app": "app.main:app",
        "host": settings.host,
        "port": settings.port,
        "reload": settings.environment == "development",
        "log_level": settings.log_level.lower(),
    }

    # Enable native SSL/TLS when certificate and private key are provided
    if settings.ssl_certfile and settings.ssl_keyfile:
        if os.path.exists(settings.ssl_certfile) and os.path.exists(settings.ssl_keyfile):
            logger.info("Starting Uvicorn with native SSL/TLS encryption.")
            uvicorn_kwargs["ssl_certfile"] = settings.ssl_certfile
            uvicorn_kwargs["ssl_keyfile"] = settings.ssl_keyfile
        else:
            logger.warning(
                f"Configured SSL cert ({settings.ssl_certfile}) or key ({settings.ssl_keyfile}) "
                "not found on disk. Falling back to plain HTTP."
            )

    uvicorn.run(**uvicorn_kwargs)

