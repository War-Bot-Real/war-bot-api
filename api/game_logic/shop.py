from api.models.Operation import Operation

def buyItem(nation, gameData, item, quantity):
    total_cost = gameData.getShop()[item] * quantity

    if nation["Balance"] < total_cost:
        raise ValueError("Not enough money")

    return {
        nation["Name"]: {
            "Balance": Operation("add", -total_cost)
        }
    }