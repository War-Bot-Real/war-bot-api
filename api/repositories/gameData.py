import requests
from supabase import Client
from datetime import datetime
from zoneinfo import ZoneInfo
from supabase import Client
from api.realtime import broadcast
from api.game_logic.shared import findItem, quadify
from api.models import Territory, Sea, Nation, Unit

EPOCH = datetime(1970, 1, 1, tzinfo=ZoneInfo("America/Toronto"))

class GameData:

    def __init__(self, supabase: Client):
        self.supabase = supabase

    # ---------- Nations ----------
    def getAllNations(self) -> list[Nation]:
        res = self.supabase.table("nations").select("*").execute()

        return [Nation(n) for n in res.data]

    def getNation(self, nationName: str) -> Nation:
        matches = findItem(nationName, self.getAllNations(), "name")

        if not matches:
            raise ValueError(f"Nation '{nationName}' not found")

        if len(matches) > 1:
            raise ValueError(f"Multiple nations found: {', '.join(n.name for n in matches)}")
          
        return matches[0]

    def updateNation(self, nationName, changes):
        # changes is a dict of column names and their new values, e.g. {"balance": 1000, "last": {...}}
        return self.supabase.table("nations").update(changes).eq("name", nationName).execute()

    # ---------- Territories / Seas ----------
    
    def getAllTerr(self) -> list[Territory]:
        res = self.supabase.table("territories").select("*").execute()

        return [Territory(t) for t in res.data]

    def getNationTerr(self, nationName: str) -> list[Territory]:
        res = self.supabase.table("territories").select("*").eq("nation", nationName).execute()

        return [Territory(t) for t in res.data]
    
    def getTerritory(self, name: str) -> Territory:
      matches = findItem(name, self.getAllTerr(), "name")

      if not matches:
          raise ValueError(f"Territory '{name}' not found")

      if len(matches) > 1:
          raise ValueError(f"Multiple territories found for '{name}'")

      return matches[0]
    
    def getAllSeas(self) -> list[Sea]:
        res = self.supabase.table("seas").select("*").execute()

        return [Sea(s) for s in res.data]
      
    def getSea(self, name: str) -> Sea:
      matches = findItem(name, self.getAllSeas(), "name")

      if not matches:
          raise ValueError(f"Sea '{name}' not found")

      if len(matches) > 1:
          raise ValueError(f"Multiple seas found for '{name}'")

      return matches[0]

    # ---------- Units ----------

    def createUnit(self, unit):
        self.supabase.table("units").insert(unit).execute()
        
    def getUnit(self, id, throwError = False):
      units = self.getUnits()
      for unit in units:
          if unit.name.lower() == id.lower():
              return unit

      matched = None
      shortforms = self.getUnitShortForms()
      for shortForm in shortforms.keys():
          if id.lower().endswith(shortForm.lower()):
              matched = id[-len(shortForm):]
              break

      if matched:
          id = quadify(id.removesuffix(matched)) + matched.upper()
          for unit in units:
              if unit.name.upper() == id:
                  return unit
                
      if throwError:
        raise ValueError(f"Unit '{id}' not found.")
      return None
              
    def getUnits(self, nation=None):
        query = self.supabase.table("units").select("*")

        if nation is not None:
            territories = [t.name for t in self.getNationTerr(nation)]
            query = query.or_(f'nation.ilike.{nation},location.in.({",".join(territories)})')

        return [Unit(u) for u in query.execute().data]

    def updateUnit(self, id, changes):
        self.supabase.table("units").update(changes).eq("name", id).execute()

    def deleteUnit(self, id):
        self.supabase.table("units").delete().eq("name", id).execute()

    def getUnitCounters(self):
        res = self.supabase.table("unitcounters").select("*").execute()

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
    
    # ---------- Treaties ----------
    
    def createTreaty(self, treaty):
        res = self.supabase.table("treaties").insert(treaty).execute()
        return res.data[0]
    
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
    
    def getWars(self):
        res = self.supabase.table("interactions").select("*").eq("type", "war").execute()
        return res.data

    def atWar(self, nation1, nation2):
        for war in self.getWars():
            aggressors = war["details"]["aggressors"]
            defenders = war["details"]["defenders"]

            if nation1 in aggressors and nation2 in defenders:
                return True
            if nation2 in aggressors and nation1 in defenders:
                return True

        return False
    
    # ---------- Messages ----------
    
    def createMessage(self, sender, recipient, messageType, message, details = {}):
        res = self.supabase.table("messages").insert({
            "sender": sender,
            "recipient": recipient,
            "type": messageType,
            "message": message,
            "details": details
        }).execute()

        result = res.data[0]
        self.broadcastMessage(result)

        return result
      
    def broadcastMessage(self, message):
      topic = f"{message['recipient']}:events" if message["recipient"] else "world:events"

      if message["type"] in ["news", "message"]:
        event = message["type"]
      else:
        event = "notification"

      broadcast(topic, event, message)
    
    # ---------- Game Data ----------

    def getDefaultGameData(self):
        res = self.supabase.storage.from_("info").create_signed_url("data.json", expires_in=60)

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
    
    def getUnitShortForms(self):
      masterdata = self.getDefaultGameData()
      shortforms = {}
      for domain in masterdata["Units"]:
        for i in masterdata["Units"][domain]:
          shortforms[masterdata["Units"][domain][i]["Short Form"]] = i
      return shortforms

    # ---------- Game Time ----------

    def gameSeconds(self, date):
        data = self.getDefaultGameData()
        activeStart = int(data["Settings"]["Admin"]["Truce End"]["Value"])
        activeEnd = int(data["Settings"]["Admin"]["Truce Start"]["Value"])

        days = (date.date() - EPOCH.date()).days
        activeSecsPerDay = (24 - activeStart + activeEnd) * 3600
        seconds = days * activeSecsPerDay

        if date.hour >= activeStart:
            seconds += (date.hour - activeStart) * 3600 + date.minute * 60 + date.second
        elif date.hour < activeEnd:
            seconds += (24 - activeStart + date.hour) * 3600 + date.minute * 60 + date.second

        return seconds

    def gameTime(self):
        return self.gameSeconds(datetime.now(ZoneInfo("America/Toronto")))