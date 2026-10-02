import requests
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from api.auth import get_current_user
from api.database import gameData, supabase
from api.models import Nation, Territory
from api.game_logic.income import collectIncome, calcRevByTerr
from api.game_logic.shop import buyItem
from api.game_logic.military import deployUnit, getForces, mergeUnits, splitUnit, disbandUnit
from api.game_logic.diplomacy import allyNation, declareWar
from api.game_logic.admin import registerNation
from api.game_logic.top import top
from api.game_logic.give import giveMoney

router = APIRouter()

@router.get("/me")
def getMe(user = Depends(get_current_user)):
    return user

@router.get("/")
def root():
    return {"status": "War Bot API running"}

@router.get("/territories")
def getAllTerr():
    # All aspects of a territory are public information
    res = supabase.table("territories").select("*").execute()
    return res.data

@router.get("/territory/{name}")
def getTerr(name: str):
    # All aspects of a territory are public information
    res = supabase.table("territories").select("*").ilike("Name", name).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Territory not found")

    return res.data[0]
  
nationPublicFields = ["Name", "Ideology", "Flag", "Demonym", "Color", "Capital", "Diplomacy"]

@router.get("/nations")
def getNations():
  res = supabase.table("nations").select(", ".join(nationPublicFields)).execute()
          
  return res.data

@router.get("/nation/{nation}")
def getNation(nation: str, user = Depends(get_current_user)):
  if user["admin"]:
    res = supabase.table("nations").select("*").eq("Name", nation).execute()
  elif user["nation"] == nation:
    res = supabase.table("nations").select("*").eq("Name", nation).execute()
  elif user.get("source") == "bot":
    res = supabase.table("nations").select(", ".join(nationPublicFields + ["Channel"])).eq("Name", nation).execute()
  else:
    res = supabase.table("nations").select(", ".join(nationPublicFields)).eq("Name", nation).execute()
  
  return res.data[0]

@router.get("/territories/{nation}")
def getNationTerr(nation: str):
    nations = [i["Name"].lower() for i in getNations()]
    if nation.lower() not in nations:
        raise HTTPException(status_code=404, detail="Nation does not exist")
      
    # All aspects of a territory are public information
    res = supabase.table("territories").select("*").ilike("Nation", nation).execute()
    return res.data
  
@router.get("/borders/terr/{name}")
def getBordersTerr(name: str):
    res = supabase.table("territories").select("Bordering").ilike("Name", name).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="No territory found")
    
    return res.data[0]  
      
@router.get("/borders/nation/{name}")
def getBordersNat(name: str):
  terrlist = getNationTerr(name)
  
  borders = set()
  for i in terrlist:
    borders.update(getBordersTerr(i.name)["Bordering"])
  
  borders = borders - set([i.name for i in terrlist])
  
  data = []
  for i in borders:
    data.append({"Name": i, "Nation": getTerr(i)["Nation"]})
  return data

@router.get("/distance/{from_territory}/{to_territory}")
def getDistance(from_territory: str, to_territory: str):
    from_res = (
        supabase
        .table("territories")
        .select("Name, Location")
        .ilike("Name", from_territory)
        .execute()
    )

    if not from_res.data:
        raise HTTPException(status_code=404, detail="Starting territory not found")

    to_res = (
        supabase
        .table("territories")
        .select("Name, Location")
        .ilike("Name", to_territory)
        .execute()
    )

    if not to_res.data:
        raise HTTPException(status_code=404, detail="Destination territory not found")

    loc1 = from_res.data[0]["Location"]
    loc2 = to_res.data[0]["Location"]

    x1, y1 = loc1[0]
    x2, y2 = loc2[0]

    distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    return {
        "from": from_res.data[0]["Name"],
        "to": to_res.data[0]["Name"],
        "distance": distance
    }

@router.get("/players")
def getPlayers():
    data = gameData.getDefaultGameData()
    show_ids = data["Settings"]["Admin"]["Anonymous Players"]["Value"]

    res = supabase.table("nations").select("Name, Flag, Ideology, ruler").execute()

    players = []
    for nation in res.data:
        players.append({
            "Nation": nation["Name"],
            "Flag": nation["Flag"],
            "Ideology": nation["Ideology"],
            "Ruler": nation["ruler"] if show_ids else None
        })

    return players

@router.get("/seas")
def getAllSeas():
    res = supabase.table("seas").select("*").execute()
    return res.data

