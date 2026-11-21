from api.repositories.gameData import GameData
from api.models import Nation
from api.game_logic.shared import findItem
  
def createTheater(gameData: GameData, nation: Nation, name: str, items: list[str]):
    if not name.strip():
        raise ValueError("Theater name cannot be empty")

    # I don't think we'll need the following code, but I am preserving the logic from the discord bot so we might need it
    # if name.lower() in ["list", "help", "delete", "create", "c", "d", "add", "remove", "a", "r", "map"]:
    #     raise ValueError("That theater name is reserved")

    if any(theater.lower() == name.lower() for theater in nation.theaters):
        raise ValueError("You already have a theater with that name")

    theaters = {k: dict(v) for k, v in nation.theaters.items()}
    theaters[name] = {"territories": [], "seas": []}

    result = addtoTheater(gameData, nation, name, items, theaters)
    gameData.updateNation(nation.name, {"theaters": theaters})

    return {"name": name, **theaters[name], "tiles": result}

def getTheater(nation: Nation, name: str):
    for theater in nation.theaters:
        if theater.lower() == name.lower():
            return {"name": theater, **nation.theaters[theater]}

    raise ValueError(f"Theater '{name}' not found")

def addtoTheater(gameData: GameData, nation: Nation, name: str, items: list[str], theaters=None):
    if theaters is None:
        theaters = {k: dict(v) for k, v in nation.theaters.items()}

    theaterName = next((t for t in theaters if t.lower() == name.lower()), None)
    if theaterName is None:
        raise ValueError(f"Theater '{name}' not found")

    theater = theaters[theaterName]
    results = {"added": [], "failed": []}

    territories = gameData.getAllTerr()
    seas = gameData.getAllSeas()

    for item in items:
        terrMatches = findItem(item, territories, "name")
        seaMatches = findItem(item, seas, "name")

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

    if results["added"] and theaters is nation.theaters:
        gameData.updateNation(nation.name, {"theaters": theaters})

    return results
  
def removeFromTheater(gameData: GameData, nation: Nation, name: str, items: list[str]):
    theaterName = next((t for t in nation.theaters if t.lower() == name.lower()), None)
    if theaterName is None:
        raise ValueError(f"Theater '{name}' not found")

    theaters = {k: dict(v) for k, v in nation.theaters.items()}
    theater = theaters[theaterName]

    territories = gameData.getAllTerr()
    seas = gameData.getAllSeas()
    results = {"removed": [], "failed": []}

    for item in items:
        terrMatches = findItem(item, territories, "name")
        seaMatches = findItem(item, seas, "name")

        matches = [(t, "territories") for t in terrMatches if t.name in theater["territories"]]
        matches += [(s, "seas") for s in seaMatches if s.name in theater["seas"]]

        if len(matches) == 0:
            if not terrMatches and not seaMatches:
                reason = "Not found"
            else:
                reason = "Not in theater"
            results["failed"].append({"name": item, "reason": reason})
            continue

        if len(matches) > 1:
            results["failed"].append({"name": item, "reason": "Ambiguous name"})
            continue

        entity, category = matches[0]
        theater[category].remove(entity.name)
        results["removed"].append({"name": entity.name, "type": category})

    if results["removed"]:
        gameData.updateNation(nation.name, {"theaters": theaters})

    return results

def deleteTheater(gameData: GameData, nation: Nation, name: str):
    theaterName = next((t for t in nation.theaters if t.lower() == name.lower()), None)
    if theaterName is None:
        raise ValueError(f"Theater '{name}' not found")

    theaters = dict(nation.theaters)
    del theaters[theaterName]

    gameData.updateNation(nation.name, {"theaters": theaters})
    return {"deleted": theaterName}