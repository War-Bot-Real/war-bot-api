from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.database import gameData
from api.auth import checkAdmin
from api.game_logic.diplomacy import registerNation

router = APIRouter(prefix="/admin", tags=["admin"])

class RegisterRequest(BaseModel):
    nation: str
    ruler: int
    channel: int

@router.post("/register")
def register(data: RegisterRequest, user=Depends(checkAdmin)):
    nation = gameData.getNation(data.nation)
    return registerNation(gameData, nation, data.ruler, data.channel)