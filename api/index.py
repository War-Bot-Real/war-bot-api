from supabase import create_client
import os
from fastapi import FastAPI, HTTPException

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="War Bot API")

@app.get("/")
def root():
    return {"status": "War Bot API running"}

@app.get("/territories")
def getAllTerr():
    res = supabase.table("territories").select("Name").execute()
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
  res = supabase.table("nations").select("Name").execute()
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
    res = (
        supabase
        .table("territories")
        .select("Name")
        .ilike("Nation", nation)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Nation has no territories")

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