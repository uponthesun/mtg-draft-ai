import mock
import os
import pytest
from mtg_draft_ai.brains import GreedySynergyPicker, all_common_neighbors
from mtg_draft_ai.api import *
from mtg_draft_ai import synergy


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# Cards:
# Abzan Battle Priest, Ajani's Pridemate, Lightning Helix, "Ayli, Eternal Pilgrim",
# Tuskguard Captain, Swift Justice
@pytest.fixture
def cards():
    file_path = os.path.join(TEST_DATA_DIR, 'test_greedy_synergy_picker_cards.toml')
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


def test_all_common_neighbors_coverage(graph, cards):
    common = all_common_neighbors(graph, cards)

    for c1 in cards:
        for c2 in cards:
            if c1 != c2:
                assert common[c1][c2] == common[c2][c1]


def test_common_neighbors_found(graph, cards, cards_by_name):
    common = all_common_neighbors(graph, cards)

    c1 = cards_by_name['Abzan Battle Priest']
    c2 = cards_by_name["Lightning Helix"]

    expected_neighbor_names = ["Ajani's Pridemate", "Ayli, Eternal Pilgrim"]

    assert set(common[c1][c2]) == {cards_by_name[n] for n in expected_neighbor_names}


def test_greedy_synergy_picker(cards, cards_by_name, draft_info):
    picker = GreedySynergyPicker.factory(cards).create()
    owned_card_names = ['Abzan Battle Priest', "Ajani's Pridemate"]
    pack_card_names = ['Ayli, Eternal Pilgrim', 'Tuskguard Captain']
    owned_cards = [cards_by_name[n] for n in owned_card_names]
    pack = [cards_by_name[n] for n in pack_card_names]

    ratings = picker._ratings(pack=pack, cards_owned=owned_cards, draft_info=draft_info)

    # Ayli in WB only, Tuskguard Captain in GW/GU/GR/GB
    assert len(ratings) == 5

    top_ranked = ratings[0]
    assert top_ranked.card == cards_by_name['Ayli, Eternal Pilgrim']
    # Expected:
    # total edges: priest/pridemate/ayli all connected
    # common neighbors (not already in pool): swift justice
    assert top_ranked[1:] == ('WB', 3, 1, picker.default_ratings[top_ranked.card])
