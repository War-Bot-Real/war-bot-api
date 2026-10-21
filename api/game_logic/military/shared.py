from api.game_logic.shared import calcDistance, pxToKm
from models import Territory, Unit

def getUnitData(gameData, unittype):
  allunits = gameData.getDefaultGameData()["Units"]
  for domain in allunits:
    for unit in allunits[domain]:
      if unit.lower() == unittype.lower() or allunits[domain][unit]["Short Form"] == unittype.upper(): 
        return unit, allunits[domain][unit]
  return None, None

def getDomain(gameData, unittype):
  allunits = gameData.getDefaultGameData()["Units"]
  for domain in allunits:
    if unittype in allunits[domain]:
      return domain
  return None

def station(gameData, division):
    if isinstance(division, str):
        units = gameData.getUnit(division)
        if not units:
            return None
        division = units[0]

    try:
        return gameData.getTerritory(division.location)
    except ValueError:
        pass

    try:
        return gameData.getSea(division.location)
    except ValueError:
        pass

    units = gameData.getUnit(division.location)
    if units:
        return units[0]

    return None

def getCapacity(gameData, unit):
    data = getUnitData(gameData, unit.type)[1]
    return unit.quantity * data.get("Capacity", 0)
  
def getAllBorders(gameData, tile):
    borders = tile.bordering.copy()

    if isinstance(tile, Territory):
        borders += tile.coast

        for unit in gameData.getUnits():
            if unit.location == tile.name and getCapacity(gameData, unit) > 0:
                borders.append(unit.name)
    else:
        for territory in gameData.getAllTerr():
            if tile.name in territory.coast:
                borders.append(territory.name)

    return borders
  
def inRange(gameData, plane, target, roundTrip=True):
    if plane.location in getAllBorders(gameData, target):
        return True

    unitData = getUnitData(gameData, plane.type)[1]
    unitRange = unitData["Range"]

    location = station(gameData, plane)

    if location is None:
        return False

    if isinstance(location, Unit):
        location = station(gameData, location)

        if location is None:
            return False

        if location.name in getAllBorders(gameData, target):
            return True

    distance = calcDistance(location, target)

    if roundTrip:
        distance *= 2

    return pxToKm(gameData, distance) < unitRange


def canTakeoff(plane: Unit):
  s = station(plane)
  if isinstance(s, Unit):
    if s.type == "Aircraft Carrier":
      return True
    return False
  if isinstance(s, Territory):
    if "Airport" in s.buildings or "Airstrip" in s.buildings:
      return True
  return False #Shouldn't ever reach here

def findOwner(gameData, sea):
    for unit in gameData.getUnits():
        if unit.location == sea.name and getUnitData(gameData, unit.type)[0] == "Naval" and unit.type != "Submarine":
            return gameData.getNation(unit.nation)
    return None

def findCoastOccupant(gameData, territory):
    for unit in gameData.getUnits():
        if unit.location == territory.name and getUnitData(gameData, unit.type)[0] == "Naval":
            return gameData.getNation(unit.nation)
    return None

def findFuelRequired(gameData, unitlist: list[Unit], action: str) -> float:
    fuelRequired = 0.0

    for unit in unitlist:
        data = getUnitData(gameData, unit.type)[1]
        fuelRequired += data["Fuel"][action.title()] * unit.quantity / data["Each"]

    return fuelRequired

def getLoad(gameData, unit: Unit) -> list[Unit]:
    return [loadedUnit for loadedUnit in gameData.getUnits() if loadedUnit.location == unit.name]

def antiAirDef(gameData, unit: Unit) -> int | float:
    domain = getDomain(gameData, unit.type)
    unitdata = getUnitData(gameData, unit.type)[1]

    if domain != "Naval":
        if unit.type in ["Fighter", "Anti-Air"]:
            return unitdata["Aircraft Interception"] * unit.quantity / unitdata["Each"]
        return 0

    for loadedUnit in getLoad(gameData, unit):
        if loadedUnit.type == "Anti-Air":
            return unitdata["Anti-Air Defense"] * unit.quantity / unitdata["Each"]

    return 0

def getNavalPower(gameData) -> dict[str, int | float]:
    navalData = gameData.getDefaultGameData()["Units"]["Naval"]
    return {unitType: data["Power"] for unitType, data in navalData.items()}