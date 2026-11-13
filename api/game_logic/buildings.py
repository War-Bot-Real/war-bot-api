import math
from api.game_logic.top import calcPower

def getAllBuildings(gameData) -> list[str]:
    return list(gameData.getDefaultGameData()["Buildings"])


def financialCenterLimit(gameData, nation) -> int:
    power = calcPower(gameData, nation)
    if power <= 0:
        return 0
    return max(int(math.floor(math.log(power, 2) + 3)), 1)