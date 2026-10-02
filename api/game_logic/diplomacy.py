truceTimes = {
  "Broken Alliance": 21600,
  "Broken NAP": 21600,
  "White Peace": 7200,
  "Broken Trusted": 36000
}

def allyNation(gameData, nation, otherNation):
    if nation.name == otherNation.name:
        raise ValueError("You can't ally with yourself")

    if otherNation.name in nation.diplomacy["Allies"]:
        raise ValueError(f'You are already allied with {otherNation.name}')

    existingRequest = gameData.getInteraction(nation.name, otherNation.name, "ally")

    if existingRequest is not None:
        raise ValueError(f'You have already requested an alliance with {otherNation.name}')

    incomingRequest = gameData.getInteraction(otherNation.name, nation.name, "ally")

    if incomingRequest is not None:
        gameData.deleteInteraction(incomingRequest["id"])

        nationDiplomacy = nation.diplomacy.copy()
        nationDiplomacy["Allies"].append(otherNation.name)

        gameData.updateNation(
            nation.name,
            {
                "diplomacy": nationDiplomacy
            }
        )

        otherDiplomacy = otherNation.diplomacy.copy()
        otherDiplomacy["Allies"].append(nation.name)

        gameData.updateNation(
            otherNation.name,
            {
                "diplomacy": otherDiplomacy
            }
        )

        msg = f'{nation.name} has accepted your offer of an alliance. Good luck to you both, and may this alliance last.'
        gameData.createMessage(None, otherNation.name, "ally", msg)

        return {
            "accepted": True,
            "nation": otherNation.name
        }

    gameData.createInteraction(nation.name, otherNation.name, "ally")

    msg = f'{nation.name} has requested an alliance with you. If you accept, you will be called into all defensive wars {nation.name} takes part in.'
    gameData.createMessage(None, otherNation.name, "ally", msg)

    return {
        "accepted": False,
        "nation": otherNation.name
    }
    
def declareWar(gameData, nation, target):
    if nation.name == target.name:
        raise ValueError("You can't declare war on yourself")

    if gameData.atWar(nation.name, target.name):
        raise ValueError("You're already at war with that nation")

    if target.name in nation.diplomacy["Allies"]:
        raise ValueError(f"You are currently allied to {target.name}")

    if target.name in nation.diplomacy["Trusted"]:
        raise ValueError("You cannot go to war with someone you trust")

    napBroken = False

    if target.name in nation.diplomacy["Non-Aggression Pacts"]:
        if nation.ideology != "Fascism":
            raise ValueError(f"You currently have a non-aggression pact with {target.name}")
        napBroken = True

    # TODO: Implement the actual political power cost.
    ppCost = 30

    if nation.political_power < ppCost:
        raise ValueError(f"You require {ppCost - nation.political_power} more political power to declare war on {target.name}")

    defenders = [target.name] + target.diplomacy["Allies"]

    # treatyName = createWhitePeaceTreaty(gameData, nation, target)
    treatyName = "" #remove once testing done
    warDetails = {
        "aggressors": [nation.name],
        "defenders": defenders,
        "treaties": [treatyName]
    }

    # gameData.createInteraction(nation.name, target.name, "war", warDetails)

    nationDiplomacy = nation.diplomacy.copy()

    breakmsg = ""
    if napBroken:
        nationDiplomacy["Non-Aggression Pacts"].remove(target.name)

        targetDiplomacy = target.diplomacy.copy()
        targetDiplomacy["Non-Aggression Pacts"].remove(nation.name)

        gameData.updateNation(target.name, {
            "diplomacy": targetDiplomacy
        })
        breakmsg = ", breaking your non-aggression pact" if napBroken else ""

    gameData.createMessage(None, target.name, "war", f"Alert! {nation.name} has declared war on {target.name}{breakmsg}!")

    for allyName in target.diplomacy["Allies"]:
        gameData.createMessage(None, allyName, "war", f"You have been called into the {nation.demonym}-{target.demonym} War on the side of {target.name}!")

    gameData.createMessage(None, None, "news", f"{nation.name} has declared war on {target.name}!")
    
    gameData.updateNation(nation.name, {
        "political_power": nation.political_power - ppCost,
        "diplomacy": nationDiplomacy
    })

    return {
        "target": target.name,
        "cost": ppCost,
        "nap_broken": napBroken,
        "war": warDetails
    }

def createWhitePeaceTreaty(gameData, nation, target):
    treatyName = f"{nation.demonym}-{target.demonym} White Peace"

    treaty = {
        "name": treatyName,
        "author": "Auto-Generated",
        "draft": False,
        "truce": truceTimes["White Peace"],
        "reparations": {},
        "borders": {},
        "ratifiers": []
    }

    participants = [nation.name, target.name] + target.diplomacy["Allies"]

    for participant in participants:
        treaty["borders"][participant] = [territory.name for territory in gameData.getNationTerr(participant)]

    if target.ruler is None:
        treaty["ratifiers"].append(target.name)

    gameData.createTreaty(treaty)
    
    return treatyName