import os
import pytest
from mtg_draft_ai.brains import all_common_neighbors
from mtg_draft_ai.api import *
from .. import TEST_DATA_DIR


# Cards:
# Abzan Battle Priest, Ajani's Pridemate, Lightning Helix, "Ayli, Eternal Pilgrim",
# Tuskguard Captain, Swift Justice
@pytest.fixture
def cards():
    file_path = os.path.join(TEST_DATA_DIR, 'test_common_neighbors.toml')
    return read_cube_toml(file_path)


@pytest.fixture
def cards_by_name(cards):
    return {c.name: c for c in cards}


def test_all_common_neighbors_coverage(cards):
    common = all_common_neighbors(cards)

    for c1 in cards:
        for c2 in cards:
            if c1 != c2:
                assert common[c1][c2] == common[c2][c1]


def test_common_neighbors_found(cards, cards_by_name):
    common = all_common_neighbors(cards)

    c1 = cards_by_name['Abzan Battle Priest']
    c2 = cards_by_name["Lightning Helix"]

    expected_neighbor_names = ["Ajani's Pridemate", "Ayli, Eternal Pilgrim"]

    assert set(common[c1][c2]) == {cards_by_name[n] for n in expected_neighbor_names}
