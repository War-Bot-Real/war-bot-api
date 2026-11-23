import pytest

from api.game_logic.military.management import deployUnit
from tests.military_test_support import (
    InMemoryGameData,
    make_nation,
    make_sea,
    make_territory,
)


def build_deploy_game(*, territory=None, sea=None, nation_name="France"):
    nation = make_nation(
        nation_name,
        inventory={"Infantry": 10, "Destroyer": 10, "Fighter": 10}
    )
    game_data = InMemoryGameData(
        territories=[territory] if territory is not None else [],
        seas=[sea] if sea is not None else [],
        nations=[nation]
    )
    return game_data, nation


def test_ground_unit_deploys_on_integrated_owned_territory():
    territory = make_territory("Paris", "France")
    game_data, nation = build_deploy_game(territory=territory)

    result = deployUnit(game_data, nation, territory, "Infantry", 2)

    assert result["location"] == "Paris"
    assert result["quantity"] == 2


@pytest.mark.parametrize("owner", ["Spain", "Germany"])
def test_ground_unit_cannot_deploy_on_unowned_territory(owner):
    territory = make_territory("Madrid", owner)
    game_data, nation = build_deploy_game(territory=territory)

    with pytest.raises(ValueError, match="is owned by"):
        deployUnit(game_data, nation, territory, "Infantry", 1)


def test_ground_unit_cannot_deploy_on_trusted_territory():
    territory = make_territory("Madrid", "Spain")
    nation = make_nation("France", trusted=("Spain",), inventory={"Infantry": 10})
    game_data = InMemoryGameData(territories=[territory], nations=[nation])

    with pytest.raises(ValueError, match="is owned by Spain"):
        deployUnit(game_data, nation, territory, "Infantry", 1)


def test_ground_unit_cannot_deploy_on_unintegrated_owned_territory():
    territory = make_territory("Paris", "France", integrated=200)
    game_data, nation = build_deploy_game(territory=territory)

    with pytest.raises(ValueError, match="has not been integrated"):
        deployUnit(game_data, nation, territory, "Infantry", 1)


def test_naval_unit_deploys_on_integrated_owned_coastal_territory():
    territory = make_territory("Le Havre", "France", coast=("English Channel",))
    game_data, nation = build_deploy_game(territory=territory)

    result = deployUnit(game_data, nation, territory, "Destroyer", 1)

    assert result["location"] == "Le Havre"


def test_naval_unit_cannot_deploy_on_owned_landlocked_territory():
    territory = make_territory("Paris", "France")
    game_data, nation = build_deploy_game(territory=territory)

    with pytest.raises(ValueError, match="landlocked"):
        deployUnit(game_data, nation, territory, "Destroyer", 1)


def test_naval_unit_cannot_deploy_in_sea():
    sea = make_sea("English Channel")
    game_data, nation = build_deploy_game(sea=sea)

    with pytest.raises(ValueError, match="only be deployed on territories"):
        deployUnit(game_data, nation, sea, "Destroyer", 1)


def test_naval_unit_cannot_deploy_on_foreign_coastal_territory():
    territory = make_territory("Le Havre", "Spain", coast=("English Channel",))
    game_data, nation = build_deploy_game(territory=territory)

    with pytest.raises(ValueError, match="is owned by Spain"):
        deployUnit(game_data, nation, territory, "Destroyer", 1)


def test_naval_unit_cannot_deploy_on_unintegrated_coastal_territory():
    territory = make_territory(
        "Le Havre", "France", coast=("English Channel",), integrated=200
    )
    game_data, nation = build_deploy_game(territory=territory)

    with pytest.raises(ValueError, match="has not been integrated"):
        deployUnit(game_data, nation, territory, "Destroyer", 1)


def test_air_unit_deploys_on_integrated_owned_territory_with_airport():
    territory = make_territory("Paris", "France", buildings=("Airport",))
    game_data, nation = build_deploy_game(territory=territory)

    result = deployUnit(game_data, nation, territory, "Fighter", 1)

    assert result["location"] == "Paris"


def test_air_unit_cannot_deploy_on_foreign_territory_with_airport():
    territory = make_territory("Madrid", "Spain", buildings=("Airport",))
    game_data, nation = build_deploy_game(territory=territory)

    with pytest.raises(ValueError, match="is owned by Spain"):
        deployUnit(game_data, nation, territory, "Fighter", 1)


def test_air_unit_cannot_deploy_on_owned_territory_without_airport():
    territory = make_territory("Paris", "France")
    game_data, nation = build_deploy_game(territory=territory)

    with pytest.raises(ValueError, match="must have an airport"):
        deployUnit(game_data, nation, territory, "Fighter", 1)


def test_air_unit_cannot_deploy_on_unintegrated_owned_territory():
    territory = make_territory(
        "Paris", "France", buildings=("Airport",), integrated=200
    )
    game_data, nation = build_deploy_game(territory=territory)

    with pytest.raises(ValueError, match="has not been integrated"):
        deployUnit(game_data, nation, territory, "Fighter", 1)
