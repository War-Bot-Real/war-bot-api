from supabase import create_client
import os
import requests
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="War Bot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://war-bot-web.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    try:
        user = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token"
        )

    if not user or not user.user:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication"
        )

    auth_user_id = user.user.id

    res = (
        supabase
        .table("players")
        .select("id, auth_user_id, discord_id, admin")
        .eq("auth_user_id", auth_user_id)
        .execute()
    )

    if not res.data:
        raise HTTPException(
            status_code=403,
            detail="Authenticated user is not a registered player"
        )
    
    nation_res = (
        supabase
        .table("nations")
        .select("Name")
        .eq("ruler", res.data[0]["id"])
        .execute()
    )
    res.data[0]["nation"] = nation_res.data[0]["Name"] if nation_res.data else None

    return res.data[0]

@app.get("/me")
def getMe(user = Depends(get_current_user)):
    return user

@app.get("/")
def root():
    return {"status": "War Bot API running"}

@app.get("/territories")
def getAllTerr():
    # All aspects of a territory are public information
    res = supabase.table("territories").select("*").execute()
    return res.data

@app.get("/territory/{name}")
def getTerr(name: str):
    # All aspects of a territory are public information
    res = (
        supabase
        .table("territories")
        .select("*")
        .ilike("Name", name)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Territory not found")

    return res.data[0]
  
nationPublicFields = ["Name", "Ideology", "Flag", "Demonym", "Color", "Capital", "Diplomacy"]

@app.get("/nations")
def getNations():
  res = supabase.table("nations").select(", ".join(nationPublicFields)).execute()
          
  return res.data

@app.get("/nation/{nation}")
def getNation(nation: str, user = Depends(get_current_user)):
  if user["admin"]:
    res = supabase.table("nations").select("*").eq("Name", nation)
  elif user["nation"] is not None:
    res = supabase.table("nations").select("*").eq("Name", nation)
  else:
    res = supabase.table("nations").select(", ".join(nationPublicFields)).eq("Name", nation)
  
  return res.data
    
  

@app.get("/territories/{nation}")
def getNationTerr(nation: str):
    nations = [i["Name"].lower() for i in getNations()]
    if nation.lower() not in nations:
        raise HTTPException(status_code=404, detail="Nation does not exist")
      
    res = (
        supabase
        .table("territories")
        .select("*")
        .ilike("Nation", nation)
        .execute()
    )

    return res.data

@app.get("/units/{nation}")
def getNationTroops(nation: str, user = Depends(get_current_user)):
    if user["admin"]:
      res = supabase.table("units").select("*").eq("Nation", nation).execute()
    elif user["nation"] is not None:
      if user["nation"] == nation:
        res = supabase.table("units").select("*").eq("Nation", nation).execute()
      else:
        raise HTTPException(status_code=403, detail="You do not have permission to access units from this nation.")
    else:
      raise HTTPException(status_code=403, detail="You do not have permission to access units from this nation.")

    return res.data
  
@app.get("/borders/terr/{name}")
def getBordersTerr(name: str):
    res = (
        supabase
        .table("territories")
        .select("Bordering")
        .ilike("Name", name)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="No territory found")
    
    return res.data[0]  
      
@app.get("/borders/nation/{name}")
def getBordersNat(name: str):
  terrlist = getNationTerr(name)
  
  borders = set()
  for i in terrlist:
    print(i["Name"])
    borders.update(getBordersTerr(i["Name"])["Bordering"])
  
  borders = borders - set([i["Name"] for i in terrlist])
  
  data = []
  for i in borders:
    data.append({"Name": i, "Nation": getTerr(i)["Nation"]})
  return data

@app.get("/distance/{from_territory}/{to_territory}")
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

@app.get("/players")
def getPlayers():
    res = (
        supabase
        .table("nations")
        .select("Name, Flag, Ideology, ruler")
        .execute()
    )

    players = []

    for nation in res.data:
        players.append({
            "Nation": nation["Name"],
            "Flag": nation["Flag"],
            "Ideology": nation["Ideology"],
            "Ruler": nation["ruler"]
        })

    return players

@app.get("/seas")
def getAllSeas():
    res = supabase.table("seas").select("*").execute()
    return res.data

@app.get("/sea/{name}")
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

@app.get("/borders/sea/{name}")
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

@app.get("/maps")
def getAllMaps():
    res = supabase.table("maps").select("*").execute()
    return res.data

@app.get("/market")
def getMarket():
    res = supabase.table("market").select("*").execute()
    return res.data

@app.get("/map/{map}/{shrink}")
def getMap(map: str, shrink: bool):
    try:
        if shrink:
          res = supabase.storage.from_("maps").create_signed_url(f"{map}/shrink.png", expires_in=60)
        else:
          res = supabase.storage.from_("maps").create_signed_url(f"{map}/map.png", expires_in=60)
          
        return {"url": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def getDefaultGameData():
  res = supabase.storage.from_("info").create_signed_url(
      "data.json",
      expires_in=60
  )

  signed_url = res["signedUrl"]

  response = requests.get(signed_url)
  response.raise_for_status()

  data = response.json()

  return data

@app.get("/shop")
def shop():
    try:
        data = getDefaultGameData()
        store = {}
        
        for i in data["Units"]:
          prices = {}
          for j in data["Units"][i]:
            prices[j] = data["Units"][i][j]["Cost"]
          store[i + " Units"] = prices
        
        store["Buildings"] = data["Buildings"]
        
        return store

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.patch("/settax/{rate}")
def settax(rate: int, user = Depends(get_current_user)):
  if user["nation"] is None:
    raise HTTPException(status_code=403, detail="User is not a nation.")
  
  if rate < 0:
    raise HTTPException(status_code=400, detail="Tax rate cannot be below 0!")
  
  if rate > 100:
    raise HTTPException(status_code=400, detail="Tax rate cannot be above 100!")
  
  res = supabase.table("nations").update({"Tax Rate": rate}).eq("Name", user["nation"]).execute()
  return res.data[0]

