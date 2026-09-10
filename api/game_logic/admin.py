def registerNation(gameData, nation, ruler, channel):
    if nation["ruler"] != 0:
        raise ValueError("That nation already has a ruler!")

    gameData.updateNation(nation["Name"], {"ruler": ruler, "Channel": channel})

    return {
        "nation": nation["Name"],
        "ruler": ruler,
        "channel": channel
    }