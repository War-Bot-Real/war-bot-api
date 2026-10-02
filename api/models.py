class Tile():
  def __init__(self, data):
    self.name = data["Name"]
    self.location = data["Location"]
    self.bordering = data["Bordering"]
        
class Territory(Tile):
  def __init__(self, data):
    super().__init__(data)
    self.nation = data["Nation"]
    self.pop = data["Population"]
    self.buildings = data["Buildings"]
    self.coast = data["Coast"]
    self.integrated = data["Integrated"]
    self.area = data["Area"]
    self.terrain = data["Terrain"]
    self.rails = data["Rails"]
    self.resources = data["Resources"]
    self.devastation = data["Devastation"]

class Sea(Tile):
  def __init__(self, data):
    super().__init__(data)

class Nation():
  def __init__(self, data):
    self.name: str = data["Name"]
    self.balance: float = data["Balance"]
    self.stability: float = data["Stability"]
    self.inventory: dict[str, int | float] = data["Inventory"]
    self.channel: int = data["Channel"]
    self.flag: str = data["Flag"]
    self.taxRate: int = data["Tax Rate"]
    self.politicalPower: int = data["Political Power"]
    self.demonym: str = data["Demonym"]
    self.ideology: str = data["Ideology"]
    self.color: list = data["Color"]
    self.capital: str = data["Capital"]
    self.diplomacy: dict[str, list[str]] = data["Diplomacy"]
    self.ruler = data["ruler"]
    self.centralized: bool = data["Centralized"]
    self.last: dict[str, int] = data["last"]
    self.theaters: dict = data["Theaters"]
    