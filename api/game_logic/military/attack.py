import random
from api.models import Territory, Sea, Nation, Unit
from api.game_logic.military.management import getUnitData
from api.game_logic.shared import formatTime, findquan, addToDict
from api.game_logic.military.shared import getDomain, canTakeoff, inRange, findCoastOccupant, findFuelRequired, findOwner, getAllBorders, station, antiAirDef

def strength(gameData, divs: list[Unit], type: str) -> float:
    total = 0

    for unit in divs:
        domain, data = getUnitData(gameData, unit.type)
        unitStrength = data.get("Strength", {}).get("Attack" if type == "att" else "Defense")

        if unitStrength is None:
            continue

        total += unit.quantity / data["Each"] * unitStrength * (1.5 if not unit.active else 1)

    return total

def casByNation(cas: dict[Unit, int]):
  byNation = {}
  for i in cas:
    if i.nation in byNation:
      if i.type in byNation[i.nation]:
        byNation[i.nation][i.type] += cas[i]
      else:
        byNation[i.nation][i.type] = cas[i]
    else:
      byNation[i.nation] = {i.type: cas[i]}
  return byNation

def groupUnitsByType(cas: dict[Unit, int]):
  byType = {}
  for i in cas:
    if i.type in byType:
      byType[i.type] += cas[i]
    else:
      byType[i.type] = cas[i]
  return byType

def addToAllCas(allcas: dict, newcas: dict):
  for nation in newcas:
    if nation in allcas:
      addToDict(allcas[nation], newcas[nation])
    else:
      allcas[nation] = newcas[nation]

def divideUnit(unit: Unit) -> list[Unit]:
    return [Unit({
        "name": unit.name,
        "type": unit.type,
        "quantity": 1,
        "nation": unit.nation,
        "location": unit.location,
        "tiredUntil": unit.tiredUntil,
        "active": unit.active
    }) for _ in range(unit.quantity)]

