import pytest

from api.game_logic.income import (
    calcRevByTerr,
    collectIncome,
    collectResources,
    getResourceFlow
)
from military_test_support import InMemoryGameData, make_nation, make_territory


TAX_COOLDOWN = 30 * 60


def build_income_game(*, current_time, last_tax=None):
    territory = make_territory("Paris", "France")
    territory.pop = 1000
    territory.resources = {"Coal": 4, "Iron": 2}
    nation = make_nation("France", inventory={"Coal": 3, "Iron": 1})
    nation.tax_rate = 50
    nation.stability = 70
    nation.last = {} if last_tax is None else {"tax": last_tax}
    game_data = InMemoryGameData(territories=[territory], nations=[nation])
    game_data.gameTime = lambda: current_time
    return game_data, nation


def test_cannot_collect_before_30_minutes():
    current_time = 100_000
    game_data, nation = build_income_game(
        current_time=current_time,
        last_tax=current_time - TAX_COOLDOWN + 1
    )

    with pytest.raises(ValueError, match="Can't collect yet"):
        collectIncome(game_data, nation)

    assert game_data.memory_supabase.writes == []


def test_can_collect_after_30_minutes():
    current_time = 100_000
    game_data, nation = build_income_game(
        current_time=current_time,
        last_tax=current_time - TAX_COOLDOWN - 1
    )

    result = collectIncome(game_data, nation)

    assert result["Collected Until"] - result["Collected From"] == TAX_COOLDOWN + 1
    assert game_data.memory_supabase.tables["nations"][0]["last"]["tax"] == current_time


def test_zero_last_tax_collects_only_one_period():
    current_time = 100_000
    game_data, nation = build_income_game(
        current_time=current_time,
        last_tax=0
    )

    result = collectIncome(game_data, nation)

    assert result["Collected From"] == current_time - TAX_COOLDOWN
    assert result["Collected Until"] == current_time
    assert result["Income"] == sum(calcRevByTerr(game_data, nation).values())


def test_collected_resources_match_resflow_for_one_period():
    current_time = 100_000
    game_data, nation = build_income_game(
        current_time=current_time,
        last_tax=current_time - TAX_COOLDOWN
    )
    expected_resources = collectResources(game_data, nation, TAX_COOLDOWN)

    result = collectIncome(game_data, nation)

    assert result["Resources"] == {
        resource: round(amount, 2)
        for resource, amount in expected_resources.items()
        if amount != 0
    }
    assert {
        resource: round(amount, 2)
        for resource, amount in getResourceFlow(game_data, nation).items()
    } == {
        resource: round(amount, 2)
        for resource, amount in expected_resources.items()
    }


def test_collected_income_matches_view_income_for_one_period():
    current_time = 100_000
    game_data, nation = build_income_game(
        current_time=current_time,
        last_tax=current_time - TAX_COOLDOWN
    )
    view_income = calcRevByTerr(game_data, nation)

    result = collectIncome(game_data, nation)

    assert result["Income"] == sum(view_income.values())
