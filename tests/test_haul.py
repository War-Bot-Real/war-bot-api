import pytest

from api.game_logic.military.movement import executeHaul
from military_test_support import InMemoryGameData, make_nation, make_territory, make_unit

def build_haul_game(
    *,
    trusted=(),
    coal=10,
    source_buildings=("Railway Station",),
    destination_buildings=("Railway Station",),
    rails=True,
    middle_nation="France",
    destination_nation="France"
):
    source = make_territory(
        "Paris",
        "France",
        location=(0, 0),
        buildings=source_buildings,
        rails=["Lyon"] if rails else [],
        terrain=1
    )
    middle = make_territory(
        "Lyon",
        middle_nation,
        location=(10, 0),
        rails=["Marseille"] if rails else [],
        terrain=1
    )
    destination = make_territory(
        "Marseille",
        destination_nation,
        location=(20, 0),
        buildings=destination_buildings,
        terrain=1
    )
    unit = make_unit("IN-1", "Infantry", "France", source.name)
    nation = make_nation("France", trusted=trusted, inventory={"Coal": coal})
    nations = [nation]
    if "Spain" in {middle_nation, destination_nation}:
        nations.append(make_nation("Spain"))

    game_data = InMemoryGameData(
        territories=[source, middle, destination],
        nations=nations,
        units=[unit]
    )
    return game_data, nation, unit, destination


def test_haul_succeeds_to_own_territory_over_indirect_rail_and_consumes_coal():
    game_data, nation, unit, destination = build_haul_game()

    result = executeHaul(game_data, nation, unit, destination)

    assert result["destination"] == "Marseille"
    assert result["coal_cost"] == 1
    assert unit.location == "Marseille"
    assert game_data.memory_supabase.tables["nations"][0]["inventory"]["Coal"] == 9
    assert any(
        table == "units" and operation == "update"
        for table, operation, *_rest in game_data.memory_supabase.writes
    )


def test_haul_succeeds_through_trusted_territory():
    game_data, nation, unit, destination = build_haul_game(
        trusted=["Spain"],
        middle_nation="Spain"
    )

    result = executeHaul(game_data, nation, unit, destination)

    assert result["destination"] == "Marseille"


def test_haul_succeeds_to_trusted_nation_territory():
    source = make_territory(
        "Paris", "France", buildings=["Railway Station"],
        rails=["Madrid"], terrain=1
    )
    destination = make_territory(
        "Madrid", "Spain", buildings=["Railway Station"], terrain=1
    )
    nation = make_nation("France", trusted=["Spain"], inventory={"Coal": 10})
    unit = make_unit("IN-1", "Infantry", "France", source.name)
    game_data = InMemoryGameData(
        territories=[source, destination],
        nations=[nation, make_nation("Spain")],
        units=[unit]
    )

    result = executeHaul(game_data, nation, unit, destination)

    assert result["destination"] == "Madrid"


def test_haul_cannot_reach_untrusted_territory():
    source = make_territory(
        "Paris", "France", buildings=["Railway Station"],
        rails=["Madrid"], terrain=1
    )
    destination = make_territory(
        "Madrid", "Spain", buildings=["Railway Station"], terrain=1
    )
    nation = make_nation("France", inventory={"Coal": 10})
    unit = make_unit("IN-1", "Infantry", "France", source.name)
    game_data = InMemoryGameData(
        territories=[source, destination],
        nations=[nation, make_nation("Spain")],
        units=[unit]
    )

    with pytest.raises(ValueError, match="No valid rail connects"):
        executeHaul(game_data, nation, unit, destination)

    assert game_data.memory_supabase.writes == []


def test_haul_cannot_route_through_untrusted_territory():
    game_data, nation, unit, destination = build_haul_game(
        middle_nation="Spain"
    )

    with pytest.raises(ValueError, match="No valid rail connects"):
        executeHaul(game_data, nation, unit, destination)

    assert game_data.memory_supabase.writes == []


def test_haul_requires_enough_coal():
    game_data, nation, unit, destination = build_haul_game(coal=0.5)

    with pytest.raises(ValueError, match="more coal required"):
        executeHaul(game_data, nation, unit, destination)

    assert unit.location == "Paris"
    assert game_data.memory_supabase.writes == []


@pytest.mark.parametrize("missing_station", ["source", "destination"])
def test_haul_requires_stations_at_both_ends(missing_station):
    source_buildings = (
        () if missing_station == "source" else ("Railway Station",)
    )
    destination_buildings = (
        () if missing_station == "destination" else ("Railway Station",)
    )
    game_data, nation, unit, destination = build_haul_game(
        source_buildings=source_buildings,
        destination_buildings=destination_buildings
    )

    with pytest.raises(ValueError, match="does not have a railway station"):
        executeHaul(game_data, nation, unit, destination)

    assert game_data.memory_supabase.writes == []


def test_haul_requires_a_rail_connection():
    game_data, nation, unit, destination = build_haul_game(rails=False)

    with pytest.raises(ValueError, match="No valid rail connects"):
        executeHaul(game_data, nation, unit, destination)

    assert game_data.memory_supabase.writes == []
