import pytest
from api.game_logic.military.shared import canTakeoff, dead, findCooldown, findWeight, getCapacity, getDomain, inRange
from api.game_logic.military.attack import aircraftInterception, executeBattleCas, groundBombardment
from api.game_logic.shared import getSettings
from api.models import Nation, Territory, Unit

class FakeGameData:
    def __init__(self, units):
        self.data = {"Units": units}

    def getDefaultGameData(self):
        return self.data

@pytest.fixture
def transporter():
    return Unit({
        "name": "TR-1",
        "type": "Transporter",
        "quantity": 1,
        "nation": "France",
        "location": "Paris",
        "tiredUntil": 0,
        "active": True
    })

@pytest.fixture
def gameData():
    return FakeGameData({
        "Naval": {
            "Transporter": {"Short Form": "TR", "Capacity": 10}
        },
        "Air": {
            "Fighter": {"Short Form": "FI", "Weight": 0.2}
        }
    })

def test_transporter_capacity(gameData, transporter):
    assert getCapacity(gameData, transporter) == 10

def test_execute_battle_cas_applies_counted_land_losses_to_survivors_and_destroyed_units():
    class UnitCasGameData:
        def __init__(self):
            self.updated = {}
            self.deleted = []

        def updateUnit(self, name, changes):
            self.updated[name] = changes

        def deleteUnit(self, name):
            self.deleted.append(name)

    gameData = UnitCasGameData()
    survivor = Unit({
        "name": "LI-1",
        "type": "Light Infantry",
        "quantity": 5,
        "nation": "France",
        "location": "Lyon",
        "tiredUntil": 12,
        "active": True
    })
    destroyed = Unit({
        "name": "LI-2",
        "type": "Light Infantry",
        "quantity": 2,
        "nation": "France",
        "location": "Paris",
        "tiredUntil": 0,
        "active": True
    })
    defender = Unit({
        "name": "LI-3",
        "type": "Light Infantry",
        "quantity": 4,
        "nation": "Spain",
        "location": "Madrid",
        "tiredUntil": 0,
        "active": True
    })

    attDivs = [survivor, destroyed]
    defDivs = [defender]
    losses = executeBattleCas(gameData, attDivs, defDivs, {survivor: 2, destroyed: 2, defender: 3})

    assert losses == {survivor: 2, destroyed: 2, defender: 3}
    assert survivor.quantity == 3
    assert defender.quantity == 1
    assert gameData.updated == {"LI-1": {"quantity": 3}, "LI-3": {"quantity": 1}}
    assert gameData.deleted == ["LI-2"]
    assert attDivs == [survivor]
    assert defDivs == [defender]

def test_capacity_missing_returns_zero(gameData):
    unit = Unit({
        "name": "FI-1",
        "type": "Fighter",
        "quantity": 1,
        "nation": "France",
        "location": "Paris",
        "tiredUntil": 0,
        "active": True
    })
    assert getCapacity(gameData, unit) == 0

def test_capacity_can_be_zero():
    gameData = FakeGameData({
        "Naval": {
            "Transporter": {"Capacity": 0}
        }
    })
    unit = Unit({
        "name": "TR-1",
        "type": "Transporter",
        "quantity": 1,
        "nation": "France",
        "location": "Paris",
        "tiredUntil": 0,
        "active": True
    })
    assert getCapacity(gameData, unit) == 0

def test_capacity_is_numeric(gameData, transporter):
    assert isinstance(getCapacity(gameData, transporter), (int, float))

def test_can_takeoff_uses_game_data_to_resolve_station():
    territory = Territory({
        "name": "Paris",
        "location": [0, 0],
        "bordering": [],
        "nation": "France",
        "population": 0,
        "buildings": ["Airstrip"],
        "coast": [],
        "integrated": 0,
        "area": 0,
        "terrain": 0,
        "rails": [],
        "resources": {},
        "devastation": 0
    })

    class StationGameData:
        def getTerritory(self, name):
            if name != territory.name:
                raise ValueError(name)
            return territory

        def getSea(self, name):
            raise ValueError(name)

        def getUnit(self, name):
            return None

    plane = Unit({
        "name": "FI-1",
        "type": "Fighter",
        "quantity": 1,
        "nation": "France",
        "location": territory.name,
        "tiredUntil": 0,
        "active": True
    })

    assert canTakeoff(StationGameData(), plane)

def test_nation_can_enter_includes_self_and_trusted_nations():
    nation = Nation({
        "name": "France",
        "balance": 0,
        "stability": 0,
        "inventory": {},
        "channel": None,
        "flag": "",
        "tax_rate": 0,
        "political_power": 0,
        "demonym": "",
        "ideology": "",
        "color": "",
        "capital": "",
        "diplomacy": {"Trusted": ["Spain"]},
        "ruler": None,
        "centralized": False,
        "last": {},
        "theaters": {}
    })

    assert nation.canEnter() == {"France", "Spain"}

def test_find_weight_returns_unit_load_weight():
    gameData = FakeGameData({
        "Naval": {
            "Transporter": {"Short Form": "TR", "Weight": 4, "Each": 2}
        }
    })
    unit = Unit({
        "name": "TR-1",
        "type": "Transporter",
        "quantity": 6,
        "nation": "France",
        "location": "Paris",
        "tiredUntil": 0,
        "active": True
    })

    assert findWeight(gameData, [unit]) == 12