@router.get("/sea/{name}")
def getSea(name: str):
    res = (
        supabase
        .table("seas")
        .select("*")
        .ilike("Name", name)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Sea not found")

    return res.data[0]

@router.get("/borders/sea/{name}")
def getBordersSea(name: str):
    res = (
        supabase
        .table("seas")
        .select("Bordering")
        .ilike("Name", name)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Sea not found")

    return res.data[0]

@router.get("/maps")
def getAllMaps():
    res = supabase.table("maps").select("*").execute()
    return res.data
  
@router.get("/map/{map}/image/{shrink}")
def getMapImage(map: str, shrink: bool):
    try:
        if shrink:
          res = supabase.storage.from_("maps").create_signed_url(f"{map}/shrink.png", expires_in=60)
        else:
          res = supabase.storage.from_("maps").create_signed_url(f"{map}/map.png", expires_in=60)
          
        return {"url": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/map/{map}/data")
def getMapData(map: str):
    try:
        res = supabase.storage.from_("maps").create_signed_url(f"{map}/data.json", expires_in=60)
        signed_url = res["signedUrl"]
        response = requests.get(signed_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/shop")
def shop():
    return gameData.getShop()

@router.get("/market")
def getMarket():
    res = supabase.table("market").select("*").execute()
    return res.data

def checkNation(user) -> Nation:
  if user["nation"] is None:
    raise HTTPException(status_code=403, detail="User is not a nation.")
  return gameData.getNation(user["nation"])

@router.patch("/settax/{rate}")
def settax(rate: int, user = Depends(get_current_user)):
  checkNation(user)
  
  if rate < 0:
    raise HTTPException(status_code=400, detail="Tax rate cannot be below 0!")
  
  if rate > 100:
    raise HTTPException(status_code=400, detail="Tax rate cannot be above 100!")
  
  res = supabase.table("nations").update({"Tax Rate": rate}).eq("Name", user["nation"]).execute()
  return res.data[0]

@router.get("/bal")
def balance(user = Depends(get_current_user)):
  checkNation(user)
  
  res = supabase.table("nations").select('Balance, Stability, "Political Power"').eq("Name", user["nation"]).execute()
  return res.data[0]

@router.get("/inv")
def inventory(user = Depends(get_current_user)):
  checkNation(user)
  
  res = supabase.table("nations").select("Inventory").eq("Name", user["nation"]).execute()
  return res.data[0]
  
@router.post("/income/collect")
def collect(user=Depends(get_current_user)):
    checkNation(user)

    try:
        nation = gameData.getNation(user["nation"])
        result = collectIncome(gameData, nation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "Nation": nation.name,
        "result": result
    }

@router.get("/income/view")
def income(user = Depends(get_current_user)):
    checkNation(user)

    res = supabase.table("nations").select("*").eq("ruler", user["id"]).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="User Nation not found")

    nation = Nation(res.data[0])
    income = calcRevByTerr(gameData, nation)

    return {
        "success": True,
        "Nation": nation.name,
        "Income": income
    }

class BuyRequest(BaseModel):
    item: str
    quantity: int
    
@router.post("/buy")
def buy(request: BuyRequest, user=Depends(get_current_user)):
    checkNation(user)

    try:
        nation = gameData.getNation(user["nation"])
        result = buyItem(nation, gameData, request.item, request.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "result": result
    }
    
class DeployRequest(BaseModel):
    unit: str
    quantity: int
    territory: str    
    
@router.post("/deploy")
def deploy(request: DeployRequest, user=Depends(get_current_user)):
    checkNation(user)
    nation = gameData.getNation(user["nation"])

    territory = supabase.table("territories").select("*").eq("Name", request.territory).execute()

    if not territory.data:
        raise HTTPException(status_code=404, detail="Territory not found")

    try:
        result = deployUnit(gameData, nation, Territory(territory.data[0]), request.unit, request.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "result": result
    }

class AllyRequest(BaseModel):
    nation: str

@router.post("/ally")
def ally(request: AllyRequest, user=Depends(get_current_user)):
    checkNation(user)

    try:
        nation = gameData.getNation(user["nation"])
        otherNation = gameData.getNation(request.nation)

        result = allyNation(gameData, nation, otherNation)

        return {
            "success": True,
            "result": result
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
      
def generateDiscordLinkCode():
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))
    
@router.post("/discord/link/generate")
def startDiscordLink(user=Depends(get_current_user)):
    
    player_id = user["id"]
    supabase.table("discord_link_codes").delete().eq("player_id", player_id).execute()
    
    code = generateDiscordLinkCode()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    supabase .table("discord_link_codes").insert({
      "code": code,
      "player_id": player_id,
      "expires_at": expires_at.isoformat()
    }).execute()

    return {
        "code": code,
        "expires_at": expires_at.isoformat()
    }
    
class DiscordLinkRequest(BaseModel):
    code: str
    discord_id: str    
    
@router.post("/discord/link/confirm")
def confirmDiscordLink(request: DiscordLinkRequest, user=Depends(get_current_user)):
    if user.get("source") != "bot":
        raise HTTPException(status_code=403, detail="This endpoint can only be used by the Discord bot")

    res = supabase.table("discord_link_codes").select("code, player_id, expires_at").eq("code", request.code.upper()).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="Invalid linking code")

    link = res.data[0]
    
    expires_at = datetime.fromisoformat(link["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) >= expires_at:
        supabase.table("discord_link_codes").delete().eq("code", request.code.upper()).execute()
        raise HTTPException(status_code=400, detail="Linking code has expired")

    player_res = supabase.table("players").select("id, discord_id").eq("id", link["player_id"]).execute()
    if not player_res.data:
        raise HTTPException(status_code=404, detail="Player not found")

    player = player_res.data[0]
    if player["discord_id"] is not None:
        supabase.table("discord_link_codes").delete().eq("code", request.code.upper()).execute()
        raise HTTPException(status_code=400, detail="A Discord account is already linked to this player")

    existing_res = supabase.table("players").select("id").eq("discord_id", request.discord_id).execute()
    if existing_res.data:
        raise HTTPException(status_code=400, detail="This Discord account is already linked to a player")

    supabase.table("players").update({"discord_id": request.discord_id}).eq("id", link["player_id"]).execute()
    supabase.table("discord_link_codes").delete().eq("code", request.code.upper()).execute()

    return {
        "success": True,
        "message": "Discord account linked successfully"
    }

class RegisterRequest(BaseModel):
    nation: str
    ruler: int
    channel: int

@router.post("/register")
def register(data: RegisterRequest, user = Depends(get_current_user)):
    if not user["admin"]:
        raise HTTPException(status_code=403, detail="Admin only")

    nation = gameData.getNation(data.nation)
    result = registerNation(gameData, nation, data.ruler, data.channel)

    return result

@router.get("/gametime")
def getGameTime():
  return gameData.gameTime()

class DeclareWarRequest(BaseModel):
    nation: str
  
@router.post("/declarewar")
def declareWarEndpoint(request: DeclareWarRequest, user=Depends(get_current_user)):
    checkNation(user)

    try:
        nation = gameData.getNation(user["nation"])
        target = gameData.getNation(request.nation)
        result = declareWar(gameData, nation, target)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "result": result
    }

@router.get("/messages")
def getMessages(user=Depends(get_current_user)):
  toAll = supabase.table("messages").select("*").eq("recipient", None).execute()
  
  if user["nation"] is None:
    return toAll.data
  
  recieved = supabase.table("messages").select("*").eq("recipient", user["nation"]).execute()
  sent = supabase.table("messages").select("*").eq("sender", user["nation"]).execute()
  news = supabase.table("messages").select("*").eq("type", "news").execute()
  
  return {
    "success": True,
    "result": toAll.data + recieved.data + sent.data + news.data
  }

@router.get("/last/read")
def getMessages(user=Depends(get_current_user)):
    nation = checkNation(user)

    if "read" not in nation.last:
        nation.last["read"] = {}

    for i in ["notifications", "messages", "news"]:
        if i not in nation.last["read"]:
            nation.last["read"][i] = 0

    gameData.updateNation(nation.name, {"last": nation.last})

    return nation.last["read"]

@router.post("/read/{category}")
def readMessage(category: str, user=Depends(get_current_user)):
    nation = checkNation(user)
    category = category.lower()
    
    if category not in ["notifications", "messages", "news"]:
        raise HTTPException(status_code=400, detail="Invalid Category. Valid categories are notifications, messages, and news.")

    if "read" not in nation.last:
        nation.last["read"] = {}

    nation.last["read"][category] = datetime.now(timezone.utc).isoformat()

    gameData.updateNation(nation.name, {"last": nation.last})

    return nation.last

@router.get("/wars")
def currentWars():
    wars = gameData.getWars()
    response = []
    for i in wars:
      war = {}
      attacker = gameData.getNation(i["from"])
      defender = gameData.getNation(i["to"])
      war["name"] = f"{attacker.demonym}-{defender.demonym} War"
      war["aggressors"] = i["details"]["aggressors"]
      war["defenders"] = i["details"]["defenders"]
      response.append(war)
    return response
      
@router.get("/top/{category}")
def rankNations(category: str):
  try:
    return top(gameData, category.lower())
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))

