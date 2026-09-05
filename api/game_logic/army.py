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
    if unittype in allunits[domain]:
      return allunits[domain][unittype]
  return None

def deployUnit(gameData, nation, territory, unit, quantity):
  if territory["Nation"] != nation["Name"]:
    raise ValueError(f'{territory["Name"]} is owned by {territory["Nation"]}')
  
  if unit not in nation["Inventory"]:
    raise ValueError(f"Nation does not have any {unit}")
   
  if nation["Inventory"][unit] < quantity:
    raise ValueError(f"Nation does not have enough {unit}")
  
  unitdata = getUnitData(gameData, unit)
  
  if unitdata == None:
    raise ValueError("Invalid Unit Type")
  
  unitid = quadify(gameData.incrementUnitCounters(unitdata["Short Form"])) + unitdata["Short Form"]
  
  return {
    "changes": {
        nation["Name"]: {
            "Inventory": Operation("add", -quantity, unit)
        }
    },

    "unit": {
        "Name": unitid,
        "Type": unit,
        "Quantity": quantity * unitdata["Each"],
        "Nation": nation["Name"],
        "Location": territory["Name"],
        "Active": True,
        "TiredUntil": 0
    }
  }
  