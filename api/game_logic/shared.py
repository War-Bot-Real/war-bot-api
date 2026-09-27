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
    if i[key].lower() == item:
      return [i]
    if item in i[key].lower():
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