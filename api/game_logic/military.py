from api.game_logic.shared import quadify

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

def deployUnit(gameData, nation, territory, unit, quantity):
    if not isinstance(quantity, int):
        raise ValueError("Use an integer!")

    if quantity == 0:
        raise ValueError("You can't deploy 0 troops")

    if quantity < 0:
        raise ValueError("You can't deploy negative troops")

    # Territory ownership
    if territory.nation != nation.name:
        raise ValueError(f'{territory.name} is owned by {territory.nation}')

    # Territory integration
    if territory.integrated > gameData.gameTime():
        raise ValueError("This territory has not been integrated yet")

    # Find unit
    unit, unitdata = getUnitData(gameData, unit)
    if unitdata is None:
        raise ValueError("Invalid Unit Type")

    inventoryName = unit

    # if unitdata["Each"] > 1:
    #     inventoryName += " Division"
    if inventoryName not in nation.inventory:
        raise ValueError(f"Nation does not have any {inventoryName}")

    if nation.inventory[inventoryName] < quantity:
        raise ValueError(f"Nation does not have enough {inventoryName}")

    unitDomain = getDomain(gameData, unit)
    
    if unitDomain == "Naval":
        # Coast occupant logic will be implemented later
        pass

    if unitDomain == "Air":
        if "Airport" not in territory.buildings:
            raise ValueError(f'{territory.name} must have an airport for you to deploy an aircraft')


    # Generate unit ID
    shortForm = unitdata["Short Form"]

    unitid = quadify(gameData.incrementUnitCounters(shortForm)) + shortForm

    # Remove units from inventory
    inventory = nation.inventory.copy()
    inventory[inventoryName] -= quantity

    gameData.updateNation(
        nation.name,
        {
            "inventory": inventory
        }
    )

    # Ground units start active
    active = unitDomain == "Ground"

    # Create deployed unit
    gameData.createUnit({
        "name": unitid,
        "type": unit,
        "quantity": quantity * unitdata["Each"],
        "nation": nation.name,
        "location": territory.name,
        "active": active,
        "tiredUntil": 0
    })


    return {
        "unit": unitid,
        "quantity": quantity * unitdata["Each"],
        "location": territory.name
    }

def getForces(gameData, nation, domain=None, theater=None):
    masterdata = gameData.getDefaultGameData()

    if domain is not None:
        for d in masterdata["Units"]:
            if d.lower() == domain.lower():
                domain = d
                break
        else:
            raise ValueError("Invalid domain")

    territoryNames = None

    if theater != None:     
      theaters = nation.theaters

      matches = [t for t in theaters if theater.lower() in t.lower()]

      if not matches:
          raise ValueError("Invalid theater")
      if len(matches) > 1:
          raise ValueError("Multiple theaters found")

      theater = matches[0]
      territoryNames = theaters[theater]

    units = gameData.getUnits(nation.name)

    if domain is not None:
        units = [u for u in units if getDomain(gameData, u["type"]) == domain]

    if territoryNames is not None:
        units = [u for u in units if u["location"] in territoryNames]

    territories = {}
    abroad = {}
    carriers = {}
    nationTerritories = [t.name for t in gameData.getNationTerr(nation.name)]
    
    for unit in units:
        location = unit["location"]
        potentialUnit = gameData.getUnit(location)

        if location in nationTerritories:
            territories.setdefault(location, []).append(unit)
        elif potentialUnit != None:
            carriers.setdefault(potentialUnit, []).append(unit)
        else:
            abroad.setdefault(location, []).append(unit)

    return {
        "territories": territories,
        "abroad": abroad,
        "carriers": carriers
    }

