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
            "Inventory": inventory
        }
    )

    # Ground units start active
    active = unitDomain == "Ground"

    # Create deployed unit
    gameData.createUnit({
        "Name": unitid,
        "Type": unit,
        "Quantity": quantity * unitdata["Each"],
        "Nation": nation.name,
        "Location": territory.name,
        "Active": active,
        "TiredUntil": 0
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
        units = [u for u in units if getDomain(gameData, u["Type"]) == domain]

    if territoryNames is not None:
        units = [u for u in units if u["Location"] in territoryNames]

    territories = {}
    abroad = {}
    carriers = {}
    nationTerritories = [t.name for t in gameData.getNationTerr(nation.name)]
    
    for unit in units:
        location = unit["Location"]
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

        if unit["Nation"] != nation.name:
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
            unit["Type"] == base["Type"]
            and unit["Location"] == base["Location"]
            and unit["Active"] == base["Active"]
        ):
            mergeable.append(unit)
        else:
            failed.append(unit["Name"])

    if not mergeable:
        raise ValueError("No units can be merged. Units must have the same type, location, and active status.")
    
    allUnits = gameData.getUnits()
    for unit in mergeable:
        for loadedUnit in allUnits:
            if loadedUnit["Location"] == unit["Name"]:
                gameData.updateUnit(loadedUnit["Name"], {
                    "Location": base["Name"]
                })

    quantity = base["Quantity"] + sum(unit["Quantity"] for unit in mergeable)
    tiredUntil = max([base["TiredUntil"]] + [unit["TiredUntil"] for unit in mergeable])

    gameData.updateUnit(base["Name"], {
        "Quantity": quantity,
        "TiredUntil": tiredUntil
    })

    for unit in mergeable:
        gameData.deleteUnit(unit["Name"])

    return {
        "unit": base["Name"],
        "merged": [unit["Name"] for unit in mergeable],
        "failed": failed
    }

def splitUnit(gameData, nation, unitName, divisions=2):
    unit = gameData.getUnit(unitName)

    if not unit:
        raise ValueError(f"Unit '{unitName}' not found")

    if unit["Nation"] != nation.name:
        raise ValueError("You don't own that unit")

    if divisions < 2:
        raise ValueError("You must split into at least 2 divisions")

    quantity = unit["Quantity"] // divisions
    unitData = getUnitData(gameData, unit["Type"])[1]

    if quantity < unitData["Minimum"]:
        raise ValueError("The resulting divisions would be too small")

    loaded = gameData.getUnits()
    if any(u["Location"] == unit["Name"] for u in loaded):
        raise ValueError("Can't split loaded carriers")

    remainder = unit["Quantity"] - quantity * divisions

    gameData.updateUnit(unit["Name"], {
        "Quantity": quantity + remainder
    })

    newUnits = []

    for _ in range(divisions - 1):
        count = gameData.incrementUnitCounters(unitData["Short Form"])
        unitId = quadify(count) + unitData["Short Form"]

        newUnit = {
            "Name": unitId,
            "Type": unit["Type"],
            "Quantity": quantity,
            "Nation": unit["Nation"],
            "Location": unit["Location"],
            "TiredUntil": unit["TiredUntil"],
            "Active": unit["Active"]
        }

        gameData.createUnit(newUnit)
        newUnits.append(newUnit)

    return {
        "original": unit["Name"],
        "divisions": [unit["Name"]] + [u["Name"] for u in newUnits]
    }

def disbandUnit(gameData, nation, unitName):
    unit = gameData.getUnit(unitName)

    if not unit:
        raise ValueError(f"Unit '{unitName}' not found")

    ownUnit = unit["Nation"] == nation.name

    if not ownUnit:
        territory = gameData.getTerritory(unit["Location"])

        if territory.nation != nation.name:
            raise ValueError("That unit is not yours")

        unitData = getUnitData(gameData, unit["Type"])[0]

        if unitData == "Naval":
            raise ValueError("You cannot disband another nation's naval unit")

        if unit["Nation"] in nation.diplomacy["Trusted"]:
            raise ValueError(f"You currently trust {unit['Nation']}, so you cannot disband their unit")

    # TODO: Prevent disbanding units belonging to a nation that recently broke a trusted agreement until their evacuation truce expires.

    loaded = [u for u in gameData.getUnits() if u["Location"] == unit["Name"]]
    disbanded = [unit["Name"]]

    gameData.deleteUnit(unit["Name"])

    for loadedUnit in loaded:
        gameData.deleteUnit(loadedUnit["Name"])
        disbanded.append(loadedUnit["Name"])

    return {
        "unit": unit["Name"],
        "disbanded": disbanded
    }