class GiveRequest(BaseModel):
  nation: str
  money: int
  message: str = ""

@router.post("/give")
def give(request: GiveRequest, user=Depends(get_current_user)):
  nation = checkNation(user)
  try:
    response = giveMoney(gameData, nation, gameData.getNation(request.nation), request.money, request.message)  
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  
  response["success"] = True
  return response

@router.get("/forces")
def forces(domain: Optional[str] = None, theater: Optional[str] = None, user=Depends(get_current_user)):
    nation = checkNation(user)

    try:
        result = getForces(gameData, nation, domain, theater)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "result": result
    }  

class MergeRequest(BaseModel):
  units: list[str]

@router.post("/merge")
def merge(request: MergeRequest, user=Depends(get_current_user)):
  nation = checkNation(user)
  try:
    result = mergeUnits(gameData, nation, request.units)
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  
  return {
      "success": True,
      "result": result
  }

class SplitRequest(BaseModel):
  unit: str
  parts: int = 2

@router.post("/split")
def split(request: SplitRequest, user=Depends(get_current_user)):
  nation = checkNation(user)
  try:
    result = splitUnit(gameData, nation, request.unit, request.parts)
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  
  return {
      "success": True,
      "result": result
  }

@router.post("/disband/{unit}")
def disband(unit: str, user=Depends(get_current_user)):
  nation = checkNation(user)
  try:
    result = disbandUnit(gameData, nation, unit)
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  
  return {
      "success": True,
      "result": result
  }