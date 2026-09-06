import requests
from supabase import Client

class GameData:

    def __init__(self, supabase: Client):
        self.supabase = supabase

    # ---------- Nations ----------

    def getNation(self, nationName):
        res = (
            self.supabase
            .table("nations")
            .select("*")
            .eq("Name", nationName)
            .execute()
        )

        if not res.data:
            raise ValueError(f"Nation '{nationName}' not found")

        return res.data[0]

    def updateNation(self, nationName, changes):
        return (
            self.supabase
            .table("nations")
            .update(changes)
            .eq("Name", nationName)
            .execute()
        )

    # ---------- Territories ----------

    def getNationTerr(self, nationName):
        res = (
            self.supabase
            .table("territories")
            .select("*")
            .eq("Nation", nationName)
            .execute()
        )

        return res.data

    # ---------- Units ----------

    def createUnit(self, unit):
        return (
            self.supabase
            .table("units")
            .insert(unit)
            .execute()
        )

    def getUnitCounters(self):
        res = (
            self.supabase
            .table("unitcounters")
            .select("*")
            .execute()
        )

        return {
            row["id"]: row["count"]
            for row in res.data
        }

    def incrementUnitCounters(self, unit_id):
      res = self.supabase.table("unitcounters").select("count").eq("id", unit_id).execute()

      if not res.data:
        self.supabase.table("unitcounters").insert({"id": unit_id, "count": 1}).execute()
        return 1

      newcount = res.data[0]["count"] + 1
      self.supabase.table("unitcounters").update({"count": newcount}).eq("id", unit_id).execute()

      return newcount
    
    # ---------- Interactions ----------
    def getInteraction(self, fromNation, toNation, interactionType):
      res = self.supabase.table("interactions").select("*").eq("from", fromNation).eq("to", toNation).eq("type", interactionType).execute()

      if res.data:
          return res.data[0]

      return None
    
    def createInteraction(self, fromNation, toNation, interactionType, details=None):
      if details is None:
          details = {}

      res = self.supabase.table("interactions").insert({
              "from": fromNation,
              "to": toNation,
              "type": interactionType,
              "details": details
          }).execute()

      return res.data[0]
    
    def deleteInteraction(self, interactionId):
      self.supabase.table("interactions").delete().eq("id", interactionId).execute()
    
    # ---------- Game Data ----------

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

    # ---------- Game Time ----------

    def gameTime(self):
        return 100