from supabase import create_client
import os
from api.repositories.gameData import GameData

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
gameData = GameData(supabase)