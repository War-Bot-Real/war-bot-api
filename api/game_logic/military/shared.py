from api.game_logic.shared import calcDistance, pxToKm, quadify
from api.models import Territory, Unit

def getUnitData(gameData, unittype, unitData = None):
  if not unitData:
    unitData = gameData.getDefaultGameData()["Units"]
  for domain in unitData:
    for unit in unitData[domain]:
      if unit.lower() == unittype.lower() or unitData[domain][unit]["Short Form"] == unittype.upper():
        return unit, unitData[domain][unit]
  return None, None

def getDomain(gameData, unittype, unitData = None):
  if not unitData:
    unitData = gameData.getDefaultGameData()["Units"]
  for domain in unitData:
    if unittype in unitData[domain]:
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

def getCapacity(gameData, unit, unitData=None):
    data = getUnitData(gameData, unit.type, unitData)[1]
    return unit.quantity * data.get("Capacity", 0)
  
def getAllBorders(gameData, tile, unitData=None):
    borders = tile.bordering.copy()

    if isinstance(tile, Territory):
        borders += tile.coast

        for unit in gameData.getUnits():
            if unit.location == tile.name and getCapacity(gameData, unit, unitData) > 0:
                borders.append(unit.name)
    else:
        for territory in gameData.getAllTerr():
            if tile.name in territory.coast:
                borders.append(territory.name)

    return borders
  
def inRange(gameData, plane, target, roundTrip=True, unitData=None):
    if plane.location in getAllBorders(gameData, target, unitData):
        return True

    planeData = getUnitData(gameData, plane.type, unitData)[1]
    unitRange = planeData["Range"]

    location = station(gameData, plane)

    if location is None:
        return False

    if isinstance(location, Unit):
        location = station(gameData, location)

        if location is None:
            return False

        if location.name in getAllBorders(gameData, target, unitData):
            return True

    distance = calcDistance(location, target)

    if roundTrip:
        distance *= 2

    return pxToKm(gameData, distance) < unitRange


def canTakeoff(gameData, plane: Unit):
  s = station(gameData, plane)
  if isinstance(s, Unit):
    if s.type == "Aircraft Carrier":
      return True
    return False
  if isinstance(s, Territory):
    if "Airport" in s.buildings or "Airstrip" in s.buildings:
      return True
  return False #Shouldn't ever reach here

def findOwner(gameData, sea, unitData=None):
    for unit in gameData.getUnits():
        if unit.location == sea.name and getDomain(gameData, unit.type, unitData) == "Naval" and unit.type != "Submarine":
            return gameData.getNation(unit.nation)
    return None

def findCoastOccupant(gameData, territory, unitData=None):
    for unit in gameData.getUnits():
        if unit.location == territory.name and getDomain(gameData, unit.type, unitData) == "Naval":
            return gameData.getNation(unit.nation)
    return None

def findFuelRequired(gameData, unitlist: list[Unit], action: str, unitData=None) -> float:
    fuelRequired = 0.0

    for unit in unitlist:
        data = getUnitData(gameData, unit.type, unitData)[1]
        fuelRequired += data["Fuel"][action.title()] * unit.quantity / data["Each"]

    return fuelRequired

def getLoad(gameData, unit: Unit) -> list[Unit]:
    return [loadedUnit for loadedUnit in gameData.getUnits() if loadedUnit.location == unit.name]

def antiAirDef(gameData, unit: Unit, unitData=None) -> int | float:
    domain = getDomain(gameData, unit.type, unitData)
    unitdata = getUnitData(gameData, unit.type, unitData)[1]

    if domain != "Naval":
        if unit.type in ["Fighter", "Anti-Air"]:
            return unitdata["Aircraft Interception"] * unit.quantity / unitdata["Each"]
        return 0

    for loadedUnit in getLoad(gameData, unit):
        if loadedUnit.type == "Anti-Air":
            return unitdata["Anti-Air Defense"] * unit.quantity / unitdata["Each"]

    return 0

def getNavalPower(gameData, navalData = None) -> dict[str, int | float]:
    if not navalData:
      navalData = gameData.getDefaultGameData()["Units"]["Naval"]
    return {unitType: data["Power"] for unitType, data in navalData.items()}

def devastationRatio():
    return 0.1 #how much each division raises the War Devastation stat by

def convertIntToBattleId(num: int):
  letters = ['q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']

  asStr = quadify(num)
  id = ""
  passed = True
  for i in asStr:
    if i == "0" and passed:
      id += "0"
      continue
    passed = False
    id += letters[int(i) - 1]
  
  return id
  
cooldownConstants = {
  "loading": 300
}

cooldownMultiplier = {
  "Attacking": 1.25,
  "Loading": 1.05,
  "Bombard": 1.1,
  "Integration": 500,
  "Rail": 450 #how many seconds it takes to move something 100 pixels
}

def findCooldown(gameData, unitType: str, terrain: int | str, stability: int | float, unitData=None) -> float:
    mapName = gameData.getMapName()
    if stability > 1:
        stabEffect = 4.0 / stability ** (1 / 3)
    else:
        stabEffect = -1 / 40 * stability + 161 / 40

    domain = getDomain(gameData, unitType, unitData)
    data = getUnitData(gameData, unitType, unitData)[1]
    if domain == "Naval":
        return data["Cooldown"] * stabEffect

    if terrain in ["Transporter", "Aircraft Carrier"]:
        return cooldownConstants["loading"]

    if isinstance(terrain, str):
        terrains = gameData.getMapData(mapName)["Terrains"]
        terrain = next((i for i, item in enumerate(terrains) if item["Name"] == terrain), terrain)

    exponent = data["Speed"]["Exponent"]
    divisor = data["Speed"]["Divisor"]
    return 1000 * (terrain + 3) ** exponent / divisor * stabEffect

def getCapacity(gameData, unit: Unit, unitData=None) -> float:
    return getUnitData(gameData, unit.type, unitData)[1].get("Capacity", 0)

def findWeight(gameData, units: list[Unit], unitData=None):
  weight = 0
  for unit in units:
    data = getUnitData(gameData, unit.type, unitData)[1]
    weight += unit.quantity * data["Weight"] / data["Each"]
  return weight

def dead(gameData, nation, unitData=None) -> bool:
    if gameData.getNationTerr(nation.name):
        return False
    for u in gameData.getUnits():
        if u.nation == nation.name and getDomain(gameData, u.type, unitData) != "Naval":
            return False
    return True