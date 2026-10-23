from api.models import Unit, Nation, Territory, Sea, NavalBattleResponse, LandBattleResponse
from api.game_logic.shared import formatNum, estimate

def generateMessage(niq: Nation, attN: Nation, defN: Nation, tile: Territory | Sea, stab: int, allcas, landBattle: LandBattleResponse, navalBattle: NavalBattleResponse):
  if niq == attN:
    msg = attackerMessage(landBattle, navalBattle, tile, defN)
  elif niq == defN:
    msg = defenderMessage(landBattle, navalBattle, tile, attN)
  else:
    msg = allyMessage(landBattle, navalBattle, tile, attN)
  
  casmsg = ""
  if niq.name in allcas:
    print(allcas[niq.name])
    casmsg = formatCasualtyMessage(allcas[niq.name])
  
  if casmsg == "":
    if niq == attN:
      msg += "\n\nYou suffered no casualties!"
    elif landBattle:
      if landBattle.undefended:
        msg += " The territory fell without a fight.\n"
      else:
        msg += " You suffered no casualties.\n"
    else:
      msg += " You suffered no casualties!"
  else:
    msg += "\n\nYou suffered the following casualties:\n" + casmsg    
  
  if landBattle:
    if landBattle.attSaved and niq == attN:
      msg += f"\nYour medical units helped to save {formatNum(landBattle.attSaved)} soldiers!\n"
    elif landBattle.defSaved and niq != attN:
      if len(allcas) <= 2:
        msg += f"\nYour medical units helped to save {formatNum(landBattle.defSaved)} soldiers!\n"
      else:
        msg += f"\nAllied medical units helped to save {formatNum(landBattle.defSaved)} soldiers!\n"
  
  if round(stab, 2) != 0:
    msg += "\nStability: **{}{}%**".format('+' if stab > 0 else '', round(stab, 2))

  if landBattle:
    if niq.name in landBattle.defFuelShortages:
      msg += "\nAdditionally, due to an ongoing fuel shortage, some of your units were not able to defend at full strength."
  
  return msg

def formatCasualtyMessage(cas: dict[str, int], estimateCas: bool = False, separator: str = "\n"):
  casmsgs = []
  for i in cas:
    if cas[i] > 0:
      casmsg = ""
      if estimateCas:
        casmsg += estimate(cas[i]) + " "
      else:
        casmsg += formatNum(cas[i]) + " "

      casmsg += i
      if i[-1] != "y" and (cas[i] > 1 or estimateCas):
        casmsg += "s"
      casmsgs.append(casmsg)
  return separator.join(casmsgs)

def attackerMessage(landBattle: LandBattleResponse, navalBattle: NavalBattleResponse, tile, defN: Nation):
  if navalBattle == None and landBattle == None:
    return f"You attacked {tile.name}."
  
  if landBattle and not navalBattle:
    if landBattle.attWin:
      return f"You have won the battle of {tile.name}! You now occupy this key {defN.demonym} province."
    else:
      return f"Your forces have unfortunately lost the battle of {tile.name}."
    
  if navalBattle and not landBattle:
    if navalBattle.attWin:
      return f"You have won the naval battle of {tile.name}!"
    else:
      return f"Your forces have unfortunately lost the naval battle of {tile.name}."
  
  if navalBattle.attWin == landBattle.attWin:
    if landBattle.attWin:
      return f"You have won the battle of {tile.name} in both land and sea! You now occupy this key {defN.demonym} province."
    else:
      return f"Your forces have unfortunately lost the battle of {tile.name} in both land and sea."
  else:
    if navalBattle.attWin:
      return f"Your forces were able to secure the coast of {tile.name}, however they failed to take the territory itself."
    else:
      return f"Your forces were unable to secure the coast of {tile.name}, however were able to take the territory itself."

def defenderMessage(landBattle: LandBattleResponse, navalBattle: NavalBattleResponse, tile, attN: Nation):
  if navalBattle == None and landBattle == None:
    return f"{attN.demonym} forces attacked {tile.name}."
  
  if landBattle and not navalBattle:
    if landBattle.attWin:
      return f"You have lost {tile.name} to invading {attN.demonym} forces."
    else:
      return f"You have successfully defended the territory of {tile.name} from invading {attN.demonym} forces!"
    
  if navalBattle and not landBattle:
    if navalBattle.attWin:
      return f"You have lost the naval battle of {tile.name} to {attN.demonym} forces."
    else:
      if isinstance(tile, Territory):
        return f"You have successfully defended the coast of {tile.name} from attacking {attN.demonym} forces!"
      else:
        return f"You have successfully defended {tile.name} from attacking {attN.demonym} forces!"
  
  if navalBattle.attWin == landBattle.attWin:
    if landBattle.attWin:
      return f"You have lost the battle of {tile.name} in both land and sea to invading {attN.demonym} forces."
    else:
      return f"You have successfully defended {tile.name} in both land and sea from invading {attN.demonym} forces!"
  else:
    if navalBattle.attWin:
      return f"You have lost the coast of {tile.name} to invading {attN.demonym} forces, however were able to successfully defend the territory itself!"
    else:
      return f"You have lost the territory of {tile.name} to invading {attN.demonym} forces, however were able to successfully defend the coast!"
    
def allyMessage(landBattle: LandBattleResponse, navalBattle: NavalBattleResponse, tile, attN: Nation):
  if navalBattle == None and landBattle == None:
    return f"{attN.demonym} planes attacked {tile.name}."
  
  if bool(navalBattle) ^ bool(landBattle):
    prefix = ""
    name = tile.name
    
    if landBattle and not navalBattle:
      if landBattle.attWin:
        prefix = "un"
      
    if navalBattle and not landBattle:
      if navalBattle.attWin:
        prefix = "un"
      if isinstance(tile, Territory):
        name = f"the coast of {tile.name}"
    
    return f"Your forces participated in the {prefix}successful defense of {name} against {attN.demonym} forces."
  
  if navalBattle.attWin == landBattle.attWin:
    return f"Your forces have participated in the {"un" if landBattle.attWin else ""}successful defense of {tile.name} in both land and sea against {attN.demonym} forces."
  else:
    if navalBattle.attWin:
      return f"Your forces participated in the successful defense of {tile.name}, while losing the coast to invading {attN.demonym} forces."
    else:
      return f"Your forces participated in the unsuccessful defense of {tile.name} to invading {attN.demonym} forces, while successfully defending the coast."

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