from api.models.Operation import Operation

def quadify(arg):
  if type(arg) == type(str()):
    if not arg.isdigit():
      return (arg)
  z = ""
  arg = str(arg)
  if len(arg) < 4:
    for i in range(4 - len(arg)):
      z += "0"
  z += arg
  return (z)

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
    if territory["Nation"] != nation["Name"]:
        raise ValueError(f'{territory["Name"]} is owned by {territory["Nation"]}')

    # Territory integration
    if territory["Integrated"] > gameData.gameTime():
        raise ValueError("This territory has not been integrated yet")

    # Find unit
    unit, unitdata = getUnitData(gameData, unit)
    if unitdata is None:
        raise ValueError("Invalid Unit Type")

    inventoryName = unit

    # if unitdata["Each"] > 1:
    #     inventoryName += " Division"
    if inventoryName not in nation["Inventory"]:
        raise ValueError(f"Nation does not have any {inventoryName}")

    if nation["Inventory"][inventoryName] < quantity:
        raise ValueError(f"Nation does not have enough {inventoryName}")

    unitDomain = getDomain(gameData, unit)
    
    if unitDomain == "Naval":
        # Coast occupant logic will be implemented later
        pass

    if unitDomain == "Air":
        if "Airport" not in territory["Buildings"]:
            raise ValueError(f'{territory["Name"]} must have an airport for you to deploy an aircraft')


    # Generate unit ID
    shortForm = unitdata["Short Form"]

    unitid = quadify(gameData.incrementUnitCounters(shortForm)) + shortForm

    # Remove units from inventory
    inventory = nation["Inventory"].copy()
    inventory[inventoryName] -= quantity

    gameData.updateNation(
        nation["Name"],
        {
            "Inventory": inventory
        }
    )

    # Ground units start active
    active = unitDomain == "Ground"

    # Create deployed unit
    gameData.createUnit({
        "Name": unitid,
        "Type": unitdata,
        "Quantity": quantity * unitdata["Each"],
        "Nation": nation["Name"],
        "Location": territory["Name"],
        "Active": active,
        "TiredUntil": 0
    })


    return {
        "unit": unitid,
        "quantity": quantity * unitdata["Each"],
        "location": territory["Name"]
    }