from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.database import gameData
from api.controllers.game import checkNation
from api.game_logic.theaters import createTheater, getTheater, addtoTheater

router = APIRouter(tags=["theaters"])

class TheaterTiles(BaseModel):
    items: list[str]

@router.post("/theater/create/{name}")
def create(name: str, data: TheaterTiles, nation=Depends(checkNation)):
    try:
        return {"success": True, "result": createTheater(gameData, nation, name, data.items)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/theaters")
def get_all(nation=Depends(checkNation)):
    return {"success": True, "result": nation.theaters}

@router.get("/theaters/{name}")
def get_one(name: str, nation=Depends(checkNation)):
    try:
        return {"success": True, "result": getTheater(nation, name)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/theaters/add/{name}")
def add_items(name: str, data: TheaterTiles, nation=Depends(checkNation)):
    try:
        result = addtoTheater(gameData, nation, name, data.items)
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))