def mergeUnits(gameData, nation, unitNames):
    if len(unitNames) < 2:
        raise ValueError("You must specify at least two units to merge")

    units = []
    invalid = []

    for name in unitNames:
        unit = gameData.getUnit(name)

        if not unit:
            invalid.append(name)
            continue

        if unit["nation"] != nation.name:
            invalid.append(name)
            continue

        units.append(unit)

    if invalid:
        raise ValueError(f"Invalid or unowned units: {', '.join(invalid)}")

    base = units[0]
    mergeable = []
    failed = []

    for unit in units[1:]:
        if (
            unit["type"] == base["type"]
            and unit["location"] == base["location"]
            and unit["active"] == base["active"]
        ):
            mergeable.append(unit)
        else:
            failed.append(unit["name"])

    if not mergeable:
        raise ValueError("No units can be merged. Units must have the same type, location, and active status.")
    
    allUnits = gameData.getUnits()
    for unit in mergeable:
        for loadedUnit in allUnits:
            if loadedUnit["location"] == unit["name"]:
                gameData.updateUnit(loadedUnit["name"], {
                    "location": base["name"]
                })

    quantity = base["quantity"] + sum(unit["quantity"] for unit in mergeable)
    tiredUntil = max([base["tiredUntil"]] + [unit["tiredUntil"] for unit in mergeable])

    gameData.updateUnit(base["name"], {
        "quantity": quantity,
        "tiredUntil": tiredUntil
    })

    for unit in mergeable:
        gameData.deleteUnit(unit["name"])

    return {
        "unit": base["name"],
        "merged": [unit["name"] for unit in mergeable],
        "failed": failed
    }

def splitUnit(gameData, nation, unitName, divisions=2):
    unit = gameData.getUnit(unitName)

    if not unit:
        raise ValueError(f"Unit '{unitName}' not found")

    if unit["nation"] != nation.name:
        raise ValueError("You don't own that unit")

    if divisions < 2:
        raise ValueError("You must split into at least 2 divisions")

    quantity = unit["quantity"] // divisions
    unitData = getUnitData(gameData, unit["type"])[1]

    if quantity < unitData["Minimum"]:
        raise ValueError("The resulting divisions would be too small")

    loaded = gameData.getUnits()
    if any(u["location"] == unit["name"] for u in loaded):
        raise ValueError("Can't split loaded carriers")

    remainder = unit["quantity"] - quantity * divisions

    gameData.updateUnit(unit["name"], {
        "quantity": quantity + remainder
    })

    newUnits = []

    for _ in range(divisions - 1):
        count = gameData.incrementUnitCounters(unitData["Short Form"])
        unitId = quadify(count) + unitData["Short Form"]

        newUnit = {
            "name": unitId,
            "type": unit["type"],
            "quantity": quantity,
            "nation": unit["nation"],
            "location": unit["location"],
            "tiredUntil": unit["tiredUntil"],
            "active": unit["active"]
        }

        gameData.createUnit(newUnit)
        newUnits.append(newUnit)

    return {
        "original": unit["name"],
        "divisions": [unit["name"]] + [u["name"] for u in newUnits]
    }

def disbandUnit(gameData, nation, unitName):
    unit = gameData.getUnit(unitName)

    if not unit:
        raise ValueError(f"Unit '{unitName}' not found")

    ownUnit = unit["nation"] == nation.name

    if not ownUnit:
        territory = gameData.getTerritory(unit["location"])

        if territory.nation != nation.name:
            raise ValueError("That unit is not yours")

        unitData = getUnitData(gameData, unit["type"])[0]

        if unitData == "Naval":
            raise ValueError("You cannot disband another nation's naval unit")

        if unit["nation"] in nation.diplomacy["Trusted"]:
            raise ValueError(f"You currently trust {unit['Nation']}, so you cannot disband their unit")

    # TODO: Prevent disbanding units belonging to a nation that recently broke a trusted agreement until their evacuation truce expires.

    loaded = [u for u in gameData.getUnits() if u["location"] == unit["name"]]
    disbanded = [unit["name"]]

    gameData.deleteUnit(unit["name"])

    for loadedUnit in loaded:
        gameData.deleteUnit(loadedUnit["name"])
        disbanded.append(loadedUnit["name"])

    return {
        "unit": unit["name"],
        "disbanded": disbanded
    }