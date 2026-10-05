from api.models import Territory, Unit
from api.game_logic.military import getUnitData
from api.game_logic.shared import calcDistance, pxToKm

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