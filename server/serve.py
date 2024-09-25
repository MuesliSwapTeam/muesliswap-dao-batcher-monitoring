from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import sessionmaker, Session
from typing import List

from . import crud
from common.db import Batcher, _ENGINE
from .schemas import *

app = FastAPI()

SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=_ENGINE)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@app.get("/", response_model=dict)
async def root():
    return {"message": "MuesliSwap Batcher Analytics"}


@app.get("/batchers", response_model=List[BatcherResponse])
async def batchers(session: Session = Depends(get_session)):
    return crud.get_batchers(session)


@app.get("/stats", response_model=BatcherStatsResponse)
async def batcher_stats(address: str, session: Session = Depends(get_session)):
    response = crud.batcher_stats(session, address)
    if response is None:
        raise HTTPException(status_code=404, detail="Batcher not found")
    return response


@app.get("/all-stats", response_model=List[ExpandedBatcherStatsResponse])
async def all_batcher_stats(session: Session = Depends(get_session)):
    return crud.all_batcher_stats(session)


@app.get("/transactions", response_model=List[TransactionResponse])
async def batcher_transactions(address: str, session: Session = Depends(get_session)):
    response = crud.batcher_transactions(session, address)
    if not response:
        raise HTTPException(status_code=404, detail="Batcher not found")
    return response
