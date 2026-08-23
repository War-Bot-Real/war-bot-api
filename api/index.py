from supabase import create_client
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="War Bot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], #add real host to this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "War Bot API running"}

@app.get("/territories")
def getAllTerr():
    res = supabase.table("territories").execute()
    return res.data

@app.get("/territory/{name}")
def getTerr(name: str):
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

@app.get("/nations")
def getNations():
  res = supabase.table("nations").execute()
  return res.data

@app.get("/nation/{name}")
def getNation(name: str):
    res = (
        supabase
        .table("nations")
        .select("*")
        .ilike("Name", name)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Nation not found")

    return res.data[0]

@app.get("/territories/{nation}")
def getNationTerr(nation: str):
    nations = [i["Name"].lower() for i in getNations()]
    if nation.lower() not in nations:
        raise HTTPException(status_code=404, detail="Nation does not exist")
      
    res = (
        supabase
        .table("territories")
        .select("Name", "Population", "Buildings")
        .ilike("Nation", nation)
        .execute()
    )

    return res.data

@app.get("/troops")
def getAllTroops():
    res = supabase.table("troops").select("ID").execute()
    return res.data

@app.get("/troops/{nation}")
def getNationTroops(nation: str):
    res = (
        supabase
        .table("troops")
        .select("ID")
        .ilike("Nation", nation)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Nation has no troops")

    return res.data

@app.get("/troop/{id}")
def getTroop(id: str):
    res = (
        supabase
        .table("troops")
        .select("*")
        .ilike("ID", id)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="No troop found")

    return res.data[0]
  
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