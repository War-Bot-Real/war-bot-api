import pytest
from api.game_logic.military.shared import getCapacity
from api.models import Unit

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