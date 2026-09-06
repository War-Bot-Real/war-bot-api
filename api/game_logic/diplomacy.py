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

        return {
            "accepted": True,
            "nation": otherNation["Name"]
        }

    gameData.createInteraction(nation["Name"], otherNation["Name"], "ally")

    return {
        "accepted": False,
        "nation": otherNation["Name"]
    }