def attack(gameData, nation: Nation, target: Territory | Sea, units: list[Unit]):
    # ---------- Defender ----------
    defDivs = []

    for unit in gameData.getUnits():
        if unit.location != target.name:
            continue

        if not gameData.atWar(nation.name, unit.nation):
            continue

        domain = getUnitData(gameData, unit.type)[0]

        if domain != "Air":
            defDivs.append(unit)
        elif canTakeoff(gameData, unit):
            defDivs.append(unit)

    # ---------- Attacker validation ----------
    attDivs = []
    partOfGroup = []
    notAdjacent = []
    notInRange = []
    noTakeoff = []
    entrenched = []
    notCoastal = []
    notSeaUnits = []

    for unit in units:
        if unit.nation != nation.name:
            raise ValueError(f"You don't own unit '{unit.name}'")

        domain = getUnitData(gameData, unit.type)[0]

        if domain != "Air" and unit.location not in getAllBorders(gameData, target):
            notAdjacent.append(unit.name)
            continue

        if domain == "Air" and not inRange(gameData, unit, target):
            notInRange.append(unit.name)
            continue

        if domain == "Air" and not canTakeoff(gameData, unit):
            noTakeoff.append(unit.name)
            continue

        attDivs.append(unit)

    for unit in attDivs:
        domain = getUnitData(gameData, unit.type)[0]

        if domain == "Ground" and not unit.active:
            entrenched.append(unit.name)

        if domain == "Naval" and isinstance(target, Territory) and not target.coast:
            notCoastal.append(unit.name)

        if domain == "Ground" and isinstance(target, Sea):
            notSeaUnits.append(unit.name)

    errors = []

    if partOfGroup:
        errors.append(f"The following units are part of an existing group, and thus cannot attack independently: {', '.join(partOfGroup)}")

    if notAdjacent:
        errors.append(f"The following units or groups are not adjacent to {target.name}: {', '.join(notAdjacent)}")

    if notInRange:
        errors.append(f"The following planes are not in range to attack {target.name}: {', '.join(notInRange)}")

    if noTakeoff:
        errors.append(f"The following planes are unable to takeoff due to a lack of airports/airstrips/aircraft carriers in their current province: {', '.join(noTakeoff)}")

    if entrenched:
        errors.append(f"The following units are entrenched so are not allowed to attack: {', '.join(entrenched)}")

    if notCoastal:
        errors.append(f"The following units are naval units, but you are attacking a landlocked territory: {', '.join(notCoastal)}")

    if notSeaUnits:
        errors.append(f"The following units are ground units, but you are attacking a sea: {', '.join(notSeaUnits)}")

    if errors:
        raise ValueError("\n".join(errors))

    # ---------- Cooldown ----------
    timedOut = {}

    for unit in attDivs:
        if unit.tiredUntil > gameData.gameTime():
            timedOut[unit.name] = unit.tiredUntil - gameData.gameTime()

    if timedOut:
        msg = "Cool down there! Some of your divisions are tired!\n"
        for unit, remaining in timedOut.items():
            msg += f"`{unit}` will be able to attack in {formatTime(remaining)}\n"
        raise ValueError(msg)

    # ---------- Basic attack validation ----------
    attdomains = {getUnitData(gameData, unit.type)[0] for unit in attDivs}

    if attdomains == {"Ground"} and strength(gameData, attDivs, "att") == 0:
        raise ValueError("The units you are currently attacking with have 0 attack power. You must use different units alongside these ones.")

    # ---------- Determine defender ----------
    if isinstance(target, Sea):
        defN = findOwner(gameData, target)

        if defN is None:
            raise ValueError("Nobody currently occupies that sea. There is nothing to attack.")

        if defN.name == nation.name:
            raise ValueError("Why are you attacking yourself?")

        if not gameData.atWar(nation.name, defN.name):
            raise ValueError(f"You are not at war with {defN.name}!")

    else:
        owner = gameData.getNation(target.nation)

        if "Ground" in attdomains or "Air" in attdomains:
            if owner.name == nation.name:
                raise ValueError("Why are you attacking yourself?")

            if not gameData.atWar(nation.name, owner.name):
                raise ValueError(f"You are not at war with {owner.name}!")

            defN = owner

        elif not gameData.atWar(nation.name, owner.name):
            coastowner = findCoastOccupant(gameData, target)

            if coastowner is None:
                raise ValueError("There is nobody there for you to attack!")

            if coastowner.name == nation.name:
                raise ValueError("Why are you attacking yourself?")

            if not gameData.atWar(nation.name, coastowner.name):
                raise ValueError(f"You are not at war with {coastowner.name}!")

            defN = coastowner
        else:
            defN = owner

    # ---------- Fuel ----------
    fuelRequired = findFuelRequired(gameData, attDivs, "attack")
    fuel = nation.inventory.get("Fuel", 0)

    if fuelRequired > fuel:
        raise ValueError(f"You require {round(fuelRequired - fuel, 2)} more fuel to complete this action.")

    nation.inventory["Fuel"] = fuel - fuelRequired

    gameData.updateNation(nation.name, {"inventory": nation.inventory})

    # ---------- Air interception ----------
    attplanes = [unit for unit in attDivs if getUnitData(gameData, unit.type)[0] == "Air"]
    interception = aircraftInterception(gameData, nation, attplanes, target, False)

    if findquan(attDivs) == 0:
        raise ValueError(f"All your planes were intercepted before reaching {target.name}. The battle ended before it began.")

    interceptlog = {}

    if interception is not None:
        for tile in interception.lossesByTile:
            interceptlog[tile.name] = {}
            byNation = casByNation(interception.lossesByTile[tile])
            for defender in byNation:
                interceptlog[tile.name][defender] = groupUnitsByType(byNation[defender])

    # ---------- Intelligence ----------
    intelligent = set()

    for border in getAllBorders(gameData, target):
        try:
            territory = gameData.getTerritory(border)
        except ValueError:
            continue

        if "Radar Station" in territory.buildings:
            intelligent.add(territory.nation)

    for unit in attDivs + defDivs:
        if unit.type == "Spy Plane":
            intelligent.add(unit.nation)

    # ---------- Battle log ----------
    battleId = getNextBattleId()

    battleLog = {
        "Attacker": {"Name": nation.name, "Flag": nation.flag},
        "Defender": {"Name": defN.name, "Flag": defN.flag},
        "Sea" if isinstance(target, Sea) else "Territory": target.name,
        "Time": gameData.gameTime(),
        "Has Intelligence": list(intelligent),
        "Initial": {},
        "Casualties": {}
    }

    if interception is not None:
        battleLog["Intercepted"] = interceptlog

    allcas = {}

    for unit in attDivs + defDivs:
        unitInfo = {
            "Unit ID": unit.name,
            "Type": unit.type,
            "Quantity": unit.quantity
        }

        if getUnitData(gameData, unit.type)[0] == "Ground":
            unitInfo["Entrenched"] = not unit.active

        if unit.nation in battleLog["Initial"]:
            battleLog["Initial"][unit.nation].append(unitInfo)
        else:
            battleLog["Initial"][unit.nation] = [unitInfo]
            allcas[unit.nation] = {}

    # ---------- Fighter battle ----------
    battle = fighterBattle(gameData, attDivs, defDivs)

    if battle:
        cas = executeBattleCas(gameData, attDivs, defDivs, battle)
        byNation = casByNation(cas)
        battleLog["Casualties"]["Fighter Battle"] = byNation
        addToAllCas(allcas, byNation)

    # ---------- Naval / air raids ----------
    offensiveRaid = navalAirRaid(gameData, attDivs, defDivs, isinstance(target, Sea))
    defensiveRaid = navalAirRaid(gameData, defDivs, attDivs, isinstance(target, Sea))

    if offensiveRaid or defensiveRaid:
        cas = executeBattleCas(gameData, attDivs, defDivs, offensiveRaid | defensiveRaid)
        byNation = casByNation(cas)
        battleLog["Casualties"]["Naval Air Raids"] = byNation
        addToAllCas(allcas, byNation)

    # ---------- Naval battle ----------
    navBat = None
    navRetreatMsg = ""

    if "Naval" in attdomains:
        navBat = navalBattle(gameData, nation, attDivs, defDivs)

        if navBat.destroyedShips:
            cas = executeBattleCas(gameData, attDivs, defDivs, navBat.destroyedShips)
            byNation = casByNation(cas)
            battleLog["Casualties"]["Naval Battle"] = byNation
            battleLog["Naval Logs"] = navBat.logs
            addToAllCas(allcas, byNation)

            defShips = [unit for unit in defDivs if getUnitData(gameData, unit.type)[0] == "Naval"]
            attShips = [unit for unit in attDivs if getUnitData(gameData, unit.type)[0] == "Naval"]

            if navBat.attWin:
                encircled = []
                navRetreatMsg = formatRetreatMessage(retreatShips(gameData, defShips))

                for unit in attShips:
                    gameData.updateUnit(unit.name, {"location": target.name})
                    unit.location = target.name

                for unit in defShips:
                    if unit.location == target.name:
                        encircled.append(unit)

                if encircled:
                    navRetreatMsg += "The following ships were encircled:\n" + formatEncirclementMessage(encircled)

    # ---------- Ground-based air combat ----------
    if isinstance(target, Territory):
        offensive = groundBasedAirDefense(gameData, attDivs, defDivs, navBat is None)
        defensive = groundBasedAirDefense(gameData, defDivs, attDivs, False)

        if offensive or defensive:
            cas = executeBattleCas(gameData, attDivs, defDivs, offensive | defensive)
            byNation = casByNation(cas)
            battleLog["Casualties"]["Ground-Based Air Defense"] = byNation
            addToAllCas(allcas, byNation)

        offensive = groundBombardment(gameData, attDivs, defDivs, navBat is None)

        if offensive:
            byNation = casByNation(offensive)
            battleLog["Casualties"]["Offensive Ground Bombardment"] = byNation
            addToAllCas(allcas, byNation)

        defensive = groundBombardment(gameData, defDivs, attDivs, navBat is None)

        if defensive:
            byNation = casByNation(defensive)
            battleLog["Casualties"]["Defensive Ground Bombardment"] = byNation
            addToAllCas(allcas, byNation)

    # ---------- Land battle ----------
    retreatmsg = ""

    if isinstance(target, Territory) and "Ground" in attdomains and strength(gameData, attDivs, "att") > 0:
        battle = landBattle(gameData, target, nation, attDivs, defDivs)

        byType = groupUnitsByType(battle.attCas)
        battleLog["Casualties"]["Land Battle"] = {nation.name: byType}
        addToAllCas(allcas, {nation.name: byType})

        for defender in battle.defCas:
            byType = groupUnitsByType(battle.defCas[defender])
            battleLog["Casualties"]["Land Battle"][defender] = byType
            addToAllCas(allcas, {defender: byType})

        if battle.defFuelShortages:
            battleLog["Fuel Shortages"] = battle.defFuelShortages

        landBattleAftermath(gameData, nation, target, battle)

        if battle.attWin:
            retreatmsg = retreatForces(gameData, target, defDivs)

        annexmsg = generateAnnexMessage(gameData, nation, defN)

        participants = set(allcas.keys())
        participants.add(defN.name)

        for participant in participants:
            participantNation = gameData.getNation(participant)

            if participantNation is None:
                continue

            if participant in allcas:
                stabloss = calcCasualtyStabLoss(participantNation, allcas[participant], battle.attWin == (nation.name == participant))
            elif battle.undefended:
                stabloss = -2
            else:
                stabloss = -1

            participantNation.stability += stabloss
            gameData.updateNation(participantNation.name, {"stability": participantNation.stability})

    # ---------- Non-land battle ----------
    else:
        pass

    # ---------- Unit cooldown ----------
    currentTime = gameData.gameTime()

    for unit in attDivs:
        domain = getUnitData(gameData, unit.type)[0]

        if domain != "Air":
            terrain = target.terrain if isinstance(target, Territory) else 0
            cooldown = findCooldown(gameData, unit.type, terrain, nation.stability) * cooldownMultiplier["Attacking"]
        else:
            location = station(gameData, unit)
            if isinstance(location, Unit):
                location = station(gameData, location)
            cooldown = planeCooldown(gameData, unit.type, location, target, True)

        tiredUntil = currentTime + cooldown
        unit.tiredUntil = tiredUntil
        gameData.updateUnit(unit.name, {"tiredUntil": tiredUntil})

    # ---------- Save battle ----------
    battles = getAllBattles(gameData)
    battles[battleId] = battleLog

    saveBattles(gameData, battles)

    return {
        "battleId": battleId,
        "battle": battleLog,
        "retreat": retreatmsg,
        "navalRetreat": navRetreatMsg
    }

