
from api.models import Territory, Sea, Nation, Unit
from api.game_logic.military import getUnitData
from api.game_logic.shared import calcDistance, pxToKm, formatTime

def station(gameData, division):
    if isinstance(division, str):
        units = gameData.getUnit(division)
        if not units:
            return None
        division = units[0]

    try:
        return gameData.getTerritory(division.location)
    except ValueError:
        pass

    try:
        return gameData.getSea(division.location)
    except ValueError:
        pass

    units = gameData.getUnit(division.location)
    if units:
        return units[0]

    return None

def getCapacity(gameData, unit):
    data = getUnitData(gameData, unit.type)[1]
    return unit.quantity * data.get("Capacity", 0)
  
def getAllBorders(gameData, tile):
    borders = tile.bordering.copy()

    if isinstance(tile, Territory):
        borders += tile.coast

        for unit in gameData.getUnits():
            if unit.location == tile.name and getCapacity(gameData, unit) > 0:
                borders.append(unit.name)
    else:
        for territory in gameData.getAllTerr():
            if tile.name in territory.coast:
                borders.append(territory.name)

    return borders
  
def inRange(gameData, plane, target, roundTrip=True):
    if plane.location in getAllBorders(gameData, target):
        return True

    unitData = getUnitData(gameData, plane.type)[1]
    unitRange = unitData["Range"]

    location = station(gameData, plane)

    if location is None:
        return False

    if isinstance(location, Unit):
        location = station(gameData, location)

        if location is None:
            return False

        if location.name in getAllBorders(gameData, target):
            return True

    distance = calcDistance(location, target)

    if roundTrip:
        distance *= 2

    return pxToKm(gameData, distance) < unitRange

def strength(gameData, divs: list[Unit], type: str) -> float:
    total = 0

    for unit in divs:
        domain, data = getUnitData(gameData, unit.type)
        unitStrength = data.get("Strength", {}).get("Attack" if type == "att" else "Defense")

        if unitStrength is None:
            continue

        total += unit.quantity / data["Each"] * unitStrength * (1.5 if not unit.active else 1)

    return total

def canTakeoff(plane: Unit):
  s = station(plane)
  if isinstance(s, Unit):
    if s.type == "Aircraft Carrier":
      return True
    return False
  if isinstance(s, Territory):
    if "Airport" in s.buildings or "Airstrip" in s.buildings:
      return True
  return False #Shouldn't ever reach here

def findOwner(gameData, sea):
    for unit in gameData.getUnits():
        if unit.location == sea.name and getUnitData(gameData, unit.type)[0] == "Naval" and unit.type != "Submarine":
            return gameData.getNation(unit.nation)
    return None

def findCoastOccupant(gameData, territory):
    for unit in gameData.getUnits():
        if unit.location == territory.name and getUnitData(gameData, unit.type)[0] == "Naval":
            return gameData.getNation(unit.nation)
    return None

def findFuelRequired(gameData, unitlist: list[Unit], action: str) -> float:
    fuelRequired = 0.0

    for unit in unitlist:
        data = getUnitData(gameData, unit.type)[1]
        fuelRequired += data["Fuel"][action.title()] * unit.quantity / data["Each"]

    return fuelRequired

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