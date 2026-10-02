from api.models import Nation

def registerNation(gameData, nation: Nation, ruler, channel):
    if nation.ruler != 0:
        raise ValueError("That nation already has a ruler!")

    gameData.updateNation(nation.name, {"ruler": ruler, "Channel": channel})

    return {
        "nation": nation.name,
        "ruler": ruler,
        "channel": channel
    }