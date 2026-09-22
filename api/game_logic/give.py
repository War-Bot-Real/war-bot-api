def giveMoney(gameData, nation, recipient, amount, message=""):
    if nation["Name"] == recipient["Name"]:
        raise ValueError("You can't give money to yourself")

    if amount <= 0:
        raise ValueError("Amount must be greater than 0")

    if nation["Balance"] < amount:
        raise ValueError(f"You require ${amount - nation['Balance']} more to give that much money")

    if "Blocked" in recipient["Diplomacy"]:
      if nation["Name"] in recipient["Diplomacy"]["Blocked"]:
          raise ValueError(f"{recipient['Name']} has blocked you, and you are not allowed to send messages or money to them")

    gameData.updateNation(nation["Name"], {
        "Balance": nation["Balance"] - amount
    })

    gameData.updateNation(recipient["Name"], {
        "Balance": recipient["Balance"] + amount
    })

    if len(message) > 0:
        gameData.createMessage(nation["Name"], recipient["Name"], "message", message)

    gameData.createMessage(None, recipient["Name"], "notification", f"You received ${amount} from {nation['Name']}")

    return {
        "recipient": recipient["Name"],
        "amount": amount,
        "message": message
    }