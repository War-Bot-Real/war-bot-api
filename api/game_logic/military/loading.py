from api.game_logic.military.shared import getDomain, getCapacity, findWeight, getLoad, inRange, station, cooldownConstants, cooldownMultiplier

def executeLoad(gameData, carrier, units):
    if getCapacity(gameData, carrier) <= 0:
        raise ValueError(f"That's a {carrier.type.lower()}, not a transporter or aircraft carrier!")

    carrierTerr = station(gameData, carrier)
    wrong, notAdjacent, notInRange, alreadyOn, onCooldown, valid = [], [], [], [], [], []

    for unit in units:
        domain = getDomain(gameData, unit.type)

        if domain == "Naval":
            wrong.append(unit)
        elif domain == "Air" and not inRange(gameData, unit, carrierTerr, False):
            notInRange.append(unit)
        elif domain == "Ground" and unit.location != carrierTerr.name:
            notAdjacent.append(unit)
        elif unit.location == carrier.name:
            alreadyOn.append(unit)
        elif unit.tiredUntil > gameData.gameTime():
            onCooldown.append(unit)
        else:
            valid.append(unit)

    messages = []
    if notAdjacent:
        messages.append(f"These divisions aren't on the province that your {carrier.type.lower()} is on: `{', '.join(u.name for u in notAdjacent)}`")
    if alreadyOn:
        messages.append(f"These divisions are already on your carrier: `{', '.join(u.name for u in alreadyOn)}`")
    if wrong:
        messages.append(f"These divisions can't be loaded onto {carrier.type.lower()}s: `{', '.join(u.name for u in wrong)}`. You can only load ground and air forces onto carriers.")
    if notInRange:
        messages.append(f"These aircraft are not in range of your carrier: `{', '.join(u.name for u in notInRange)}`")
    if onCooldown:
        messages.append(f"These divisions are on cooldown: `{', '.join(u.name for u in onCooldown)}`")

    if messages:
        raise ValueError("\n".join(messages))

    troopWeight = findWeight(gameData, valid)
    existingWeight = findWeight(gameData, getLoad(gameData, carrier))
    capacity = getCapacity(gameData, carrier)

    if troopWeight > capacity - existingWeight:
        excess = round(troopWeight + existingWeight - capacity, 2)
        raise ValueError(f"Too heavy! You have exceeded the limit by {excess} kilotonnes.")

    tiredUntil = gameData.gameTime() + cooldownConstants["loading"] * cooldownMultiplier["Loading"]

    for unit in valid:
        gameData.updateUnit(unit.name, {"location": carrier.name, "tiredUntil": tiredUntil})

    return f"Successfully loaded all units onto {carrier.type} `{carrier.name}`."

def executeUnload(gameData, nation, carrier):
    if carrier is None or getCapacity(gameData, carrier) == 0:
        raise ValueError("That's not a valid transporter!")
    if carrier.nation != nation.name:
        raise ValueError("You don't own that transporter!")
    
    try:
        territory = gameData.getTerritory(carrier.location)
    except ValueError:
        raise ValueError("Your transporter is currently at sea. Move it to a coastal province before unloading.")

    if territory.nation not in nation.canEnter():
        raise ValueError("That territory is held by a different nation. You must attack it!")

    currentTime = gameData.gameTime()
    if carrier.tiredUntil > currentTime:
        remaining = carrier.tiredUntil - currentTime
        raise ValueError(f"This transporter is currently on cooldown. You can unload in {remaining:.0f} seconds.")

    troops = getLoad(gameData, carrier)
    if not troops:
        return {"territory": territory.name, "unloaded": []}

    cooldown = currentTime + cooldownConstants["loading"] * cooldownMultiplier["Loading"]
    unloaded = []
    for unit in troops:
        gameData.updateUnit(unit.name, {"location": territory.name, "tiredUntil": cooldown})
        unloaded.append(unit.name)

    return {
        "territory": territory.name,
        "unloaded": unloaded,
        "cooldown": cooldown - currentTime
    }