class FlightResponse:
    def __init__(self, flownOver: set[Sea | Territory], lossesByTile: dict[Territory | Sea, dict[Unit, int]], allNationsInvolved: set[Nation], enemyNationsInvolved: set[Nation]):
        self.flownOver = flownOver
        self.lossesByTile = lossesByTile
        self.allNationsInvolved = allNationsInvolved
        self.enemyNationsInvolved = enemyNationsInvolved

    def getCasMsg(self, nation: Nation):
        casmsg = ""
        for tile, losses in self.lossesByTile.items():
            unitsLost = {unit: quantity for unit, quantity in losses.items() if unit.nation == nation.name}
            tempcasmsg = formatIndividualCas(unitsLost)
            if tempcasmsg:
                casmsg += f"In __{tile.name}__{tempcasmsg}\n"
        return casmsg

    def __str__(self):
        return f"__AIRCRAFT INTERCEPTION__\nFlown Over: {self.flownOver}\nLosses By Tile: {self.lossesByTile}\nNations Involved: {self.allNationsInvolved}\nEnemy Nations Involved: {self.enemyNationsInvolved}"

def aircraftInterception(gameData, nation: Nation, planes: list[Unit], dest: Territory | Sea, includeLast: bool) -> FlightResponse | None:
    if not planes:
        return None

    byTerr = {}

    for plane in planes:
        tile = station(gameData, plane)
        if isinstance(tile, Unit):
            tile = station(gameData, tile)
        if tile is None:
            continue
        byTerr.setdefault(tile, []).append(plane)

    flownOver = set()
    lossesByTile = {}
    allNationsInvolved = set()
    enemyNationsInvolved = set()

    for start, attackingPlanes in byTerr.items():
        path = shortestPathFinder(gameData, start, dest, inOneNation=False, includeSeas=True)

        for index, tile in enumerate(path[1:], start=1):
            if not attackingPlanes:
                break
            if not includeLast and tile == dest:
                continue

            flownOver.add(tile)
            enemyUnits = []

            for unit in gameData.getUnits():
                if unit.location != tile.name:
                    continue

                try:
                    defenderNation = gameData.getNation(unit.nation)
                except ValueError:
                    continue

                allNationsInvolved.add(defenderNation)

                if gameData.atWar(nation.name, defenderNation.name) or nation.name in defenderNation.diplomacy["Enemies"]:
                    enemyNationsInvolved.add(defenderNation)
                    enemyUnits.append(unit)

            if not enemyUnits:
                continue

            battle = fighterBattle(gameData, attackingPlanes, enemyUnits)
            cas = executeBattleCas(gameData, attackingPlanes, enemyUnits, battle)
            if tile in lossesByTile:
                addToDict(lossesByTile[tile], cas)
            else:
                lossesByTile[tile] = cas

            previousTile = path[index - 1]
            battle = groundBasedAirDefense(gameData, attackingPlanes, enemyUnits, isinstance(previousTile, Sea))
            cas = executeBattleCas(gameData, attackingPlanes, enemyUnits, battle)
            if tile in lossesByTile:
                addToDict(lossesByTile[tile], cas)
            else:
                lossesByTile[tile] = cas

    planes[:] = [plane for plane in planes if plane.quantity != 0]

    return FlightResponse(flownOver, lossesByTile, allNationsInvolved, enemyNationsInvolved)

