def formatList(l: list, conjunction: str = "and"):
  l = l.copy()
  if len(l) < 2:
    return " ".join(l)
  elif len(l) == 2:
    return "{} {} {}".format(l[0], conjunction, l[1])
  else:
    last = l.pop()
    return "{}, {} {}".format(", ".join(l), conjunction, last)