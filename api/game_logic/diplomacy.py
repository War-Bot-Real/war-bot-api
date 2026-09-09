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