def groundBombardment(gameData, attDivs: list[Unit], defDivs: list[Unit], includeAttackers: bool) -> dict[Unit, int]:
    casualties = {}
    attBombers = {"Bomber": [], "Attacker": []}

    for unit in attDivs:
        if unit.type in attBombers:
            if unit.type == "Attacker" and not includeAttackers:
                continue
            attBombers[unit.type] += divideUnit(unit)

    if not attBombers["Attacker"] and not attBombers["Bomber"]:
        return {}

    priority = {}

    for unit in defDivs:
        if getUnitData(gameData, unit.type)[0] == "Ground":
            priority.setdefault(unit.type, []).append(unit)

    priority = sorted(priority, key=lambda unitType: getUnitData(gameData, unitType)[1]["Strength"]["Attack"] + getUnitData(gameData, unitType)[1]["Strength"]["Defense"], reverse=True)

    for bomberType, bombers in attBombers.items():
        if not bombers:
            continue

        bomberData = getUnitData(gameData, bomberType)[1]
        limit = bomberData["Bombing"]["Limit"] * len(bombers)
        divsKilled = 0

        for unitType in priority:
            unitData = getUnitData(gameData, unitType)[1]

            for unit in priority[unitType]:
                if divsKilled >= limit:
                    break

                canKill = bomberData["Bombing"]["Strength"] * len(bombers) * unit.quantity / unitData["Each"]
                killed = round(min(canKill, limit - divsKilled) * unitData["Each"])
                divsKilled += killed / unitData["Each"]
                unit.quantity -= killed
                casualties[unit] = casualties.get(unit, 0) + killed

            if divsKilled >= limit:
                break

    return casualties

