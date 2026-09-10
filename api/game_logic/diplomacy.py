truceTimes = {
  "Broken Alliance": 21600,
  "Broken NAP": 21600,
  "White Peace": 7200,
  "Broken Trusted": 36000
}

def allyNation(gameData, nation, otherNation):
    if nation["Name"] == otherNation["Name"]:
        raise ValueError("You can't ally with yourself")

    if otherNation["Name"] in nation["Diplomacy"]["Allies"]:
        raise ValueError(f'You are already allied with {otherNation["Name"]}')

    existingRequest = gameData.getInteraction(nation["Name"], otherNation["Name"], "ally")

    if existingRequest is not None:
        raise ValueError(f'You have already requested an alliance with {otherNation["Name"]}')

    incomingRequest = gameData.getInteraction(otherNation["Name"], nation["Name"], "ally")

    if incomingRequest is not None:
        gameData.deleteInteraction(incomingRequest["id"])

        nationDiplomacy = nation["Diplomacy"].copy()
        nationDiplomacy["Allies"].append(otherNation["Name"])

        gameData.updateNation(
            nation["Name"],
            {
                "Diplomacy": nationDiplomacy
            }
        )

        otherDiplomacy = otherNation["Diplomacy"].copy()
        otherDiplomacy["Allies"].append(nation["Name"])

        gameData.updateNation(
            otherNation["Name"],
            {
                "Diplomacy": otherDiplomacy
            }
        )

        msg = f'{nation["Name"]} has accepted your offer of an alliance. Good luck to you both, and may this alliance last.'
        gameData.createMessage(nation["Name"], otherNation["Name"], "ally", msg)

        return {
            "accepted": True,
            "nation": otherNation["Name"]
        }

    gameData.createInteraction(nation["Name"], otherNation["Name"], "ally")

    msg = f'{nation["Name"]} has requested an alliance with you. If you accept, you will be called into all defensive wars {nation["Name"]} takes part in.'
    gameData.createMessage( nation["Name"], otherNation["Name"], "ally", msg)

    return {
        "accepted": False,
        "nation": otherNation["Name"]
    }
    
def declareWar(gameData, nation, target):
    if nation["Name"] == target["Name"]:
        raise ValueError("You can't declare war on yourself")

    if gameData.atWar(nation["Name"], target["Name"]):
        raise ValueError("You're already at war with that nation")

    if target["Name"] in nation["Diplomacy"]["Allies"]:
        raise ValueError(f"You are currently allied to {target['Name']}")

    if target["Name"] in nation["Diplomacy"]["Trusted"]:
        raise ValueError("You cannot go to war with someone you trust")

    napBroken = False

    if target["Name"] in nation["Diplomacy"]["Non-Aggression Pacts"]:
        if nation["Ideology"] != "Fascism":
            raise ValueError(f"You currently have a non-aggression pact with {target['Name']}")
        napBroken = True

    # TODO: Implement the actual political power cost.
    ppCost = 30

    if nation["Political Power"] < ppCost:
        raise ValueError(f"You require {ppCost - nation['Political Power']} more political power to declare war on {target['Name']}")

    defenders = [target["Name"]] + target["Diplomacy"]["Allies"]

    treatyName = createWhitePeaceTreaty(gameData, nation, target)
    warDetails = {
        "aggressors": [nation["Name"]],
        "defenders": defenders,
        "treaties": [treatyName]
    }

    gameData.createInteraction(
        nation["Name"],
        target["Name"],
        "war",
        warDetails
    )

    nationDiplomacy = nation["Diplomacy"].copy()

    if napBroken:
        nationDiplomacy["Non-Aggression Pacts"].remove(target["Name"])

        targetDiplomacy = target["Diplomacy"].copy()
        targetDiplomacy["Non-Aggression Pacts"].remove(nation["Name"])

        gameData.updateNation(target["Name"], {
            "Diplomacy": targetDiplomacy
        })

    gameData.updateNation(nation["Name"], {
        "Political Power": nation["Political Power"] - ppCost,
        "Diplomacy": nationDiplomacy
    })

    return {
        "target": target["Name"],
        "cost": ppCost,
        "nap_broken": napBroken,
        "war": warDetails
    }

def createWhitePeaceTreaty(gameData, nation, target):
    treatyName = f"{nation['Demonym']}-{target['Demonym']} White Peace"

    treaty = {
        "name": treatyName,
        "author": "Auto-Generated",
        "draft": False,
        "truce": truceTimes["White Peace"],
        "reparations": {},
        "borders": {},
        "ratifiers": []
    }

    participants = [nation["Name"], target["Name"]] + target["Diplomacy"]["Allies"]

    for participant in participants:
        treaty["borders"][participant] = [
            territory["Name"]
            for territory in gameData.getNationTerr(participant)
        ]

    if target.get("ruler") is None:
        treaty["ratifiers"].append(target["Name"])

    gameData.createTreaty(treaty)
    
    return treatyName