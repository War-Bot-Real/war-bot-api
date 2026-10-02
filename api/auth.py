import os
from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

from api.database import supabase

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), discord_id: str | None = Header(None)):
    token = credentials.credentials
    if token == BOT_TOKEN:
        if discord_id is None:
            return {
                "id": None,
                "auth_user_id": None,
                "discord_id": None,
                "admin": False,
                "nation": None,
                "source": "bot"
            }

        res = supabase.table("players").select("id, auth_user_id, discord_id, admin").eq("discord_id", discord_id).execute()
        if not res.data:
            return {
                "id": None,
                "auth_user_id": None,
                "discord_id": discord_id,
                "admin": False,
                "nation": None,
                "source": "bot"
            }
    else:
        try:
            user = supabase.auth.get_user(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired authentication token")

        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid authentication")

        res = supabase.table("players").select("id, auth_user_id, discord_id, admin").eq("auth_user_id", user.user.id).execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="Player not found")

    player = res.data[0]
    nation_res = supabase.table("nations").select("name").eq("ruler", player["id"]).execute()
    player["nation"] = nation_res.data[0]["name"] if nation_res.data else None
    player["source"] = "bot" if token == BOT_TOKEN else "website"
    return player

def checkAdmin(user=Depends(get_current_user)):
    if not user["admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user