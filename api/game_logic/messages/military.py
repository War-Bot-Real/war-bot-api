from api.models import Unit

def formatRetreatMessage(byTile) -> str:
    msg = ""
    for i in byTile:
        if isinstance(i, Unit):
            msg += f"\nTo {i.type} {i.id}: "
        else:
            msg += f"\nTo {i.name}: "
        msg += "<c>{}</c>".format("</c>, <c>".join(byTile[i]))
    return msg
  
def formatIndividualCas(cas: dict[Unit, int], destroyed: dict[Unit, list[str]] | None = None, includeDestroyMsg: bool = True) -> str:
  msg = ""
  destroyed = destroyed or {}
  for i in cas:
      if cas[i] > 0:
          msg += f"\n{cas[i]} from {i.type} Division <c>{i.id}</c>."
          if i.quan == 0:
              if includeDestroyMsg:
                  msg += " Division completely destroyed."
              lost = destroyed.get(i, [])
              if lost:
                  msg += f" Divisions lost alongside this {i.type}: <c>{'</c>, <c>'.join(lost)}</c>"
  return msg

def annexSuccess(defender: str, money: str, inventory: str, ships: str, stability: str) -> str:
    msg = f"<h2>{defender} has capitulated!</h2> {money} {inventory}"
    if ships:
        msg += f"\nYou also seized the following boats:{ships}"
    return f"{msg}\n{stability}"

def annexFailed(defender: str) -> str:
    return f"\nWhile {defender} has completely capitulated, its pesky allies continue to keep it alive! Finalize your conquest by drafting a treaty!"

def annexAtSea(defender: str) -> str:
    return f"While this was their last territory, {defender} lives on at sea!"

def annexAward(defender: str, money: str, stability: str) -> str:
    return f"{defender} has capitulated, and you have been awarded ${money}!\n{stability}"

def annexNews(defenderFlag: str, defender: str, attackerFlag: str, attackerDemonym: str) -> str:
    return f"<f>{defenderFlag}</f> <b>{defender}</b> has capitulated to <f>{attackerFlag}</f> <b>{attackerDemonym}</b> forces, and now ceases to exist!"