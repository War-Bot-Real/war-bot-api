from api.repositories.gameData import GameData
from api.models import Territory, Sea, Unit
from api.game_logic.shared import formatTime, formatList, formatNum
from api.game_logic.military.shared import getDomain, getCapacity, station, findFuelRequired, planeFuelReq, findCooldown, planeCooldown, inRange, getAllBorders, findOwner, findCoastOccupant
from api.game_logic.military.attack import aircraftInterception
from api.game_logic.military.pathFinder import shortestPathFinder

def move(gameData: GameData, nation, units: list[Unit], target: str):
    if not units:
        raise ValueError("No units specified.")

    invalidUnits = [unit for unit in units if unit.nation != nation.name]
    if invalidUnits:
        raise ValueError(f"You don't own these units: {', '.join(u.name for u in invalidUnits)}")

    if any(not unit.active for unit in units):
        raise ValueError("This unit is currently entrenched, and so cannot move. Unentrench it using the activate command.")

    domain = getDomain(gameData, units[0].type)
    now = gameData.gameTime()

    timedOut = {unit.name: unit.tiredUntil - now for unit in units if unit.tiredUntil > now}
    if timedOut:
        unitName, remaining = max(timedOut.items(), key=lambda item: item[1])
        raise ValueError(f"You can't move this unit yet! Timeout for `{unitName}` ends in {formatTime(remaining)}")

    try:
        targetTerritory = gameData.getTerritory(target)
    except ValueError:
        targetTerritory = None

    try:
        targetSea = gameData.getSea(target)
    except ValueError:
        targetSea = None

    try:
        targetUnit = gameData.getUnit(target)
    except ValueError:
        targetUnit = None

    if domain == "Air":
        dest = targetTerritory or targetUnit
        if dest is None:
            raise ValueError("Invalid destination.")
    elif domain == "Ground":
        dest = targetTerritory
        if dest is None:
            raise ValueError("That is not a valid territory.")
    else:
        if not targetTerritory and not targetSea:
            raise ValueError("No valid territory or sea found.")
        if targetTerritory and targetSea:
            raise ValueError(f"Both a sea ({targetSea.name}) and territory ({targetTerritory.name}) were found. Please specify which one you want to move to.")
        dest = targetTerritory or targetSea

    if isinstance(dest, Unit):
        if dest.name == units[0].location:
            raise ValueError(f"`{units[0].name}` is already aboard {dest.type} {dest.name}!")
        if getCapacity(gameData, dest) == 0:
            raise ValueError(f"You can't move a unit onto a {dest.type}.")
        if domain == "Naval":
            raise ValueError("You can't move a ship onto a carrier. Move it across the sea normally.")
        raise ValueError("To move troops onto a carrier, use the load command.")

    if dest.name == units[0].location:
        raise ValueError(f"`{units[0].name}` is already here!")

    if domain == "Ground":
        owner = gameData.getNation(dest.nation)
        if owner.name not in nation.canEnter():
            raise ValueError(f"You don't have permission to move to {owner.demonym} territory.")
        if units[0].location not in dest.bordering:
            raise ValueError(f"{units[0].location} does not border {dest.name}.")
        fuelRequired = findFuelRequired(gameData, units, "movement")

    elif domain == "Air":
        if "Airport" not in dest.buildings and "Airstrip" not in dest.buildings:
            raise ValueError(f"{dest.name} does not have an Airport or Airstrip!")
        if not inRange(gameData, units[0], dest, False):
            raise ValueError(f"{units[0].name} is not within range to move to {dest.name}!")

        current = station(gameData, units[0])
        if isinstance(current, Unit):
            current = station(gameData, current)
        if current is None:
            raise ValueError("Could not determine the aircraft's current location.")

        path = shortestPathFinder(gameData, current, dest, inOneNation=False, includeSeas=True)
        if path is None:
            raise ValueError(f"No valid flight path to {dest.name}.")

        # TODO: Add confirmation before flying over enemy territory.
        for index, tile in enumerate(path[1:], start=1):
            owner = findOwner(gameData, tile) if isinstance(tile, Sea) else gameData.getNation(tile.nation)
            if isinstance(tile, Territory) and isinstance(path[index - 1], Sea):
                coastOwner = findCoastOccupant(gameData, tile)
                if coastOwner:
                    owner = coastOwner
            if owner and (gameData.atWar(nation.name, owner.name) or nation.name in owner.diplomacy["Enemies"]):
                break

        fuelTarget = station(gameData, dest) if isinstance(dest, Unit) else dest
        fuelRequired = planeFuelReq(gameData, units, fuelTarget, False)

    else:  # Naval
        owner = findCoastOccupant(gameData, dest) if isinstance(dest, Territory) else findOwner(gameData, dest)
        if owner and owner.name != nation.name and owner.name not in nation.diplomacy["Trusted"]:
            if isinstance(dest, Territory) and dest.nation == nation.name:
                raise ValueError(f"{owner.demonym} forces are currently trespassing on your coast, and until they leave you cannot move to this territory.")
            raise ValueError(f"You do not have permission to move to this {'territory' if isinstance(dest, Territory) else 'sea'}.")
        if units[0].location not in getAllBorders(gameData, dest):
            raise ValueError(f"{units[0].location} does not border {dest.name}.")
        fuelRequired = findFuelRequired(gameData, units, "movement")

    inventory = nation.inventory.copy()
    fuel = inventory.get("Fuel", 0)
    if fuel < fuelRequired:
        amount = round(fuelRequired - fuel, 2)
        raise ValueError(f"You require **{amount}** more fuel to move this {units[0].type if len(units) == 1 else 'group'}.")

    if domain == "Air":
        originalUnits = units.copy()
        interception = aircraftInterception(gameData, nation, units, dest, True)
        if interception and len(units) == 0:
            involved = [n.demonym for n in interception.allNationsInvolved]
            combined = "combined " if interception.enemyNationsInvolved else ""
            return {
                "success": False,
                "message": f"All of your aircraft were unfortunately repelled by {combined}{formatList(involved)} forces!",
                "interception": interception
            }

        message = None
        if interception and len(originalUnits) != len(units):
            message = f"Most of your aircraft made it through, though unfortunately the following were intercepted along the way:\n{interception.getCasMsg(nation)}"
        elif interception and interception.enemyNationsInvolved:
            message = f"Safely landed your aircraft in **{dest.name}**. Along the journey, enemy aircraft were spotted, however you made it through unscathed."

        if interception:
            for involvedNation in interception.allNationsInvolved:
                if involvedNation.name == nation.name:
                    continue
                casmsg = interception.getCasMsg(involvedNation)
                notification = f"{nation.demonym} planes were spotted flying over our territory."
                if casmsg:
                    notification += " We attempted to stop them, and suffered the following losses:\n" + casmsg
                gameData.createMessage(nation.name, involvedNation.name, "notification", notification)

        for unit in units:
            gameData.updateUnit(unit.name, {
                "location": dest.name,
                "tiredUntil": now + planeCooldown(gameData, unit.type, current, dest, False)
            })

    else:
        for unit in units:
            cooldown = findCooldown(gameData, unit.type, dest.terrain if domain == "Ground" else "None", nation.stability)
            gameData.updateUnit(unit.name, {
                "location": dest.name,
                "tiredUntil": now + cooldown
            })
        message = f"`{units[0].name if len(units) == 1 else 'Units'}` has been moved to **{dest.name}**."

    inventory["Fuel"] = fuel - fuelRequired
    gameData.updateNation(nation.name, {"inventory": inventory})

    if domain == "Air" and not message:
        message = f"`{units[0].name if len(units) == 1 else 'Aircraft'}` has been moved to **{dest.name}**."

    return {"success": True, "message": message, "destination": dest.name}
