import math
from api.game_logic.top import calcNationPower
from api.game_logic.shared import calcDensity, calcDistance

bulldozeCosts = {
    "Building": 20000,
    "Track": 5000
}

def getAllBuildings(gameData) -> list[str]:
    return list(gameData.getDefaultGameData()["Buildings"])

def financialCenterLimit(gameData, nation) -> int:
    power = calcNationPower(gameData, nation)
    if power <= 0:
        return 0
    return max(int(math.floor(math.log(power, 2) + 3)), 1)
  
def executeBuild(gameData, nation, territory, building: str):
    if territory.nation != nation.name:
        raise ValueError("You cannot build in another nation's territory.")

    if not building:
        raise ValueError("Specify what to build.")

    building = building.lower()
    matches = [b for b in getAllBuildings(gameData) if building in b.lower()]
    if not matches:
        raise ValueError("Not a valid building.")
    if len(matches) > 1:
        raise ValueError("Multiple buildings matched. Be more specific.")

    building = matches[0]

    if building == "Statue":
        raise ValueError("Statue construction is not implemented yet.")

    inventory = dict(nation.inventory or {})
    if inventory.get(building, 0) <= 0:
        raise ValueError(f"You don't have any {building} in your inventory.")

    if building in ["Oil Drill", "Fuel Refinery", "Financial Center", "Railway Center"] and territory.devastation > 10:
        raise ValueError(f"You cannot build a {building} on territories with a devastation of 10+!")

    buildings = list(territory.buildings or [])
    if building in buildings:
        raise ValueError(f"You already have a {building} in {territory.name}.")

    if building == "Financial Center":
        count = sum(1 for terr in gameData.getNationTerr(nation.name) if "Financial Center" in terr.buildings)
        if count >= financialCenterLimit(gameData, nation):
            raise ValueError("You have reached your limit for building financial centers!")

    inventory[building] -= 1
    buildings.append(building)

    gameData.updateNation(nation.name, {"inventory": inventory})
    gameData.updateTerritory(territory.name, {"buildings": buildings})

    return {
        "building": building,
        "territory": territory.name,
        "remaining": inventory[building]
    }

def executeBulldoze(gameData, nation, territory, building: str):
    if territory.nation != nation.name:
        raise ValueError(f"You don't own {territory.name}!")

    buildings = list(territory.buildings or [])
    matches = [b for b in buildings if building.lower() in b.lower()]

    if not matches:
        raise ValueError(f"{building} is not a valid building, or does not exist in {territory.name}.")
    if len(matches) > 1:
        raise ValueError("Multiple buildings found. Be more specific.")

    cost = bulldozeCosts["Building"]
    if nation.balance < cost:
        raise ValueError(f"Not enough funds! It costs ${cost:,} to bulldoze a building.")

    removed = matches[0]
    buildings.remove(removed)
    gameData.updateTerritory(territory.name, {"buildings": buildings})
    gameData.updateNation(nation.name, {"balance": nation.balance - cost})

    return {"building": removed, "territory": territory.name, "cost": cost}


def executeBulldozeTrack(gameData, nation, terr1, terr2):
    if terr2.name not in terr1.rails:
        raise ValueError(f"There is no rail between {terr1.name} and {terr2.name}!")

    cost = bulldozeCosts["Track"]
    if nation.balance < cost:
        raise ValueError(f"You don't have enough money to bulldoze this track! This action costs ${cost:,}.")

    rails1 = list(terr1.rails or [])
    rails2 = list(terr2.rails or [])
    rails1.remove(terr2.name)
    rails2.remove(terr1.name)

    gameData.updateTerritory(terr1.name, {"rails": rails1})
    gameData.updateTerritory(terr2.name, {"rails": rails2})
    gameData.updateNation(nation.name, {"balance": nation.balance - cost})

    return {"territories": [terr1.name, terr2.name], "cost": cost}

def calcRailPrice(terr1, terr2) -> float:
    if terr1.area <= 0 or terr2.area <= 0:
        raise ValueError("Territory area must be greater than zero")
    price = 75 * calcDistance(terr1, terr2) * terr1.terrain ** 0.5 * terr2.terrain ** 0.5 * (calcDensity(terr1) + calcDensity(terr2)) ** 0.1
    if "Railway Station" not in terr1.buildings:
        price *= (len(terr1.rails or []) + 1) ** 0.3
    if "Railway Station" not in terr2.buildings:
        price *= (len(terr2.rails or []) + 1) ** 0.3
    return round(price, 2)

