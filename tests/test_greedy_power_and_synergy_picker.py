import mock
import os
import pytest
from mtg_draft_ai.brains import GreedyPowerAndSynergyPicker, _CombinedRating
from mtg_draft_ai.api import *


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


# Cards:
# Abzan Battle Priest, Ajani's Pridemate, Lightning Helix, "Ayli, Eternal Pilgrim",
# Tuskguard Captain, Swift Justice
CUBE_LIST_PATH = os.path.join(TEST_DATA_DIR, 'test_greedy_power_and_synergy_picker_cards.toml')
FIXER_DATA_PATH = os.path.join(TEST_DATA_DIR, 'fixer_data.toml')

CUBE_LIST = read_cube_toml(CUBE_LIST_PATH, FIXER_DATA_PATH)
CARDS_BY_NAME = {c.name: c for c in CUBE_LIST}


@pytest.fixture
def draft_info():
    return mock.Mock(name='draft_info')


@pytest.fixture
def picker():
    return GreedyPowerAndSynergyPicker.factory(CUBE_LIST).create()


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


def test_pick(draft_info, picker):
    owned_cards = _cards(['Abzan Battle Priest', "Ajani's Pridemate"])
    pack = _cards(['Ayli, Eternal Pilgrim', 'Tuskguard Captain', 'Caves of Koilos'])

    pick = picker.pick(pack, owned_cards, draft_info)
    assert pick == CARDS_BY_NAME['Ayli, Eternal Pilgrim']


def test_fixer_land_pick(draft_info, picker):
    owned_cards = _cards(['Abzan Battle Priest', "Ajani's Pridemate", 'Ayli, Eternal Pilgrim', 'Swift Justice',
                          'Angel of Vitality'])
    pack = _cards(['Tuskguard Captain', 'Caves of Koilos', 'Woodland Cemetery'])

    pick = picker.pick(pack, owned_cards, draft_info)
    assert pick == CARDS_BY_NAME['Caves of Koilos']


def _cards(card_names):
    return [CARDS_BY_NAME[n] for n in card_names]