def fighterBattle(gameData, attDivs: list[Unit], defDivs: list[Unit]) -> set[Unit]:
    attplanes = {"Fighters": [], "Others": []}
    defplanes = {"Fighters": [], "Others": []}

    for unit in attDivs:
        if unit.type == "Fighter":
            attplanes["Fighters"] += divideUnit(unit)
        elif getDomain(gameData, unit.type) == "Air":
            attplanes["Others"] += divideUnit(unit)

    for unit in defDivs:
        if unit.type == "Fighter":
            defplanes["Fighters"] += divideUnit(unit)
        elif getDomain(gameData, unit.type) == "Air":
            defplanes["Others"] += divideUnit(unit)

    destroyed = set()

    for side, enemy in [(attplanes, defplanes), (defplanes, attplanes)]:
        for _ in side["Fighters"]:
            targets = set(enemy["Fighters"]) - destroyed
            if not targets:
                targets = set(enemy["Others"]) - destroyed
            if not targets:
                break
            destroyed.add(random.choice(list(targets)))

    for unit in destroyed:
        if unit in attplanes["Fighters"]:
            attplanes["Fighters"].remove(unit)
        elif unit in defplanes["Fighters"]:
            defplanes["Fighters"].remove(unit)

    for side, enemy in [(attplanes, defplanes), (defplanes, attplanes)]:
        for _ in side["Fighters"]:
            targets = set(enemy["Fighters"]) - destroyed
            if not targets:
                targets = set(enemy["Others"]) - destroyed
            if not targets:
                break
            destroyed.add(random.choice(list(targets)))

    return destroyed

