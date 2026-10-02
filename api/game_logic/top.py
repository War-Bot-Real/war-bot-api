from api.repositories.gameData import GameData
from api.game_logic.shared import formatList

def options():
  return ["area", "population", "coal", "iron"]

def top(gameData: GameData, category):
  if category not in options():
    raise ValueError(f"Invalid option. The valid options to rank by are {formatList(options(), "or")}.")
  ranking = {}
  for t in gameData.getAllTerr():
    if t.nation not in ranking:
      ranking[t.nation] = 0
    
    if category == "area":
      ranking[t.nation] += t.area
    elif category == "population":
      ranking[t.nation] += t.pop
    elif category == "coal":
      ranking[t.nation] += t.resources["Coal"]
    elif category == "iron":
      ranking[t.nation] += t.resources["Iron"]
  ranking = sorted(ranking.items(), key=lambda kv: kv[1], reverse=True)
  ranking = dict(ranking)
  return ranking