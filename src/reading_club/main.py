"""FastAPI application entry point."""

from fastapi import FastAPI

from reading_club.api.v1.router import router as api_v1_router

app = FastAPI(title="Reading Club API", version="0.1.0")
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    """Return a stable service health payload without contacting the database."""
    return {"status": "ok"}
