from api.repositories.gameData import GameData
from api.models import Nation
from api.game_logic.shared import formatList
from api.game_logic.income import calcNationRev, calcAllNationRevs

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

class RankedNation:
    def __init__(self, nation: str, flag: str, value: int | float):
        self.nation = nation
        self.flag = flag
        self.value = value

def top(gameData: GameData, category):
    if category not in options():
        raise ValueError(f"Invalid option. The valid options to rank by are {formatList(options(), 'or')}.")

    territories = gameData.getAllTerr()
    values = {}

    if category == "power":
        worldArea = sum(t.area for t in territories)
        nationAreas = {}
        for t in territories:
            nationAreas[t.nation] = nationAreas.get(t.nation, 0) + t.area

        revenues = calcAllNationRevs(gameData, territories)
        for nation in gameData.getAllNations():
            value = calcPower(revenues[nation.name], nationAreas.get(nation.name, 0), worldArea)
            values[nation.name] = RankedNation(nation.name, nation.flag, value)
    else:
        for t in territories:
            if t.nation not in values:
                values[t.nation] = 0

            if category == "area":
                values[t.nation] += t.area
            elif category == "population":
                values[t.nation] += t.pop
            elif category == "coal":
                values[t.nation] += t.resources.get("Coal", 0)
            elif category == "iron":
                values[t.nation] += t.resources.get("Iron", 0)

        for nation, value in values.copy().items():
            niq = gameData.getNation(nation)
            values[nation] = RankedNation(niq.name, niq.flag, value)

    ranking = list(values.values())
    ranking.sort(key=lambda x: x.value, reverse=True)
    return ranking