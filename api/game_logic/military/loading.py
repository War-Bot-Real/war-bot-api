from api.game_logic.military.shared import getDomain, getCapacity, findWeight, getLoad, inRange, station, cooldownConstants, cooldownMultiplier

def load(gameData, carrier, units):
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