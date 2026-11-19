from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.database import gameData
from api.controllers.game import checkNation
from api.game_logic.theaters import createTheater

router = APIRouter(tags=["theaters"])

class CreateTheaterRequest(BaseModel):
    name: str

@router.post("/theaters")
def create(data: CreateTheaterRequest, nation=Depends(checkNation)):
    try:
        return {"success": True, "result": createTheater(gameData, nation, data.name)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))