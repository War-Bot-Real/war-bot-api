import pytest

from api.game_logic.military import attack
from military_test_support import (
    InMemoryGameData,
    make_nation,
    make_territory,
    make_unit
)


@pytest.fixture
def deterministic_air_battle(monkeypatch):
    monkeypatch.setattr(attack, "aircraftInterception", lambda *args, **kwargs: None)
    monkeypatch.setattr(attack, "fighterBattle", lambda *args, **kwargs: None)
    monkeypatch.setattr(attack, "navalAirRaid", lambda *args, **kwargs: set())
    monkeypatch.setattr(
        attack, "groundBasedAirDefense", lambda *args, **kwargs: set()
    )
    monkeypatch.setattr(attack, "groundBombardment", lambda *args, **kwargs: set())


def make_attack_scenario(at_war):
    attacker = make_nation("France")
    defender = make_nation("Spain")
    home = make_territory(
        "Paris", "France", buildings=["Airport"]
    )
    target = make_territory(
        "Madrid", "Spain", location=(10, 0), bordering=["Paris"]
    )
    plane = make_unit("FI-1", "Fighter", "France", "Paris")
    wars = [{
        "type": "war",
        "details": {"aggressors": ["France"], "defenders": ["Spain"]}
    }] if at_war else []
    game_data = InMemoryGameData(
        territories=[home, target],
        nations=[attacker, defender],
        units=[plane],
        wars=wars
    )
    return game_data, attacker, target, plane


def test_attack_rejects_territory_not_at_war_and_does_not_write(deterministic_air_battle):
    game_data, attacker, target, plane = make_attack_scenario(at_war=False)

    with pytest.raises(ValueError, match="not at war with Spain"):
        attack.attack(game_data, attacker, target, [plane])

    assert game_data.memory_supabase.writes == []


def test_attack_at_war_persists_unit_nation_and_battle_changes(deterministic_air_battle):
    game_data, attacker, target, plane = make_attack_scenario(at_war=True)

    result = attack.attack(game_data, attacker, target, [plane])

    unit_row = game_data.memory_supabase.tables["units"][0]
    nation_row = next(
        row for row in game_data.memory_supabase.tables["nations"]
        if row["name"] == "France"
    )
    assert result["battleId"]
    assert unit_row["tiredUntil"] > game_data.gameTime()
    assert nation_row["inventory"]["Fuel"] == 98
    assert attacker.inventory["Fuel"] == 98
    assert any(
        table == "units" and operation == "update"
        for table, operation, *_rest in game_data.memory_supabase.writes
    )
    assert any(
        table == "nations" and operation == "update"
        for table, operation, *_rest in game_data.memory_supabase.writes
    )
    assert len(game_data.memory_supabase.tables["battles"]) == 1