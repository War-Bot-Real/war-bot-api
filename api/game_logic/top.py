from api.gameData import GameData
from api.game_logic.shared import formatList

def options():
  return ["area", "population", "coal", "iron"]

def top(gameData: GameData, category):
  if category not in options():
    raise ValueError(f"Invalid option. The valid options to rank by are {formatList(options(), "or")}.")
  ranking = {}
  for t in gameData.getAllTerr():
    if t["Nation"] not in ranking:
      ranking[t["Nation"]] = 0
    
    if category == "area":
      ranking[t["Nation"]] += t["Area"]
    elif category == "population":
      ranking[t["Nation"]] += t["Population"]
    elif category == "coal":
      ranking[t["Nation"]] += t["Resources"]["Coal"]
    elif category == "iron":
      ranking[t["Nation"]] += t["Resources"]["Iron"]
  ranking = sorted(ranking.items(), key=lambda kv: kv[1], reverse=True)
  ranking = dict(ranking)
  return ranking
      