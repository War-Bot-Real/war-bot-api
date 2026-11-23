import pytest

from api.game_logic.buildings import (
    executeBuild,
    executeBulldoze,
    executeBulldozeTrack,
)
from tests.military_test_support import (
    InMemoryGameData,
    make_nation,
    make_territory,
)


def build_build_game(*, territory, nation_name="France"):
    nation = make_nation(nation_name, inventory={"Airport": 2})
    game_data = InMemoryGameData(
        territories=[territory],
        nations=[nation]
    )
    return game_data, nation


@pytest.mark.parametrize("integrated", [0, 200])
def test_build_succeeds_on_owned_territory_whether_integrated_or_not(integrated):
    territory = make_territory(
        "Paris", "France", integrated=integrated
    )
    game_data, nation = build_build_game(territory=territory)

    result = executeBuild(game_data, nation, territory, "Airport")

    assert result["building"] == "Airport"
    assert result["territory"] == "Paris"
    assert result["remaining"] == 1


def test_build_cannot_happen_on_foreign_territory():
    territory = make_territory("Madrid", "Spain")
    game_data, nation = build_build_game(territory=territory)

    with pytest.raises(ValueError, match="another nation's territory"):
        executeBuild(game_data, nation, territory, "Airport")


def test_build_cannot_happen_on_trusted_territory():
    territory = make_territory("Madrid", "Spain")
    nation = make_nation("France", trusted=("Spain",), inventory={"Airport": 2})
    game_data = InMemoryGameData(territories=[territory], nations=[nation])

    with pytest.raises(ValueError, match="another nation's territory"):
        executeBuild(game_data, nation, territory, "Airport")


@pytest.mark.parametrize("integrated", [0, 200])
def test_bulldoze_succeeds_on_owned_territory_whether_integrated_or_not(integrated):
    territory = make_territory(
        "Paris", "France", buildings=("Airport",), integrated=integrated
    )
    nation = make_nation("France", inventory={"Airport": 2})
    nation.balance = 100000
    game_data = InMemoryGameData(territories=[territory], nations=[nation])

    result = executeBulldoze(game_data, nation, territory, "Airport")

    assert result["building"] == "Airport"
    assert result["territory"] == "Paris"


@pytest.mark.parametrize("owner", ["Spain", "Germany"])
def test_bulldoze_cannot_happen_on_foreign_territory(owner):
    territory = make_territory(
        "Madrid", owner, buildings=("Airport",)
    )
    nation = make_nation("France", inventory={"Airport": 2})
    nation.balance = 100000
    game_data = InMemoryGameData(territories=[territory], nations=[nation])

    with pytest.raises(ValueError, match="don't own"):
        executeBulldoze(game_data, nation, territory, "Airport")


def test_bulldoze_cannot_happen_on_trusted_territory():
    territory = make_territory(
        "Madrid", "Spain", buildings=("Airport",)
    )
    nation = make_nation(
        "France", trusted=("Spain",), inventory={"Airport": 2}
    )
    nation.balance = 100000
    game_data = InMemoryGameData(territories=[territory], nations=[nation])

    with pytest.raises(ValueError, match="don't own"):
        executeBulldoze(game_data, nation, territory, "Airport")


@pytest.mark.parametrize(
    ("first_integrated", "second_integrated"),
    [(0, 0), (200, 200), (0, 200)]
)
def test_bulldoze_track_succeeds_between_owned_territories_regardless_of_integration(
    first_integrated,
    second_integrated
):
    terr1 = make_territory(
        "Paris", "France", rails=("Lyon",), integrated=first_integrated
    )
    terr2 = make_territory(
        "Lyon", "France", rails=("Paris",), integrated=second_integrated
    )
    nation = make_nation("France")
    nation.balance = 100000
    game_data = InMemoryGameData(
        territories=[terr1, terr2],
        nations=[nation]
    )

    result = executeBulldozeTrack(game_data, nation, terr1, terr2)

    assert result["territories"] == ["Paris", "Lyon"]


def test_bulldoze_track_cannot_use_foreign_destination():
    terr1 = make_territory("Paris", "France", rails=("Madrid",))
    terr2 = make_territory("Madrid", "Spain", rails=("Paris",))
    nation = make_nation("France")
    nation.balance = 100000
    game_data = InMemoryGameData(
        territories=[terr1, terr2],
        nations=[nation]
    )

    with pytest.raises(ValueError, match="territories that you own"):
        executeBulldozeTrack(game_data, nation, terr1, terr2)


def test_bulldoze_track_cannot_use_trusted_destination():
    terr1 = make_territory("Paris", "France", rails=("Madrid",))
    terr2 = make_territory("Madrid", "Spain", rails=("Paris",))
    nation = make_nation("France", trusted=("Spain",))
    nation.balance = 100000
    game_data = InMemoryGameData(
        territories=[terr1, terr2],
        nations=[nation]
    )

    with pytest.raises(ValueError, match="territories that you own"):
        executeBulldozeTrack(game_data, nation, terr1, terr2)
