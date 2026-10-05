from api.models import Territory

def formatList(l: list, conjunction: str = "and"):
  l = l.copy()
  if len(l) < 2:
    return " ".join(l)
  elif len(l) == 2:
    return "{} {} {}".format(l[0], conjunction, l[1])
  else:
    last = l.pop()
    return "{}, {} {}".format(", ".join(l), conjunction, last)

def findItem(item, items, key) -> list:
  item = " ".join(item.strip().split("_")).lower()
  matches = []
  
  for i in items:
    value = getattr(i, key) if not isinstance(i, dict) else i[key]
    
    if value.lower() == item:
      return [i]
    if item in value.lower():
      matches.append(i)
  
  return matches

def quadify(arg):
  if type(arg) == type(str()):
    if not arg.isdigit():
      return (arg)
  z = ""
  arg = str(arg)
  if len(arg) < 4:
    for i in range(4 - len(arg)):
      z += "0"
  z += arg
  return (z)
  
def pxToKm(gameData, distance):
    return distance * gameData.getMapData()["pxToKm"]

def calcDistance(tile1, tile2):
    loc1 = tile1.location
    loc2 = tile2.location

    if isinstance(tile1, Territory):
        loc1 = loc1[0]

    if isinstance(tile2, Territory):
        loc2 = loc2[0]

    x1, y1 = float(loc1[0]), float(loc1[1])
    x2, y2 = float(loc2[0]), float(loc2[1])
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5