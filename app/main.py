import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .db import engine
from .routers import auth, tasks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


app = FastAPI(title="TaskFlow")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.include_router(auth.router)
app.include_router(tasks.router)


@app.get("/healthz")
def liveness():
    return {"status": "ok"}


@app.get("/readyz")
def readiness():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ready"}
