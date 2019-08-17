import mock
import os
import pytest
from mtg_draft_ai.brains import GreedyPowerAndSynergyPicker, _CombinedRating
from mtg_draft_ai.api import *
from mtg_draft_ai import synergy


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


# Cards:
# Abzan Battle Priest, Ajani's Pridemate, Lightning Helix, "Ayli, Eternal Pilgrim",
# Tuskguard Captain, Swift Justice
@pytest.fixture
def cards():
    file_path = os.path.join(TEST_DATA_DIR, 'test_greedy_power_and_synergy_picker_cards.toml')
    return read_cube_toml(file_path)


@pytest.fixture
def cards_by_name(cards):
    return {c.name: c for c in cards}


@pytest.fixture
def graph(cards):
    return synergy.create_graph(cards)


@pytest.fixture
def draft_info():
    return mock.Mock(name='draft_info')


def test_normalize_ratings():
    cards_owned = [None] * 10

    raw_ratings = [
        _CombinedRating('card1', 'W', None, power_delta=0.8, total_power=10, edges_delta=5,
                        total_edges=50, common_neighbors_weighted=10),
        _CombinedRating('card2', 'U', None, 0.6, 8, 4, 40, 8),
        _CombinedRating('card3', 'B', None, 0.3, 6, 3, 30, 6),
    ]

    expected = [
        _CombinedRating('card1', 'W', None, 0.8, 1.0, 0.5, 1.0, 1.0),
        _CombinedRating('card2', 'U', None, 0.6, 0.8, 0.4, 0.8, 0.8),
        _CombinedRating('card3', 'B', None, 0.3, 0.6, 0.3, 0.6, 0.6),
    ]

    normalized_ratings = GreedyPowerAndSynergyPicker._normalize_ratings(raw_ratings, cards_owned)
    assert normalized_ratings == expected


def test_composite_ratings():
    normalized_ratings = [
        _CombinedRating('card1', 'W', rating=None, power_delta=1.0, total_power=1.0, edges_delta=1.0,
                        total_edges=1.0, common_neighbors_weighted=1.0),
        _CombinedRating('card2', 'U', None, 0.0, 0.2, 0.3, 0.4, 0.5),
    ]

    expected = [
        _CombinedRating('card1', 'W', rating=1.0, power_delta=1.0, total_power=1.0, edges_delta=1.0,
                        total_edges=1.0, common_neighbors_weighted=1.0),
        # Expected: power rating = 0.1 and synergy rating = 0.4 -> composite = 0.25
        _CombinedRating('card2', 'U', 0.25, 0.0, 0.2, 0.3, 0.4, 0.5),
    ]

    composite_ratings = GreedyPowerAndSynergyPicker._composite_ratings(normalized_ratings)
    assert composite_ratings == expected


def test_greedy_power_and_synergy_picker(cards, cards_by_name, draft_info):
    picker = GreedyPowerAndSynergyPicker.factory(cards).create()
    owned_card_names = ['Abzan Battle Priest', "Ajani's Pridemate"]
    pack_card_names = ['Ayli, Eternal Pilgrim', 'Tuskguard Captain']
    owned_cards = [cards_by_name[n] for n in owned_card_names]
    pack = [cards_by_name[n] for n in pack_card_names]

    pick = picker.pick(pack, owned_cards, draft_info)
    assert pick == cards_by_name['Ayli, Eternal Pilgrim']

