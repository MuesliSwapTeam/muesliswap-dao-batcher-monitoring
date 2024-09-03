from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import sessionmaker, Session
from . import crud

from common.db import Batcher, _ENGINE

app = FastAPI()

SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=_ENGINE)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@app.get("/")
async def root():
    return {"message": "MuesliSwap Batcher Analytics"}


@app.get("/batchers")
async def batchers(session: Session = Depends(get_session)):
    return crud.get_batchers(session)


@app.get("/stats")
async def batcher_stats(address: str, session: Session = Depends(get_session)):
    response = crud.batcher_stats(session, address)
    if response is None:
        raise HTTPException(status_code=404, detail="Batcher not found")
    return response


@app.get("/all-stats")
async def all_batcher_stats(session: Session = Depends(get_session)):
    return crud.all_batcher_stats(session)
