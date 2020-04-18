import mock
import os
import pytest
from mtg_draft_ai.brains import SynergyPowerFixingPicker
from mtg_draft_ai.api import *
from .. import TEST_DATA_DIR


# Cards:
# Abzan Battle Priest, Ajani's Pridemate, Lightning Helix, "Ayli, Eternal Pilgrim",
# Tuskguard Captain, Swift Justice
CUBE_LIST_PATH = os.path.join(TEST_DATA_DIR, 'test_picker.toml')
FIXER_DATA_PATH = os.path.join(TEST_DATA_DIR, 'fixer_data.toml')

CUBE_LIST = read_cube_toml(CUBE_LIST_PATH, FIXER_DATA_PATH)
CARDS_BY_NAME = {c.name: c for c in CUBE_LIST}


@pytest.fixture
def draft_info():
    return mock.Mock(name='draft_info')


@pytest.fixture
def picker():
    return SynergyPowerFixingPicker.factory(CUBE_LIST).create()


def test_pick(draft_info, picker):
    owned_cards = _cards(['Abzan Battle Priest', "Ajani's Pridemate"])
    pack = _cards(['Ayli, Eternal Pilgrim', 'Tuskguard Captain'])

    pick = picker.pick(pack, owned_cards, draft_info)
    assert pick == CARDS_BY_NAME['Ayli, Eternal Pilgrim']


def test_fixer_land_pick(draft_info, picker):
    owned_cards = _cards(['Abzan Battle Priest', "Ajani's Pridemate", 'Ayli, Eternal Pilgrim'])
    pack = _cards(['Tuskguard Captain', 'Woodland Cemetery', 'Caves of Koilos'])

    pick = picker.pick(pack, owned_cards, draft_info)
    assert pick == CARDS_BY_NAME['Caves of Koilos']


def _cards(card_names):
    return [CARDS_BY_NAME[n] for n in card_names]