def getRailPrices(gameData, nation, territory):
    prices = []
    for name in territory.bordering:
        neighbor = gameData.getTerritory(name)
        if neighbor.name in (territory.rails or []) or neighbor.nation != nation.name:
            continue
        prices.append({"territory": neighbor.name, "price": calcRailPrice(territory, neighbor)})
    return prices

def executePave(gameData, nation, terr1, terr2, contributionType: str, contributionValue: float):
    if terr2.name not in terr1.bordering:
        raise ValueError("Territories do not border each other")
    if terr2.name in (terr1.rails or []):
        raise ValueError("A railway already exists between these territories")
    if contributionType not in ("percent", "dollar") or contributionValue < 0:
        raise ValueError("Invalid contribution")

    owners = sorted({terr.nation for terr in (terr1, terr2) if terr.nation != nation.name})
    trusted = nation.canEnter()
    if any(owner not in trusted for owner in owners):
        raise ValueError("You do not have permission to build a railway in these territories")

    price = calcRailPrice(terr1, terr2)

    if not owners:
        if nation.balance < price:
            raise ValueError("Insufficient funds")
        gameData.updateTerritory(terr1.name, {"rails": list(terr1.rails or []) + [terr2.name]})
        gameData.updateTerritory(terr2.name, {"rails": list(terr2.rails or []) + [terr1.name]})
        gameData.updateNation(nation.name, {"balance": nation.balance - price})
        return {"status": "built", "price": price}

    contribution = price * min(contributionValue, 100) / 100 if contributionType == "percent" else min(contributionValue, price)
    contribution = round(contribution, 2)
    remaining = round(price - contribution, 2)
    payments = {nation.name: contribution}
    for owner in owners:
        payments[owner] = round(remaining / len(owners), 2)
    payments[owners[-1]] = round(payments[owners[-1]] + price - sum(payments.values()), 2)

    details = {
        "territories": [terr1.name, terr2.name],
        "totalCost": price,
        "payments": payments,
        "approved": [nation.name]
    }

    for interaction in gameData.getInteractions("rail"):
        existing = interaction.get("details", {}).get("territories", [])
        if interaction.get("from") == nation.name and existing in ([terr1.name, terr2.name], [terr2.name, terr1.name]):
            gameData.deleteInteraction(interaction["id"])

    gameData.createInteraction(nation.name, None, "rail", details)
    return {"status": "pending", "price": price, "payments": payments}

def approvePave(gameData, nation, interactionId):
    interaction = next((i for i in gameData.getInteractions("rail") if str(i["id"]) == str(interactionId)), None)
    if not interaction:
        raise ValueError("Rail request not found")

    details = interaction["details"]
    terr1 = gameData.getTerritory(details["territories"][0])
    terr2 = gameData.getTerritory(details["territories"][1])
    payments = details["payments"]
    approved = details.get("approved", [])

    if terr2.name not in terr1.bordering:
        raise ValueError("These territories no longer border each other")
    if terr2.name in (terr1.rails or []):
        raise ValueError("A railway already exists between these territories")

    requiredApprovals = {terr1.nation, terr2.nation}
    requiredApprovals.update(payer for payer, amount in payments.items() if amount > 0)
    requiredApprovals.discard(interaction["from"])

    if nation.name not in requiredApprovals:
        raise ValueError("Your nation is not required to approve this request")
    if nation.name in approved:
        raise ValueError("Your nation has already approved this request")

    approved.append(nation.name)
    remaining = requiredApprovals - set(approved)

    if remaining:
        details["approved"] = approved
        gameData.updateInteraction(interaction["id"], {"details": details})
        return {"status": "pending", "approved": approved, "remaining": sorted(remaining)}

    # Validate every payment before making any changes.
    payers = {}
    for payer, amount in payments.items():
        if amount <= 0:
            continue
        payerNation = gameData.getNation(payer)
        if payerNation.balance < amount:
            raise ValueError(f"{payer} does not have sufficient funds")
        payers[payer] = payerNation

    rails1 = list(terr1.rails or [])
    rails2 = list(terr2.rails or [])
    rails1.append(terr2.name)
    rails2.append(terr1.name)

    gameData.updateTerritory(terr1.name, {"rails": rails1})
    gameData.updateTerritory(terr2.name, {"rails": rails2})

    for payer, amount in payments.items():
        if amount > 0:
            gameData.updateNation(payer, {"balance": payers[payer].balance - amount})

    gameData.deleteInteraction(interaction["id"])
    return {"status": "built", "territories": [terr1.name, terr2.name], "payments": payments}
