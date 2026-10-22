import random
from api.models import Territory, Sea, Nation, Unit
from api.game_logic.military.management import getUnitData
from api.game_logic.shared import formatTime, findquan, addToDict
from api.game_logic.military.shared import getDomain, canTakeoff, inRange, findCoastOccupant, findFuelRequired, findOwner, getAllBorders, station, antiAirDef, getNavalPower, devastationRatio, convertIntToBattleId, findCooldown, cooldownMultiplier
from api.game_logic.shared import formatList
from api.game_logic.military.pathFinder import shortestPathFinder

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

def calcCasualtyStabLoss(niq: Nation, cas: dict[str, int], won: bool) -> float:
    casnum = sum(cas.values())
    if won:
        stab = -((casnum / 1000) ** 0.8 / 10 ** 0.8) / 2
        # stab += ide[niq.ide].winStab
    else:
        stab = -(casnum / 1000) ** 0.8 / 10 ** 0.8
    return stab

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
    battle = gameData.createBattle(battleLog)

    return {
        "battleId": convertIntToBattleId(battle),
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

class NavalBattleResponse:
    def __init__(self, attWin: bool, destroyedShips: set[Unit], navalLogs: list[str]):
        self.attWin = attWin
        self.destroyedShips = destroyedShips
        self.logs = navalLogs

def navalBattle(gameData, attNation: Nation, attDivs: list[Unit], defDivs: list[Unit]) -> NavalBattleResponse:
    attforce = {"Destroyer": [], "Battleship": [], "Submarine": [], "Other Ships": []}
    defforce = {"Destroyer": [], "Battleship": [], "Submarine": [], "Other Ships": []}
    logs = []

    for unit in attDivs:
        if unit.type in attforce:
            attforce[unit.type] += divideUnit(unit)
        elif getDomain(gameData, unit.type) == "Naval":
            attforce["Other Ships"] += divideUnit(unit)

    for unit in defDivs:
        if unit.type in defforce:
            defforce[unit.type] += divideUnit(unit)
        elif getDomain(gameData, unit.type) == "Naval":
            defforce["Other Ships"] += divideUnit(unit)

    usedDestroyers = set()
    destroyedShips = set()

    for unit in attforce["Destroyer"]:
        targets = set(defforce["Submarine"]) - destroyedShips
        if not targets:
            break
        destroyedShips.add(random.choice(list(targets)))
        usedDestroyers.add(unit)

    for unit in defforce["Destroyer"]:
        targets = set(attforce["Submarine"]) - destroyedShips
        if not targets:
            break
        destroyedShips.add(random.choice(list(targets)))
        usedDestroyers.add(unit)

    logs.append(f"Attacking destroyers hunt {sum(unit in destroyedShips for unit in defforce['Submarine'])} submarines")
    logs.append(f"Defending destroyers hunt {sum(unit in destroyedShips for unit in attforce['Submarine'])} submarines")

    for unit in set(attforce["Submarine"]) - destroyedShips:
        targets = set(defforce["Battleship"] + defforce["Destroyer"] + defforce["Other Ships"]) - destroyedShips
        if not targets:
            break
        destroyedShips.add(random.choice(list(targets)))

    for unit in set(defforce["Submarine"]) - destroyedShips:
        targets = set(attforce["Battleship"] + attforce["Destroyer"] + attforce["Other Ships"]) - destroyedShips
        if not targets:
            break
        destroyedShips.add(random.choice(list(targets)))

    attLost = {}
    defLost = {}
    for unit in destroyedShips:
        if unit.type != "Submarine":
            if unit.nation == attNation.name:
                addToDict(attLost, {unit.type: 1})
            else:
                addToDict(defLost, {unit.type: 1})

    logs.append(f"Attacking submarines sink {formatList([f'{v} {k}{'s' if v != 1 else ''}' for k, v in attLost.items()])}")
    logs.append(f"Defending submarines sink {formatList([f'{v} {k}{'s' if v != 1 else ''}' for k, v in defLost.items()])}")

    navalPower = getNavalPower()

    attChance = len(attforce["Battleship"]) * navalPower["Battleship"] + len(attforce["Destroyer"]) * navalPower["Destroyer"]
    defChance = len(defforce["Battleship"]) * navalPower["Battleship"] + len(defforce["Destroyer"]) * navalPower["Destroyer"]

    for unit in usedDestroyers:
        if unit.nation == attNation.name:
            attChance -= navalPower["Destroyer"]
        else:
            defChance -= navalPower["Destroyer"]

    while attChance > 0 and defChance > 0:
        logs.append(f"AttPower: {attChance}\t\tDefPower: {defChance}")
        r = random.random() * (attChance + defChance)

        if r < attChance:
            targets = set(defforce["Battleship"] + defforce["Destroyer"]) - destroyedShips
            if not targets:
                break
            destroyed = random.choice(list(targets))
            logs.append(f"Attacker lands a hit and sinks enemy {destroyed.type.lower()}")
            if destroyed.type == "Battleship":
                defChance -= navalPower["Battleship"]
            elif destroyed not in usedDestroyers:
                defChance -= navalPower["Destroyer"]
        else:
            targets = set(attforce["Battleship"] + attforce["Destroyer"]) - destroyedShips
            if not targets:
                break
            destroyed = random.choice(list(targets))
            logs.append(f"Defender lands a hit and sinks enemy {destroyed.type.lower()}")
            if destroyed.type == "Battleship":
                attChance -= navalPower["Battleship"]
            elif destroyed not in usedDestroyers:
                attChance -= navalPower["Destroyer"]

        destroyedShips.add(destroyed)

    carriersKilled = random.randint(0, max(0, attChance))
    for _ in range(carriersKilled):
        if not defforce["Other Ships"]:
            break
        sunk = random.choice(defforce["Other Ships"])
        destroyedShips.add(sunk)
        logs.append(f"Attacking Ships sink {sunk.type.lower()}")

    carriersKilled = random.randint(0, max(0, defChance))
    for _ in range(carriersKilled):
        if not attforce["Other Ships"]:
            break
        sunk = random.choice(attforce["Other Ships"])
        destroyedShips.add(sunk)
        logs.append(f"Defending Ships sink {sunk.type.lower()}")

    return NavalBattleResponse(attChance != 0, destroyedShips, logs)
class LandBattleResponse:
    def __init__(self, battleId: str, attWin: bool, attCas: dict[Unit, int], attSaved: int, defCasByNation: dict[str, dict[Unit, int]], defSaved: int, undefended: bool, defFuelShortages: list[str]):
        self.battleId = battleId
        self.attWin = attWin
        self.attCas = attCas
        self.attSaved = attSaved
        self.defCas = defCasByNation
        self.defSaved = defSaved
        self.undefended = undefended
        self.defFuelShortages = defFuelShortages

def landBattle(gameData, tiq: Territory, niq: Nation, attDivs: list[Unit], defDivs: list[Unit]) -> LandBattleResponse:
    defDivsByNation = {}
    for unit in defDivs:
        defDivsByNation.setdefault(unit.nation, []).append(unit)

    attInitial = {unit: unit.quantity for unit in attDivs}
    defInitial = {unit: unit.quantity for unit in defDivs}

    attDivNum = sum(unit.quantity / getUnitData(gameData, unit.type)[1]["Each"] for unit in attDivs)
    defDivNum = sum(unit.quantity / getUnitData(gameData, unit.type)[1]["Each"] for unit in defDivs)
    skirmish = attDivNum < defDivNum * 0.25

    defStrenByNation = {}
    fuelShortages = []
    for nationName, units in defDivsByNation.items():
        reqFuel = []
        dontreqFuel = []
        for unit in units:
            if findFuelRequired(gameData, [unit], "defense") != 0:
                reqFuel.append(unit)
            else:
                dontreqFuel.append(unit)

        dFuelReq = 0 if skirmish else findFuelRequired(gameData, reqFuel, "defense")
        defenderNation = gameData.getNation(nationName)
        inventory = defenderNation.inventory
        fuel = inventory.get("Fuel", 0)

        if dFuelReq > fuel and dFuelReq > 0:
            dFuelMult = fuel / dFuelReq
            inventory["Fuel"] = 0
            fuelShortages.append(defenderNation.name)
        else:
            dFuelMult = 1
            inventory["Fuel"] = fuel - dFuelReq

        gameData.updateNation(defenderNation.name, {"inventory": inventory})
        defStrenByNation[nationName] = strength(gameData, dontreqFuel, "def") + strength(gameData, reqFuel, "def") * dFuelMult
        # defStrenByNation[nationName] *= ide[defenderNation.ideology].defBoost

    tiq.devastation += (attDivNum + defDivNum) * devastationRatio()
    dStren = sum(defStrenByNation.values())
    if tiq.fort():
        dStren *= 2

    aStren = strength(gameData, attDivs, "att")
    aChance = aStren ** 2  # * ide[niq.ideology].attBoost
    dChance = dStren ** 2 * tiq.terrain ** 0.25

    r = random.uniform(0, aChance + dChance)
    if dStren == 0:
        attWin = True
    elif r < aChance:
        attWin = True
    else:
        attWin = False

    casualties = determineCasualties(gameData, tiq, [u for u in attDivs if getDomain(gameData, u.type) == "Ground"], [u for u in defDivs if getDomain(gameData, u.type) == "Ground"], aStren, dStren)

    aLostAll = all(unit.quantity == 0 for unit in casualties["acas"])
    dLostAll = all(unit.quantity == 0 for nationCasualties in casualties["dcas"].values() for unit in nationCasualties)

    if aLostAll:
        attWin = False
    elif dLostAll:
        attWin = True

    if attWin:
        for unit in attDivs:
            unit.location = tiq.name
            gameData.updateUnit(unit.name, {"location": unit.location, "quantity": unit.quantity})

    gameData.updateTerritory(tiq.name, {"devastation": tiq.devastation})

    attackerUnits = [
        {"type": unit.type, "initial_quantity": attInitial[unit], "casualties": casualties["acas"].get(unit, 0), "remaining_quantity": unit.quantity}
        for unit in attDivs
    ]

    defenders = [
        {
            "nation": nationName,
            "units": [
                {"type": unit.type, "initial_quantity": defInitial[unit], "casualties": casualties["dcas"].get(nationName, {}).get(unit, 0), "remaining_quantity": unit.quantity}
                for unit in units
            ]
        }
        for nationName, units in defDivsByNation.items()
    ]

    battleResults = {
        "territory": tiq.name,
        "game_time": gameData.gameTime(),
        "attacker": {"nation": niq.name, "won": attWin, "units": attackerUnits, "saved": casualties["asaved"]},
        "defenders": defenders,
        "defender_saved": casualties["dsaved"],
        "undefended": dChance == 0,
        "fuel_shortages": fuelShortages
    }

    numericBattleId = gameData.createBattle(battleResults)
    battleId = convertIntToBattleId(numericBattleId)

    return LandBattleResponse(battleId, attWin, casualties["acas"], casualties["asaved"], casualties["dcas"], casualties["dsaved"], dChance == 0, fuelShortages)

def landBattleAftermath(gameData, niq: Nation, tiq: Territory, battle: LandBattleResponse):
    if battle.attWin:
        tiq.nation = niq.name
        currentTime = gameData.gameTime()
        integrationMultiplier = cooldownMultiplier()["Integration"]
        newIntegrated = currentTime + (1600 / niq.stability if niq.stability > 0 else 1600) * integrationMultiplier
        if tiq.integrated < newIntegrated:
            tiq.integrated = newIntegrated

        gameData.updateTerritory(tiq.name, {"nation": tiq.nation, "integrated": tiq.integrated})

def determineCasualties(gameData, tiq: Territory, attDivs: list[Unit], defDivs: list[Unit], aStren: float, dStren: float) -> dict:
    median = min(aStren, dStren) / 2
    stdev = median / 3

    amed = sum(unit.quantity for unit in attDivs if unit.type == "Medical Unit")
    dmed = sum(unit.quantity for unit in defDivs if unit.type == "Medical Unit")

    acas = {}
    dcas = {}
    asaved = 0
    dsaved = 0

    for unit in attDivs:
        cas = random.normalvariate(mu=median, sigma=stdev) * unit.quantity / aStren if aStren > 0 else 0
        if unit.type in ["Light Infantry", "Motorized Infantry", "Mechanized Infantry", "Medical Unit"]:
            saved = amed * random.randint(5, 20)
            cas -= saved
            asaved += saved
        cas = max(0, cas)
        if unit.quantity - cas < getUnitData(gameData, unit.type)[1]["Minimum"]:
            cas = unit.quantity
        cas = round(cas)
        unit.quantity -= cas
        acas[unit] = cas

    for unit in defDivs:
        if dStren > 0:
            cas = random.normalvariate(mu=median, sigma=stdev) * unit.quantity / dStren
        else:
            cas = random.randint(0, unit.quantity)
        if unit.type in ["Light Infantry", "Motorized Infantry", "Mechanized Infantry", "Medical Unit"]:
            saved = dmed * random.randint(5, 20)
            cas -= saved
            dsaved += saved
        cas = max(0, cas)
        if unit.quantity - cas < getUnitData(gameData, unit.type)[1]["Minimum"]:
            cas = unit.quantity
        cas = round(cas)
        dcas.setdefault(unit.nation, {})[unit] = cas
        unit.quantity -= cas

    return {"acas": acas, "dcas": dcas, "asaved": asaved, "dsaved": dsaved}
