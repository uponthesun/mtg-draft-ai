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
    return DraftInfo(card_list=None, num_drafters=6, num_phases=3, cards_per_pack=15)


def test_normalize_ratings():
    raw_ratings = [
        _CombinedRating('card1', 'W', None, power_delta=0.8, total_power=10, edges_delta=5,
                        total_edges=50, common_neighbors_weighted=10),
        _CombinedRating('card2', 'U', None, 0.6, 8, 4, 40, 8),
        _CombinedRating('card3', 'B', None, 0.3, 6, 3, 30, 6),
    ]

    expected = [
        _CombinedRating('card1', 'W', None, 1.0, 1.0, 1.0, 1.0, 1.0),
        _CombinedRating('card2', 'U', None, 0.75, 0.8, 0.8, 0.8, 0.8),
        _CombinedRating('card3', 'B', None, 0.375, 0.6, 0.6, 0.6, 0.6),
    ]

    normalized_ratings = GreedyPowerAndSynergyPicker._normalize_ratings(raw_ratings)
    assert normalized_ratings == expected


# power_delta, edges_delta, and common_neighbors_weighted are the "greedy" ratings, and
# total_power, total_edges are the "conservative" ratings. This test verifies that at the start
# of the draft, the greedy ratings are weighted 1 and the conservative ratings are rated 0.
def test_composite_ratings_start_of_draft(draft_info):
    owned_cards = []
    normalized_ratings = [
        _CombinedRating('card1', 'W', rating=None, power_delta=1.0, total_power=0.0, edges_delta=1.0,
                        total_edges=0.0, common_neighbors_weighted=1.0),
        _CombinedRating('card2', 'U', rating=None, power_delta=0.0, total_power=1.0, edges_delta=0.0,
                        total_edges=1.0, common_neighbors_weighted=0.0)
    ]

    expected = [
        _CombinedRating('card1', 'W', rating=1.0, power_delta=1.0, total_power=0.0, edges_delta=1.0,
                        total_edges=0.0, common_neighbors_weighted=1.0),
        _CombinedRating('card2', 'U', rating=0.0, power_delta=0.0, total_power=1.0, edges_delta=0.0,
                        total_edges=1.0, common_neighbors_weighted=0.0)
    ]

    composite_ratings = GreedyPowerAndSynergyPicker._composite_ratings(normalized_ratings, owned_cards, draft_info)
    assert composite_ratings == expected


# This test verifies that on the last meaningful pick of the draft, the greedy ratings are weighted 0
# and the conservative ratings are rated 1.
def test_composite_ratings_end_of_draft(draft_info):
    owned_cards = [None for _ in range(0, 43)]
    normalized_ratings = [
        _CombinedRating('card1', 'W', rating=None, power_delta=1.0, total_power=0.0, edges_delta=1.0,
                        total_edges=0.0, common_neighbors_weighted=1.0),
        _CombinedRating('card2', 'U', rating=None, power_delta=0.0, total_power=1.0, edges_delta=0.0,
                        total_edges=1.0, common_neighbors_weighted=0.0)
    ]

    expected = [
        _CombinedRating('card1', 'W', rating=0.0, power_delta=1.0, total_power=0.0, edges_delta=1.0,
                        total_edges=0.0, common_neighbors_weighted=1.0),
        _CombinedRating('card2', 'U', rating=1.0, power_delta=0.0, total_power=1.0, edges_delta=0.0,
                        total_edges=1.0, common_neighbors_weighted=0.0)
    ]

    composite_ratings = GreedyPowerAndSynergyPicker._composite_ratings(normalized_ratings, owned_cards, draft_info)
    assert composite_ratings == expected


def test_greedy_power_and_synergy_picker(cards, cards_by_name, draft_info):
    picker = GreedyPowerAndSynergyPicker.factory(cards).create()
    owned_card_names = ['Abzan Battle Priest', "Ajani's Pridemate"]
    pack_card_names = ['Ayli, Eternal Pilgrim', 'Tuskguard Captain']
    owned_cards = [cards_by_name[n] for n in owned_card_names]
    pack = [cards_by_name[n] for n in pack_card_names]

    pick = picker.pick(pack, owned_cards, draft_info)
    assert pick == cards_by_name['Ayli, Eternal Pilgrim']

