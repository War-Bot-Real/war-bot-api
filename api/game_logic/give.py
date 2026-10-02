def giveMoney(gameData, nation, recipient, amount, message=""):
    if nation.name == recipient.name:
        raise ValueError("You can't give money to yourself")

    if amount <= 0:
        raise ValueError("Amount must be greater than 0")

    if nation.balance < amount:
        raise ValueError(f"You require ${amount - nation.balance} more to give that much money")

    if "Blocked" in recipient.diplomacy:
      
      if nation.name in recipient.diplomacy["Blocked"]:
          raise ValueError(f"{recipient.name} has blocked you, and you are not allowed to send messages or money to them")

    gameData.updateNation(nation.name, {
        "Balance": nation.balance - amount
    })

    gameData.updateNation(recipient.name, {
        "Balance": recipient.balance + amount
    })

    if len(message) > 0:
        gameData.createMessage(nation.name, recipient.name, "message", message, {"money": amount})
    else:
        gameData.createMessage(None, recipient.name, "notification", f"{nation.name} sent you ${amount}")

    return {
        "recipient": recipient.name,
        "amount": amount,
        "message": message
    }