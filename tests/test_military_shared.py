import pytest
from api.game_logic.military.shared import canTakeoff, getCapacity
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