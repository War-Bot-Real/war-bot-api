from api.models.Operation import Operation

def getUnitData(gameData, unittype):
  allunits = gameData.getDefaultGameData()["Units"]
  for domain in allunits:
    if unittype in allunits[domain]:
      return allunits[domain][unittype]
  return None

def deployUnit(gameData, nation, territory, unit, quantity):
  if territory["Nation"] != nation["Name"]:
    raise ValueError(f'{nation["Name"]} does not own {territory["Name"]}')
  
  if unit not in nation["Inventory"]:
    raise ValueError(f"Nation does not have any {unit}")
   
  if nation["Inventory"][unit] < quantity:
    raise ValueError(f"Nation does not have enough {unit}")
  
  unitdata = getUnitData(gameData, unit)
  
  return {
    "changes": {
        nation["Name"]: {
            "Inventory": Operation("add", -quantity, unit)
        }
    },

    "unit": {
        "Type": unit,
        "Quantity": quantity * unitdata["Each"],
        "Nation": nation["Name"],
        "Location": territory["Name"],
        "Active": True,
        "TiredUntil": 0
    }
  }
  