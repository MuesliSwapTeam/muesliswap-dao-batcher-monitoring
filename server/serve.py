from fastapi import FastAPI, Depends, HTTPException
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from sqlalchemy.orm import sessionmaker, Session
from contextlib import asynccontextmanager
from typing import List

from . import crud
from common.db import Batcher, _ENGINE
from .schemas import *


SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=_ENGINE)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    FastAPICache.init(InMemoryBackend())
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/", response_model=dict)
async def root():
    return {"message": "MuesliSwap Batcher Analytics"}


@cache(expire=60)
@app.get("/batchers", response_model=List[BatcherResponse])
async def batchers(session: Session = Depends(get_session)):
    return crud.get_batchers(session)


@cache(expire=60)
@app.get("/stats", response_model=BatcherStatsResponse)
async def batcher_stats(address: str, session: Session = Depends(get_session)):
    response = crud.batcher_stats(session, address)
    if response is None:
        raise HTTPException(status_code=404, detail="Batcher not found")
    return response


@cache(expire=60)
@app.get("/all-stats", response_model=List[ExpandedBatcherStatsResponse])
async def all_batcher_stats(session: Session = Depends(get_session)):
    return crud.all_batcher_stats(session)


@cache(expire=60)
@app.get("/transactions", response_model=List[TransactionResponse])
async def batcher_transactions(address: str, session: Session = Depends(get_session)):
    response = crud.batcher_transactions(session, address)
    if not response:
        raise HTTPException(status_code=404, detail="Batcher not found")
    return response
