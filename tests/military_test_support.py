from copy import deepcopy
from types import SimpleNamespace

from api.models import Nation, Sea, Territory, Unit
from api.repositories.gameData import GameData


class MemorySupabase:
    def __init__(self, tables):
        self.tables = tables
        self.writes = []

    def table(self, name):
        return MemoryQuery(self, name)


class MemoryQuery:
    def __init__(self, supabase, table):
        self.supabase = supabase
        self.table_name = table
        self.operation = "select"
        self.changes = None
        self.filters = []

    def select(self, _columns):
        self.operation = "select"
        return self

    def update(self, changes):
        self.operation = "update"
        self.changes = changes
        return self

    def insert(self, row):
        self.operation = "insert"
        self.changes = row
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def execute(self):
        rows = self.supabase.tables.setdefault(self.table_name, [])
        if self.operation == "insert":
            row = deepcopy(self.changes)
            if self.table_name == "battles":
                row["id"] = len(rows) + 1
            rows.append(row)
            self.supabase.writes.append((self.table_name, "insert", deepcopy(row)))
            return SimpleNamespace(data=[row])

        matching = [
            row for row in rows
            if all(row.get(field) == value for field, value in self.filters)
        ]
        if self.operation == "update":
            for row in matching:
                row.update(deepcopy(self.changes))
            self.supabase.writes.append((
                self.table_name,
                "update",
                list(self.filters),
                deepcopy(self.changes)
            ))
        return SimpleNamespace(data=matching)


class InMemoryGameData(GameData):
    def __init__(self, territories=(), seas=(), nations=(), units=(), wars=()):
        self.territories = {territory.name: territory for territory in territories}
        self.seas = {sea.name: sea for sea in seas}
        self.nations = {nation.name: nation for nation in nations}
        self.units = {unit.name: unit for unit in units}

        tables = {
            "units": [
                {
                    "name": unit.name,
                    "type": unit.type,
                    "quantity": unit.quantity,
                    "nation": unit.nation,
                    "location": unit.location,
                    "tiredUntil": unit.tiredUntil,
                    "active": unit.active
                }
                for unit in units
            ],
            "nations": [
                {
                    "name": nation.name,
                    "inventory": deepcopy(nation.inventory),
                    "stability": nation.stability
                }
                for nation in nations
            ],
            "interactions": list(wars),
            "battles": []
        }
        self.memory_supabase = MemorySupabase(tables)
        super().__init__(self.memory_supabase)
        self.default_data = {
            "Units": {
                "Ground": {
                    "Infantry": {
                        "Short Form": "IN",
                        "Each": 1,
                        "Fuel": {"Movement": 0, "Attack": 0},
                        "Speed": {"Exponent": 0.5, "Divisor": 1},
                        "Strength": {"Attack": 1, "Defense": 1},
                        "Minimum": 1
                    }
                },
                "Naval": {
                    "Destroyer": {
                        "Short Form": "DE",
                        "Each": 1,
                        "Fuel": {"Movement": 0, "Attack": 0},
                        "Cooldown": 10
                    }
                },
                "Air": {
                    "Fighter": {
                        "Short Form": "FI",
                        "Each": 1,
                        "Fuel": {"Movement": 2, "Attack": 2},
                        "Range": 25,
                        "Cooldown": 1,
                        "Aircraft Interception": 0
                    }
                }
            }
        }

    def getAllTerr(self):
        return list(self.territories.values())

    def getAllSeas(self):
        return list(self.seas.values())

    def getAllNations(self):
        return list(self.nations.values())

    def getNationTerr(self, nationName):
        return [
            territory for territory in self.territories.values()
            if territory.nation == nationName
        ]

    def getTerritory(self, name):
        if name not in self.territories:
            raise ValueError(f"Territory '{name}' not found")
        return self.territories[name]

    def getSea(self, name):
        if name not in self.seas:
            raise ValueError(f"Sea '{name}' not found")
        return self.seas[name]

    def getNation(self, name):
        if name not in self.nations:
            raise ValueError(f"Nation '{name}' not found")
        return self.nations[name]

    def getUnit(self, name, throwError=False):
        unit = self.units.get(name)
        if unit is None and throwError:
            raise ValueError(f"Unit '{name}' not found")
        return unit

    def getUnits(self, nation=None):
        return list(self.units.values())

    def getDefaultGameData(self):
        return self.default_data

    def getMapData(self, _mapName):
        return {"pxToKm": 1}

    def getMapName(self):
        return "Test Map"

    def gameTime(self):
        return 100


def make_nation(name, trusted=(), inventory=None):
    return Nation({
        "name": name,
        "balance": 0,
        "stability": 1,
        "inventory": inventory if inventory is not None else {"Fuel": 100},
        "channel": None,
        "flag": "",
        "tax_rate": 0,
        "political_power": 0,
        "demonym": name,
        "ideology": "",
        "color": "",
        "capital": "",
        "diplomacy": {"Trusted": list(trusted), "Enemies": []},
        "ruler": None,
        "centralized": False,
        "last": {},
        "theaters": {}
    })


def make_territory(name, nation, *, location=(0, 0), bordering=(), coast=(), buildings=()):
    return Territory({
        "name": name,
        "location": [list(location)],
        "bordering": list(bordering),
        "nation": nation,
        "population": 0,
        "buildings": list(buildings),
        "coast": list(coast),
        "integrated": 0,
        "area": 0,
        "terrain": 0,
        "rails": [],
        "resources": {},
        "devastation": 0
    })


def make_sea(name, *, location=(0, 0), bordering=()):
    return Sea({
        "name": name,
        "location": list(location),
        "bordering": list(bordering)
    })


def make_unit(name, unit_type, nation, location, *, tired_until=0):
    return Unit({
        "name": name,
        "type": unit_type,
        "quantity": 1,
        "nation": nation,
        "location": location,
        "tiredUntil": tired_until,
        "active": True
    })
