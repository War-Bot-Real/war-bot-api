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

def getTheater(nation: Nation, name: str):
    for theater in nation.theaters:
        if theater.lower() == name.lower():
            return {"name": theater, **nation.theaters[theater]}

    raise ValueError(f"Theater '{name}' not found")

def addtoTheater(gameData: GameData, nation: Nation, name: str, items: list[str]):
    theaterName = next((t for t in nation.theaters if t.lower() == name.lower()), None)
    if theaterName is None:
        raise ValueError(f"Theater '{name}' not found")

    theaters = {k: dict(v) for k, v in nation.theaters.items()}
    theater = theaters[theaterName]

    results = {"added": [], "failed": []}

    for item in items:
        territories = gameData.getAllTerr()
        seas = gameData.getAllSeas()

        terrMatches = [t for t in territories if t.name.lower() == item.strip().lower()]
        seaMatches = [s for s in seas if s.name.lower() == item.strip().lower()]

        if len(terrMatches) + len(seaMatches) == 0:
            results["failed"].append({"name": item, "reason": "Not found"})
            continue

        if len(terrMatches) + len(seaMatches) > 1:
            results["failed"].append({"name": item, "reason": "Ambiguous name"})
            continue

        entity = terrMatches[0] if terrMatches else seaMatches[0]
        category = "territories" if terrMatches else "seas"

        if entity.name in theater[category]:
            results["failed"].append({"name": item, "reason": "Already in theater"})
            continue

        theater[category].append(entity.name)
        results["added"].append({"name": entity.name, "type": category})

    if results["added"]:
        gameData.updateNation(nation.name, {"theaters": theaters})

    return results