from api.models import Territory, Nation

taxCooldown = 1800

fuelProduced = {
    "Coal": 0.75,
    "Oil": 2
}

steelFactory = {
    "Iron": -1,
    "Coal": -1,
    "Steel": 1
}


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

def calcTerritoryRev(gameTime, territory: Territory, nation: Nation) -> float:
    r = territory.pop ** 0.8
    for b in territory.buildings:
        if "Statue" not in b:
            r *= economicActivity[b]
    if territory.name == nation.capital:
        r *= economicActivity["Capital"]
    if territory.integrated > gameTime:
        r *= economicActivity["Unintegrated"]
    return r * calcStabRevEffect(nation.stability)

def calcNationRev(gameData, nation) -> float:
    return sum(calcTerritoryRev(gameData.gameTime(), terr, nation) for terr in gameData.getNationTerr(nation.name))

def calcStabRevEffect(stab: int):
    return 0.05 * stab ** 0.7 if stab > 0 else 0.05 * stab

def calcRevByTerr(gameData, nation):
    rev = {}
    for t in gameData.getNationTerr(nation.name):
        rev[t.name] = round(calcTerritoryRev(gameData.gameTime(), t, nation) * nation.tax_rate / 2000, 2)
    return rev


def findppgain(taxRate: int) -> float | int:
    pp = -1.5 * (taxRate + 5) ** 0.5 + 10
    if pp < 0:
        pp *= 0.5
    return round(pp, 2)


def getResources(gameData, nation: Nation) -> dict:
    resources = {}
    for terr in gameData.getNationTerr(nation.name):
        for resource, amount in terr.resources.items():
            resources[resource] = resources.get(resource, 0) + amount
    return {resource: round(amount, 2) for resource, amount in resources.items()}


def getResourceFlow(gameData, nation: Nation) -> dict:
    res = getResources(gameData, nation)
    ideBoost = 1.0  # TODO: Apply ideology resource multiplier

    for resource in res:
        res[resource] *= ideBoost

    for terr in gameData.getNationTerr(nation.name):
        if "Fuel Refinery" in terr.buildings:
            if "Fuel" not in res:
                res["Fuel"] = 0
            if "Oil" in res:
                res["Oil"] -= 1
                res["Fuel"] += fuelProduced["Oil"] * ideBoost
            elif "Coal" in res:
                res["Coal"] -= 1
                res["Fuel"] += fuelProduced["Coal"] * ideBoost

        if "Steel Factory" in terr.buildings:
            for resource in steelFactory:
                amount = steelFactory[resource] * (ideBoost if steelFactory[resource] > 0 else 1)
                res[resource] = res.get(resource, 0) + amount

    return res


def collectResources(gameData, nation: Nation, elapsed: int = taxCooldown) -> dict:
    res = getResourceFlow(gameData, nation)
    ideBoost = 1.0  # TODO: Apply ideology resource multiplier

    for resource in res:
        res[resource] *= elapsed / taxCooldown

    # Handle insufficient Oil by substituting Coal.
    if "Oil" in res and "Fuel" in res:
        oilInventory = nation.resources.get("Oil", 0)
        if res["Oil"] < 0 and abs(res["Oil"]) > oilInventory:
            overused = abs(res["Oil"]) - oilInventory
            res["Fuel"] -= overused * fuelProduced["Oil"] * ideBoost
            res["Oil"] += overused
            if "Coal" in res:
                res["Coal"] -= overused
                res["Fuel"] += overused * fuelProduced["Coal"] * ideBoost

    # Handle insufficient Iron.
    if "Steel" in res and "Iron" in res:
        ironInventory = nation.resources.get("Iron", 0)
        if res["Iron"] < 0 and abs(res["Iron"]) > ironInventory:
            overused = abs(res["Iron"]) - ironInventory
            res["Steel"] += overused * steelFactory["Steel"] * ideBoost / steelFactory["Iron"]
            res["Coal"] += overused * steelFactory["Coal"] / steelFactory["Iron"]
            res["Iron"] += overused

    # Handle insufficient Coal.
    if "Coal" in res:
        coalInventory = nation.inventory.get("Coal", 0)
        if res["Coal"] < 0 and abs(res["Coal"]) > coalInventory:
            overused = abs(res["Coal"]) - coalInventory
            res["Coal"] += overused

            if "Fuel" in res:
                takeAway = overused * fuelProduced["Coal"] * ideBoost
                if takeAway > res["Fuel"]:
                    overused -= res["Fuel"] / (fuelProduced["Coal"] * ideBoost)
                    res["Fuel"] = 0
                    res["Coal"] -= overused
                else:
                    overused -= takeAway / (fuelProduced["Coal"] * ideBoost)
                    res["Fuel"] -= takeAway

            if "Steel" in res and overused > 0:
                res["Steel"] -= overused * steelFactory["Steel"] * ideBoost
                res["Iron"] -= overused * steelFactory["Iron"]

    return res


def collectIncome(gameData, nation: Nation):
    currentTime = gameData.gameTime()
    last = nation.last.copy()
    previousTax = last.get("tax", currentTime - taxCooldown)
    if previousTax == 0:
        previousTax = currentTime - taxCooldown

    if previousTax + taxCooldown > currentTime:
        raise ValueError(f"Can't collect yet! Next collection in {previousTax + taxCooldown - currentTime} seconds.")

    elapsed = currentTime - previousTax

    # Tax revenue, including diminishing returns for longer collection periods.
    baseRevenue = sum(calcRevByTerr(gameData, nation).values())
    revenue = round(baseRevenue * (elapsed / taxCooldown) ** 0.75, 2)

    # Stability and political power.
    stabilityChange = 0.4 * ((101 - nation.tax_rate) ** 0.5 - 9)

    # TODO: Add statue stability bonuses.
    statueStability = 0
    statuePP = 0

    stabilityChange = (stabilityChange + statueStability) / taxCooldown * elapsed
    ppChange = (findppgain(nation.tax_rate) + statuePP) / taxCooldown * elapsed

    stability = min(100, nation.stability + stabilityChange)
    politicalPower = nation.political_power + ppChange

    # TODO: Apply war debt payments before updating the balance.
    owed = 0

    # Collect and apply resources.
    resourceChanges = collectResources(gameData, nation, elapsed)
    inventory = nation.inventory.copy()

    for resource, amount in resourceChanges.items():
        inventory[resource] = inventory.get(resource, 0) + amount

    balance = round(nation.balance + revenue - owed, 2)
    last["tax"] = currentTime

    gameData.updateNation(
        nation.name,
        {
            "balance": balance,
            "stability": stability,
            "political_power": politicalPower,
            "inventory": inventory,
            "last": last
        }
    )

    return {
        "Income": revenue,
        "War Debts": owed,
        "Balance": balance,
        "Stability": {
            "Total": round(stability, 2),
            "Change": round(stabilityChange, 2)
        },
        "Political Power": {
            "Total": round(politicalPower, 2),
            "Change": round(ppChange, 2)
        },
        "Resources": {
            resource: round(amount, 2)
            for resource, amount in resourceChanges.items()
            if amount != 0
        },
        "Collected From": previousTax,
        "Collected Until": currentTime
    }