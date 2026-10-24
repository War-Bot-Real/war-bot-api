
import heapq
from itertools import count
from api.models import Territory, Sea
from api.game_logic.military.shared import getAllBorders, calcDistance

def shortestPathFinder(gameData, start: Territory | Sea, end: Territory | Sea, inOneNation: bool = True, railroadsOnly: bool = False, includesTrusted: bool = True, includeSeas: bool = False, unitData=None) -> list[Territory | Sea] | None:
    if isinstance(start, str):
        raise Exception(f"shortestPathFinder start is invalid: {start}")
    if isinstance(end, str):
        raise Exception(f"shortestPathFinder end is invalid: {end}")
    if inOneNation and includeSeas:
        raise Exception("Cannot be both in one nation and include seas.")
    if railroadsOnly and includeSeas:
        raise Exception("Cannot include both railroads and seas.")

    queue = [(0, 0, start, [start])]
    counter = count(1)
    visited = set()
    trusted = gameData.getNation(start.nation).canEnter() if railroadsOnly and inOneNation and includesTrusted else set()

    while queue:
        current_distance, _, current, path = heapq.heappop(queue)

        if current.name in visited:
            continue
        visited.add(current.name)

        if current.name == end.name:
            return path

        if railroadsOnly:
            neighbor_names = current.rails
        elif includeSeas:
            neighbor_names = getAllBorders(gameData, current, unitData)
        else:
            neighbor_names = current.bordering

        for neighbor_name in neighbor_names:
            try:
                neighbor = gameData.getTerritory(neighbor_name)
            except ValueError:
                if not includeSeas:
                    continue
                try:
                    neighbor = gameData.getSea(neighbor_name)
                except ValueError:
                    continue

            if neighbor.name in visited:
                continue

            if inOneNation:
                if railroadsOnly and includesTrusted:
                    if neighbor.nation not in trusted:
                        continue
                elif neighbor.nation != start.nation:
                    continue

            distance = calcDistance(current, neighbor)
            heapq.heappush(queue, (current_distance + distance, next(counter), neighbor, path + [neighbor]))

    return None
