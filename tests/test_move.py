import pytest

from api.game_logic.military import movement
from military_test_support import (
    InMemoryGameData,
    make_nation,
    make_sea,
    make_territory,
    make_unit
)


@pytest.fixture
def deterministic_movement_costs(monkeypatch):
    monkeypatch.setattr(movement, "findFuelRequired", lambda *args, **kwargs: 2)
    monkeypatch.setattr(movement, "findCooldown", lambda *args, **kwargs: 10)
    monkeypatch.setattr(movement, "planeFuelReq", lambda *args, **kwargs: 2)
    monkeypatch.setattr(movement, "planeCooldown", lambda *args, **kwargs: 10)
    monkeypatch.setattr(movement, "aircraftInterception", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        movement,
        "shortestPathFinder",
        lambda _game_data, start, destination, **kwargs: [start, destination]
    )


def assert_unit_persisted(game_data, unit, destination):
    row = next(
        row for row in game_data.memory_supabase.tables["units"]
        if row["name"] == unit.name
    )
    assert row["location"] == destination
    assert row["tiredUntil"] == 110
    nation_row = next(
        row for row in game_data.memory_supabase.tables["nations"]
        if row["name"] == unit.nation
    )
    assert nation_row["inventory"]["Fuel"] == 98
    assert any(
        table == "units" and operation == "update"
        for table, operation, *_rest in game_data.memory_supabase.writes
    )


def test_ground_units_can_move_to_owned_territory_and_persist(
    deterministic_movement_costs
):
    nation = make_nation("France")
    origin = make_territory("Paris", "France")
    destination = make_territory("Lyon", "France", bordering=["Paris"])
    unit = make_unit("IN-1", "Infantry", "France", "Paris")
    game_data = InMemoryGameData(
        territories=[origin, destination],
        nations=[nation],
        units=[unit]
    )

    result = movement.move(game_data, nation, [unit], "Lyon")

    assert result["success"] is True
    assert_unit_persisted(game_data, unit, "Lyon")


def test_ground_units_can_move_to_territory_owned_by_trusted_nation_and_persist(
    deterministic_movement_costs
):
    nation = make_nation("France", trusted=["Spain"])
    origin = make_territory("Paris", "France")
    destination = make_territory("Madrid", "Spain", bordering=["Paris"])
    unit = make_unit("IN-1", "Infantry", "France", "Paris")
    game_data = InMemoryGameData(
        territories=[origin, destination],
        nations=[nation, make_nation("Spain")],
        units=[unit]
    )

    result = movement.move(game_data, nation, [unit], "Madrid")

    assert result["success"] is True
    assert_unit_persisted(game_data, unit, "Madrid")


def test_naval_units_can_move_to_coastal_territory_and_persist(
    deterministic_movement_costs
):
    nation = make_nation("France")
    destination = make_territory(
        "Brest", "France", coast=["Bay of Biscay"]
    )
    source_sea = make_sea("Bay of Biscay", bordering=["Brest"])
    unit = make_unit("DE-1", "Destroyer", "France", "Bay of Biscay")
    game_data = InMemoryGameData(
        territories=[destination],
        seas=[source_sea],
        nations=[nation],
        units=[unit]
    )

    result = movement.move(game_data, nation, [unit], "Brest")

    assert result["success"] is True
    assert_unit_persisted(game_data, unit, "Brest")


def test_naval_units_cannot_move_to_landlocked_territory(
    deterministic_movement_costs
):
    nation = make_nation("France")
    destination = make_territory(
        "Lyon", "France", bordering=["Dijon"], coast=[]
    )
    source_sea = make_sea("Bay of Biscay", bordering=["Brest"])
    unit = make_unit("DE-1", "Destroyer", "France", "Bay of Biscay")
    game_data = InMemoryGameData(
        territories=[destination],
        seas=[source_sea],
        nations=[nation],
        units=[unit]
    )

    with pytest.raises(ValueError, match="does not border"):
        movement.move(game_data, nation, [unit], "Lyon")

    assert game_data.memory_supabase.writes == []


def test_naval_units_can_move_to_sea_and_persist(deterministic_movement_costs):
    nation = make_nation("France")
    source_sea = make_sea("Bay of Biscay", bordering=["English Channel"])
    destination_sea = make_sea(
        "English Channel", bordering=["Bay of Biscay"]
    )
    unit = make_unit("DE-1", "Destroyer", "France", "Bay of Biscay")
    game_data = InMemoryGameData(
        seas=[source_sea, destination_sea],
        nations=[nation],
        units=[unit]
    )

    result = movement.move(game_data, nation, [unit], "English Channel")

    assert result["success"] is True
    assert_unit_persisted(game_data, unit, "English Channel")


def test_planes_cannot_move_to_neighbor_without_airport(
    deterministic_movement_costs
):
    nation = make_nation("France")
    origin = make_territory(
        "Paris", "France", buildings=["Airport"]
    )
    destination = make_territory(
        "Lyon", "France", location=(10, 0), bordering=["Paris"]
    )
    plane = make_unit("FI-1", "Fighter", "France", "Paris")
    game_data = InMemoryGameData(
        territories=[origin, destination],
        nations=[nation],
        units=[plane]
    )

    with pytest.raises(ValueError, match="does not have an Airport or Airstrip"):
        movement.move(game_data, nation, [plane], "Lyon")

    assert game_data.memory_supabase.writes == []


def test_planes_cannot_move_to_owned_territory_out_of_range(
    deterministic_movement_costs
):
    nation = make_nation("France")
    origin = make_territory(
        "Paris", "France", buildings=["Airport"]
    )
    destination = make_territory(
        "Marseille", "France", location=(100, 0), buildings=["Airport"]
    )
    plane = make_unit("FI-1", "Fighter", "France", "Paris")
    game_data = InMemoryGameData(
        territories=[origin, destination],
        nations=[nation],
        units=[plane]
    )

    with pytest.raises(ValueError, match="not within range"):
        movement.move(game_data, nation, [plane], "Marseille")

    assert game_data.memory_supabase.writes == []


def test_planes_can_move_in_range_to_territory_with_airport_and_persist(
    deterministic_movement_costs
):
    nation = make_nation("France")
    origin = make_territory(
        "Paris", "France", buildings=["Airport"]
    )
    destination = make_territory(
        "Lyon", "France", location=(10, 0), buildings=["Airstrip"]
    )
    plane = make_unit("FI-1", "Fighter", "France", "Paris")
    game_data = InMemoryGameData(
        territories=[origin, destination],
        nations=[nation],
        units=[plane]
    )

    result = movement.move(game_data, nation, [plane], "Lyon")

    assert result["success"] is True
    assert_unit_persisted(game_data, plane, "Lyon")


def test_ground_units_cannot_move_to_non_neighboring_territory(
    deterministic_movement_costs
):
    nation = make_nation("France")
    origin = make_territory("Paris", "France")
    destination = make_territory("Marseille", "France", bordering=["Lyon"])
    unit = make_unit("IN-1", "Infantry", "France", "Paris")
    game_data = InMemoryGameData(
        territories=[origin, destination],
        nations=[nation],
        units=[unit]
    )

    with pytest.raises(ValueError, match="does not border"):
        movement.move(game_data, nation, [unit], "Marseille")

    assert game_data.memory_supabase.writes == []