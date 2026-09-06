from api.models.Operation import Operation

def buyItem(nation, gameData, item, quantity):
    shop = gameData.getShop()
    price = None

    for category in shop:
        if item in shop[category]:
            price = shop[category][item] * quantity

    if price is None:
        raise ValueError("Invalid Shop Item")

    if nation["Balance"] < price:
        raise ValueError("Not enough money")

    inventory = nation["Inventory"].copy()

    inventory[item] = inventory.get(item, 0) + quantity

    gameData.updateNation(
        nation["Name"],
        {
            "Balance": nation["Balance"] - price,
            "Inventory": inventory
        }
    )

    return {
        "item": item,
        "quantity": quantity,
        "price": price
    }