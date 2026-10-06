import uvicorn

from backend.app.core.config import settings


def main() -> None:
    """Launch the CodeAtlas FastAPI application server."""
    print("=" * 60)
    print(f"  Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"  Host: http://127.0.0.1:{settings.APP_PORT}")
    print(f"  API Documentation: http://127.0.0.1:{settings.APP_PORT}{settings.API_V1_STR}/docs")
    print(f"  ReDoc: http://127.0.0.1:{settings.APP_PORT}{settings.API_V1_STR}/redoc")
    print("=" * 60)
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=settings.APP_PORT, reload=False)


if __name__ == "__main__":
    main()