def navalAirRaid(gameData, attDivs: list[Unit], defDivs: list[Unit], includeBombers: bool) -> set[Unit]:
    attplanes = []
    defSurfaceShips = []
    spy = False

    for unit in attDivs:
        if unit.type == "Attacker" or (unit.type == "Bomber" and includeBombers):
            attplanes += divideUnit(unit)
        elif unit.type == "Spy Plane":
            spy = True

    for unit in defDivs:
        if getDomain(gameData, unit.type) == "Naval" and unit.type != "Submarine":
            defSurfaceShips += divideUnit(unit)

    withAntiAir = {unit for unit in defSurfaceShips if antiAirDef(gameData, unit) > 0}
    targetted = set()
    destroyed = set()
    repelled = set()

    for plane in attplanes:
        targets = set(defSurfaceShips) - destroyed - targetted
        if spy:
            targets -= withAntiAir
        if not targets:
            targets |= targetted
        if not targets:
            break

        target = random.choice(list(targets))

        if random.random() * 100 < antiAirDef(gameData, target):
            repelled.add(plane)
        elif random.random() * 100 < getUnitData(gameData, plane.type)[1]["Accuracy"]["Naval"]:
            destroyed.add(target)

        targetted.add(target)

    return destroyed | repelled

def groundBasedAirDefense(gameData, attDivs: list[Unit], defDivs: list[Unit], includeNaval: bool) -> set[Unit]:
    attPlanes = []
    for unit in attDivs:
        if getDomain(gameData, unit.type) == "Air":
            attPlanes += divideUnit(unit)

    totalaa = sum(antiAirDef(gameData, unit) for unit in defDivs if getDomain(gameData, unit.type) == "Ground" or (includeNaval and getDomain(gameData, unit.type) == "Naval"))
    if totalaa == 0 or not attPlanes:
        return set()

    airData = gameData.getDefaultGameData()["Units"]["Air"]
    vulnerability = {unitType: data["Vulnerability"] for unitType, data in airData.items()}
    chance = min(totalaa / len(attPlanes), 0.95 / max(vulnerability.values()))

    shotdown = set()
    for plane in attPlanes:
        if random.random() < chance * vulnerability[plane.type]:
            shotdown.add(plane)

    return shotdown