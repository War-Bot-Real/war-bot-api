import math
from api.game_logic.top import calcPower

def getAllBuildings(gameData) -> list[str]:
    return list(gameData.getDefaultGameData()["Buildings"])


def financialCenterLimit(gameData, nation) -> int:
    power = calcPower(gameData, nation)
    if power <= 0:
        return 0
    return max(int(math.floor(math.log(power, 2) + 3)), 1)
  
def executeBuild(gameData, nation, territory, building: str):
    if territory.nation != nation.name:
        raise ValueError("You cannot build in another nation's territory.")

    if not building:
        raise ValueError("Specify what to build.")

    building = building.lower()
    matches = [b for b in getAllBuildings(gameData) if building in b.lower()]
    if not matches:
        raise ValueError("Not a valid building.")
    if len(matches) > 1:
        raise ValueError("Multiple buildings matched. Be more specific.")

    building = matches[0]

    if building == "Statue":
        raise ValueError("Statue construction is not implemented yet.")

    resources = dict(nation.resources or {})
    if resources.get(building, 0) <= 0:
        raise ValueError(f"You don't have any {building} in your inventory.")

    if building in ["Oil Drill", "Fuel Refinery", "Financial Center", "Railway Center"] and territory.devastation > 10:
        raise ValueError(f"You cannot build a {building} on territories with a devastation of 10+!")

    buildings = list(territory.buildings or [])
    if building in buildings:
        raise ValueError(f"You already have a {building} in {territory.name}.")

    if building == "Financial Center":
        count = sum(1 for terr in gameData.getNationTerr(nation.name) if "Financial Center" in terr.buildings)
        if count >= financialCenterLimit(gameData, nation):
            raise ValueError("You have reached your limit for building financial centers!")

    resources[building] -= 1
    buildings.append(building)

    gameData.updateNation(nation.name, {"resources": resources})
    gameData.updateTerritory(territory.name, {"buildings": buildings})

    return {
        "building": building,
        "territory": territory.name,
        "remaining": resources[building]
    }
