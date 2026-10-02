from api.game_logic.military import getUnitData
from api.game_logic.shared import calcDistance, pxToKm

def station(gameData, division):
    if isinstance(division, str):
        units = gameData.getUnit(division)
        if not units:
            return None
        division = units[0]

    try:
        return gameData.getTerritory(division["Location"])
    except ValueError:
        pass

    try:
        return gameData.getSea(division["Location"])
    except ValueError:
        pass

    units = gameData.getUnit(division["Location"])
    if units:
        return units[0]

    return None

def getCapacity(gameData, unit):
    data = getUnitData(gameData, unit["Type"])[1]
    return unit["Quantity"] * data.get("Capacity", 0)

def getAllBorders(gameData, tile):
    borders = tile["Bordering"].copy()

    if "Coast" in tile:
        borders += tile["Coast"]

        for unit in gameData.getUnits():
            if unit["Location"] == tile["Name"] and getCapacity(gameData, unit) > 0:
                borders.append(unit["Name"])
    else:
        for territory in gameData.getTerritories():
            if tile["Name"] in territory["Coast"]:
                borders.append(territory["Name"])

    return borders

def inRange(gameData, plane, target, roundTrip=True):
    if plane["Location"] in getAllBorders(gameData, target):
        return True

    unitData = getUnitData(gameData, plane["Type"])[1]
    unitRange = unitData["Range"]

    location = station(gameData, plane)

    if location is None:
        return False

    if "Type" in location:
        location = station(gameData, location)

        if location is None:
            return False

        if location["Name"] in getAllBorders(gameData, target):
            return True

    distance = calcDistance(location, target)

    if roundTrip:
        distance *= 2

    return pxToKm(gameData, distance) < unitRange