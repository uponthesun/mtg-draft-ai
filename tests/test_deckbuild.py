import os
import pytest
import mock
from mtg_draft_ai import deckbuild, synergy
from mtg_draft_ai.controller import read_cube_toml


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


@pytest.fixture
def cards_by_name():
    cube_list = read_cube_toml(os.path.join(TEST_DATA_DIR, 'cube_81183_tag_data.toml'))
    return {c.name: c for c in cube_list}


@pytest.fixture
def pool(cards_by_name):
    pool = ['Adeliz, the Cinder Wind', 'Harvest Pyre', 'Bloodrage Brawler', 'Cathartic Reunion', 'Thing in the Ice',
            'Riddleform', 'Goblin Welder', 'Karn, Silver Golem', 'Cinder Barrens', 'Negate', 'Akroan Crusader',
            'Bound by Moonsilver', 'Crawling Sensation', 'Anax and Cymede', 'Killing Glare', 'Thresher Lizard',
            'Orzhov Signet', 'Temur Battle Rage', "Cultivator's Caravan", 'Magus of the Scroll', 'Blighted Gorge',
            'Temple of Epiphany', 'Embodiment of Fury', 'Goblin Instigator', 'Cloudfin Raptor', 'Temple of Abandon',
            'Rootbound Crag', 'Omnath, Locus of Rage', 'Dragonskull Summit', 'Viridian Zealot', 'Fall of the Titans',
            'Bedlam Reveler', 'Izzet Chemister', 'Magus of the Wheel', "Wizard's Lightning", 'Dissolve',
            'Countryside Crusher', "Fortune's Favor", 'Ogre Battledriver', 'Dismissive Pyromancer', 'Tilling Treefolk',
            'Timber Gorge', 'Oppressive Rays', 'Oracle of Mul Daya', 'Skarrg Guildmage']
    return [cards_by_name[name] for name in pool]


# Does a deckbuild of a UR pool. Asserts that the right number of cards are in resulting deck, and that they are all on-color.
def test_deckbuild(pool):
    deck = deckbuild.best_two_color_synergy_build(pool)

    assert len(deck) == deckbuild._NONLANDS_IN_DECK

    ur_cards_in_deck = [c for c in deck if synergy.castable(c, 'UR')]
    assert deck == ur_cards_in_deck

# Asserts that build_fn is called once for each color combination.
def test_deckbuild_each_color_pair_tried(pool):
    build_fn = mock.MagicMock('build_fn')
    deckbuild.best_two_color_synergy_build(pool, build_fn=build_fn)

    assert build_fn.call_count == 10
