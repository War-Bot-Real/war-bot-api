from api.repositories.gameData import GameData
from api.models import Nation

def createTheater(gameData: GameData, nation: Nation, name: str):
    if not name.strip():
        raise ValueError("Theater name cannot be empty")

    # I don't think we'll need the following code, but I am preserving the logic from the discord bot so we might need it
    # if name.lower() in ["list", "help", "delete", "create", "c", "d", "add", "remove", "a", "r", "map"]:
    #     raise ValueError("That theater name is reserved")

    if any(theater.lower() == name.lower() for theater in nation.theaters):
        raise ValueError("You already have a theater with that name")

    theaters = dict(nation.theaters)
    theaters[name] = {"territories": [], "seas": []}

    gameData.updateNation(nation.name, {"theaters": theaters})
    return {"name": name, "territories": [], "seas": []}