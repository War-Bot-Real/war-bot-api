from models.Nation import Nation

def collectIncome(nation: Nation):
    income = 1000
    nation.balance += income

    return {
        "income": income,
        "balance": nation.balance
    }