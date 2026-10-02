class Tile:
  def __init__(self, data):
    self.name = data["name"]
    self.location = data["location"]
    self.bordering = data["bordering"]


class Territory(Tile):
  def __init__(self, data):
    super().__init__(data)
    self.nation = data["nation"]
    self.pop = data["population"]
    self.buildings = data["buildings"]
    self.coast = data["coast"]
    self.integrated = data["integrated"]
    self.area = data["area"]
    self.terrain = data["terrain"]
    self.rails = data["rails"]
    self.resources = data["resources"]
    self.devastation = data["devastation"]

class Sea(Tile):
  def __init__(self, data):
    super().__init__(data)

class Nation:
  def __init__(self, data):
    self.name = data["name"]
    self.balance = data["balance"]
    self.stability = data["stability"]
    self.inventory = data["inventory"]
    self.channel = data["channel"]
    self.flag = data["flag"]
    self.tax_rate = data["tax_rate"]
    self.political_power = data["political_power"]
    self.demonym = data["demonym"]
    self.ideology = data["ideology"]
    self.color = data["color"]
    self.capital = data["capital"]
    self.diplomacy = data["diplomacy"]
    self.ruler = data["ruler"]
    self.centralized = data["centralized"]
    self.last = data["last"]
    self.theaters = data["theaters"]