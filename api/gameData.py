import requests
from supabase import Client

class GameData:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    def getDefaultGameData(self):
        res = self.supabase.storage.from_("info").create_signed_url(
            "data.json",
            expires_in=60
        )

        signed_url = res["signedUrl"]

        response = requests.get(signed_url)
        response.raise_for_status()

        return response.json()

    def getShop(self):
        data = self.getDefaultGameData()

        store = {}

        for category in data["Units"]:
            prices = {}

            for item in data["Units"][category]:
                prices[item] = data["Units"][category][item]["Cost"]

            store[category + " Units"] = prices

        store["Buildings"] = data["Buildings"]

        return store

    def getUnitCounters(self):
      res = self.supabase.table("unitcounters").select("*").execute()

      return {row["id"]: row["count"] for row in res.data}
    
    def incrementUnitCounters(self, unit_id):
      res = self.supabase.table("unitcounters").select("count").eq("id", unit_id).execute()

      if not res.data:
        self.supabase.table("unitcounters").insert({"id": unit_id, "count": 1}).execute()
        return 1

      newcount = res.data[0]["count"] + 1
      self.supabase.table("unitcounters").update({"count": newcount}).eq("id", unit_id).execute()

      return newcount