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