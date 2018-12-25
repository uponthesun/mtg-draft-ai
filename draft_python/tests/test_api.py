import mock
import pytest
from mtg_draft_ai.api import Drafter, Packs, DraftInfo


PICKED_CARD = 1


@pytest.fixture
def draft_info():
    return DraftInfo(card_list=list(range(0, 100)), cards_per_pack=5, num_phases=3, num_drafters=4)


@pytest.fixture
def picker():
    picker = mock.Mock(name='picker')
    picker.pick.return_value = 1
    return picker


def test_drafter_pick(draft_info, picker):
    drafter = Drafter(picker)
    picked = drafter.pick([1, 2, 3])

    assert picked == PICKED_CARD
    assert drafter.cards_owned == [PICKED_CARD]
    picker.pick.assert_called_with(pack=[1, 2, 3], cards_owned=[])


def test_picker_invalid_pick(draft_info, picker):
    with pytest.raises(ValueError):
        picker.pick.return_value = 'Ace of Spades'
        drafter = Drafter(picker)
        drafter.pick(pack=[1, 2, 3])


def test_packs_get():
    packs = Packs(pack_contents=[[[1, 2, 3], [4, 5, 6]],
                                 [[7, 8, 9], [10, 11, 12]]])
    assert packs.get(phase=0, starting_seat=1) == [4, 5, 6]
