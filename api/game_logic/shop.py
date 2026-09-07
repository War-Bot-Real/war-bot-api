from api.game_logic.shared import formatList

def buyItem(nation, gameData, item, quantity):
    shop = gameData.getShop()
    price = {}

    for category in shop:
        if item in shop[category]:
            for x in shop[category][item]:
                price[x] = shop[category][item][x] * quantity
            break

    if price == {}:
        raise ValueError("Invalid Shop Item")

    notEnough = []
    for i in price:
      if i == "Money":
        if nation["Balance"] < price["Money"]:
          notEnough.append(i)
      else:
        if i not in nation["Inventory"]:
          notEnough.append(i)
          continue
        if nation["Inventory"][i] < price[i]:
          notEnough.append(i)
    
    if len(notEnough) > 0:
        raise ValueError(f"Not Enough {formatList(notEnough, 'or')}")
      
    inventory = nation["Inventory"].copy()
    inventory[item] = inventory.get(item, 0) + quantity
    for i in price:
      if i != "Money":
        nation["Inventory"][i] -= price[i]
    newbalance = nation["Balance"] - price["Money"]
    
    gameData.updateNation(
        nation["Name"],
        {
            "Balance": newbalance,
            "Inventory": inventory
        }
    )

    return {
        "item": item,
        "quantity": quantity,
        "price": price,
        "New Balance": newbalance
    }