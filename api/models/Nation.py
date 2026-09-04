class Nation:
  def __init__(self, name, ruler, balance, stability, inventory, ideology, channel, flag, taxRate, politicalPower, demonym, color, capital, diplomacy, theaters, settings, schedule, centralized):
    self.name = name
    self.ruler = ruler
    self.bal = balance
    self.stab = stability
    self.inv = inventory
    self.ide = ideology
    self.channel = channel
    self.flag = flag
    self.taxRate = taxRate
    self.pp = politicalPower
    self.demonym = demonym
    self.color = color
    self.capital = capital
    self.diplomacy = diplomacy
    for i in ["Non-Aggression Pacts", "Allies", "Trusted", "Enemies"]:
      if i not in diplomacy:
        self.diplomacy[i] = []
    self.theaters = theaters
    self.settings = settings
    self.schedule = schedule
    self.centralized = centralized