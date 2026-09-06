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

    return [
        {
            "table": "nations",
            "where": {
                "Name": nation["Name"]
            },
            "changes": {
                "Balance": Operation("add", -price),
                "Inventory": Operation("add", quantity, item)
            }
        }
    ]