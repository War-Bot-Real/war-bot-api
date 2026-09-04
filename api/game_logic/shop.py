from api.models.Operation import Operation

def buyItem(nation, gameData, item, quantity):
    shop = gameData.getShop()
    price = None
    for i in shop:
      if item in shop[i]:
        price = shop[i][item] * quantity

    if price == None:
        raise ValueError("Invalid Shop Item")
      
    if nation["Balance"] < price:
        raise ValueError("Not enough money")

    return {
        nation["Name"]: {
            "Balance": Operation("add", -price),
            "Inventory": Operation("add", quantity, item)
        }
    }