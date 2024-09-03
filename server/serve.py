from fastapi import FastAPI, Depends
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
