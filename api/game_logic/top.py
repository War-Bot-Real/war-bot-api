from api.repositories.gameData import GameData
from api.models import Nation
from api.game_logic.shared import formatList
from api.game_logic.income import calcNationRev

def options():
  return ["area", "population", "coal", "iron", "power"]

def calcNationPower(gameData: GameData, nation: Nation | str) -> float:
    if isinstance(nation, str):
      nation = gameData.getNation(nation)

    territories = gameData.getAllTerr()
    worldArea = sum(terr.area for terr in territories)
    nationArea = sum(terr.area for terr in gameData.getNationTerr(nation.name))
    if worldArea == 0:
        return 0
    
    return calcPower(calcNationRev(gameData, nation), nationArea, worldArea)

def calcPower(revenue, nationArea, worldArea):
  power = revenue / 2_000_000 + nationArea / worldArea / 0.3
  return max(power, 0)

def top(gameData: GameData, category):
  if category not in options():
    raise ValueError(f"Invalid option. The valid options to rank by are {formatList(options(), 'or')}.")
  ranking = {}
  for t in gameData.getAllTerr():
    if t.nation not in ranking:
      ranking[t.nation] = 0
    
    if category in ["area", "power"]:
      ranking[t.nation] += t.area
    elif category == "population":
      ranking[t.nation] += t.pop
    elif category == "coal":
      ranking[t.nation] += t.resources.get("Coal", 0)
    elif category == "iron":
      ranking[t.nation] += t.resources.get("Iron", 0)

  if category == "power":
    for i in ranking:
      ranking[i] = calcNationPower(gameData, i)
  
  ranking = sorted(ranking.items(), key=lambda kv: kv[1], reverse=True)
  ranking = dict(ranking)
  return ranking