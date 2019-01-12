import os
import pytest
from mtg_draft_ai.controller import create_packs, read_cube_list, DraftController
from mtg_draft_ai.api import DraftInfo, Drafter, Packs, Card


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


@pytest.fixture
def draft_info():
    return DraftInfo(card_list=list(range(0, 100)),
                     cards_per_pack=5, num_phases=3, num_drafters=4)


def test_read_cube_list():
    file_path = os.path.join(TEST_DATA_DIR, 'test_cube_list.txt')
    assert read_cube_list(file_path) == [Card('Battle Hymn'), Card('Earthquake')]


def test_create_packs_dimensions(draft_info):
    pack_contents = create_packs(draft_info).pack_contents

    assert len(pack_contents) == draft_info.num_phases
    for phase_pack_set in pack_contents:
        assert len(phase_pack_set) == draft_info.num_drafters
        for pack in phase_pack_set:
            assert len(pack) == draft_info.cards_per_pack


def test_create_packs_uniqueness(draft_info):
    pack_contents = create_packs(draft_info).pack_contents
    unique_cards = set(_flatten_pack_contents(pack_contents))

    assert len(unique_cards) == draft_info.cards_per_pack * draft_info.num_drafters * draft_info.num_phases
    assert unique_cards.issubset(set(draft_info.card_list))


def test_create_packs_invalid_config(draft_info):
    with pytest.raises(ValueError):
        draft_info.num_drafters=1000
        create_packs(draft_info)


def test_controller_create(draft_info):
    drafters = [Drafter(FirstPicker()) for _ in range(0, 4)]
    controller = DraftController.create(draft_info=draft_info, drafters=drafters)
    assert controller.drafters == drafters
    assert len(controller.packs.pack_contents) == 3
    assert len(controller.packs.pack_contents[0]) == 4
    assert len(controller.packs.pack_contents[0][0]) == 5


def test_run_draft():
    pack_contents = [[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]],
                    [[13, 14, 15, 16], [17, 18, 19, 20], [21, 22, 23, 24]],
                    [[25, 26, 27, 28], [29, 30, 31, 32], [33, 34, 35, 36]]]
    drafters = [Drafter(FirstPicker()) for _ in range(0, 3)]
    draft_info = DraftInfo(card_list=list(range(1, 37)), cards_per_pack=4, num_phases=3, num_drafters=3)

    controller = DraftController(packs=Packs(pack_contents), drafters=drafters, draft_info=draft_info)
    controller.run_draft()

    assert drafters[0].cards_owned == [1, 6, 11, 4,
                                       13, 22, 19, 16,
                                       25, 30, 35, 28]
    all_picks = set(drafters[0].cards_owned + drafters[1].cards_owned + drafters[2].cards_owned)
    assert all_picks == set(range(1, 37))


class FirstPicker:
    def pick(self, pack, cards_owned):
        return pack[0]


def _flatten_pack_contents(pack_contents):
    flattened = []
    for phase_pack_set in pack_contents:
        for pack in phase_pack_set:
            for card in pack:
                flattened.append(card)

    return flattened
