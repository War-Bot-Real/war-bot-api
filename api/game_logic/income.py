economicActivity = {
  "Unintegrated": 0.5,
  "Radar Station": 1.00,
  "Fortress": 1.0,
  "Airstrip": 1.0,
  "Railway Station": 1.02,
  "Oil Drill": 1.05,
  "Steel Factory": 1.05,
  "Fuel Refinery": 1.05,
  "Airport": 1.1,
  "Capital": 1.5,
  "Financial Center": 2
}

def calcTerritoryRev(gameTime, territory, nation) -> float:
  r = territory["Population"] ** 0.8
  for b in territory["Buildings"]:
    if "Statue" not in b:
      r *= economicActivity[b]
  if territory["Name"] == nation["Capital"]:
    r *= economicActivity["Capital"]
  if territory["Integrated"] > gameTime:
    r *= economicActivity["Unintegrated"]
  return r * calcStabRevEffect(nation["Stability"])
  
def calcStabRevEffect(stab: int):
  return 0.05 * stab ** 0.7 if stab > 0 else 0.05 * stab

def calcRevByTerr(gameData, nation):
  terr = gameData.getNationTerr(nation["Name"])
  rev = {}
  for t in terr:
    rev[t["Name"]] = round(calcTerritoryRev(gameData.gameTime(), t, nation) * nation["Tax Rate"] / 2000, 2)
  return rev

def collectIncome(gameData, nation):
    revByTerr = calcRevByTerr(gameData, nation)
    revenue = round(sum(revByTerr.values()), 2)
    balance = round(nation["Balance"] + revenue, 2)

    gameData.updateNation(
        nation["Name"],
        {
            "Balance": nation["Balance"] + revenue
        }
    )

    return {"Income": revenue, "Balance": balance}