def test_dead_checks_unit_domain_with_game_data():
    navalUnit = Unit({
        "name": "TR-1",
        "type": "Transporter",
        "quantity": 1,
        "nation": "France",
        "location": "Sea",
        "tiredUntil": 0,
        "active": True
    })

    class DeadGameData(FakeGameData):
        def getNationTerr(self, nation):
            return []

        def getUnits(self):
            return [navalUnit]

    nation = Nation({
        "name": "France",
        "balance": 0,
        "stability": 0,
        "inventory": {},
        "channel": None,
        "flag": "",
        "tax_rate": 0,
        "political_power": 0,
        "demonym": "",
        "ideology": "",
        "color": "",
        "capital": "",
        "diplomacy": {"Trusted": []},
        "ruler": None,
        "centralized": False,
        "last": {},
        "theaters": {}
    })
    gameData = DeadGameData({
        "Naval": {"Transporter": {"Short Form": "TR"}}
    })

    assert dead(gameData, nation)

def test_nation_settings_default_to_empty_and_get_settings_adds_defaults():
    nation = Nation({
        "name": "France",
        "balance": 0,
        "stability": 0,
        "inventory": {},
        "channel": None,
        "flag": "",
        "tax_rate": 0,
        "political_power": 0,
        "demonym": "",
        "ideology": "",
        "color": "",
        "capital": "",
        "diplomacy": {"Trusted": []},
        "ruler": None,
        "centralized": False,
        "last": {},
        "theaters": {}
    })
    class SettingsGameData:
        def getDefaultGameData(self):
            return {"Settings": {"Player": {"Allow trusted carrier retreats": {"Default": False}}}}

    gameData = SettingsGameData()

    assert getSettings(gameData, nation) == {"Allow trusted carrier retreats": False}

def test_domain_lookup_returns_unit_domain(gameData):
    assert getDomain(gameData, "Transporter") == "Naval"
    assert getDomain(gameData, "Fighter") == "Air"

def test_ground_bombardment_resolves_ground_target_units():
    gameData = FakeGameData({
        "Air": {
            "Bomber": {
                "Short Form": "BM",
                "Bombing": {"Limit": 2, "Strength": 1}
            }
        },
        "Ground": {
            "Light Infantry": {
                "Short Form": "LI",
                "Each": 1,
                "Strength": {"Attack": 1, "Defense": 1}
            }
        }
    })
    bomber = Unit({
        "name": "BM-1",
        "type": "Bomber",
        "quantity": 1,
        "nation": "France",
        "location": "Paris",
        "tiredUntil": 0,
        "active": True
    })
    infantry = Unit({
        "name": "LI-1",
        "type": "Light Infantry",
        "quantity": 5,
        "nation": "Spain",
        "location": "Paris",
        "tiredUntil": 0,
        "active": True
    })

    assert groundBombardment(gameData, [bomber], [infantry], True) == {infantry: 2}
    assert infantry.quantity == 5

def test_naval_cooldown_uses_naval_data():
    class NavalGameData(FakeGameData):
        def getMapName(self):
            return "Test Map"

    gameData = NavalGameData({
        "Naval": {"Destroyer": {"Short Form": "DD", "Cooldown": 12}}
    })

    assert findCooldown(gameData, "Destroyer", 0, 1) == 48

def test_aircraft_interception_skips_unreachable_path(monkeypatch):
    territory = Territory({
        "name": "Paris",
        "location": [0, 0],
        "bordering": [],
        "nation": "France",
        "population": 0,
        "buildings": ["Airstrip"],
        "coast": [],
        "integrated": 0,
        "area": 0,
        "terrain": 0,
        "rails": [],
        "resources": {},
        "devastation": 0
    })

    class InterceptionGameData:
        def getTerritory(self, name):
            if name != territory.name:
                raise ValueError(name)
            return territory

        def getSea(self, name):
            raise ValueError(name)

        def getUnit(self, name):
            return None

        def getUnits(self):
            return []

    plane = Unit({
        "name": "FI-1",
        "type": "Fighter",
        "quantity": 1,
        "nation": "France",
        "location": territory.name,
        "tiredUntil": 0,
        "active": True
    })

    monkeypatch.setattr("api.game_logic.military.attack.shortestPathFinder", lambda *args, **kwargs: None)

    result = aircraftInterception(InterceptionGameData(), None, [plane], territory, False)

    assert result is not None
    assert result.flownOver == set()

def test_in_range_uses_active_map_data():
    source = Territory({
        "name": "Source",
        "location": [[0, 0]],
        "bordering": [],
        "nation": "France",
        "population": 0,
        "buildings": ["Airstrip"],
        "coast": [],
        "integrated": 0,
        "area": 0,
        "terrain": 0,
        "rails": [],
        "resources": {},
        "devastation": 0
    })
    target = Territory({
        "name": "Target",
        "location": [[3, 4]],
        "bordering": [],
        "nation": "Spain",
        "population": 0,
        "buildings": [],
        "coast": [],
        "integrated": 0,
        "area": 0,
        "terrain": 0,
        "rails": [],
        "resources": {},
        "devastation": 0
    })

    class RangeGameData:
        def getDefaultGameData(self):
            return {"Units": {"Air": {"Fighter": {"Short Form": "FI", "Range": 10}}}}

        def getTerritory(self, name):
            if name == source.name:
                return source
            raise ValueError(name)

        def getSea(self, name):
            raise ValueError(name)

        def getUnit(self, name):
            return None

        def getUnits(self):
            return []

        def getMapName(self):
            return "Test Map"

        def getMapData(self, mapName):
            assert mapName == "Test Map"
            return {"pxToKm": 1}

    plane = Unit({
        "name": "FI-1",
        "type": "Fighter",
        "quantity": 1,
        "nation": "France",
        "location": source.name,
        "tiredUntil": 0,
        "active": True
    })

    assert inRange(RangeGameData(), plane, target, roundTrip=False)