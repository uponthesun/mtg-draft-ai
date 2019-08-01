import mock
import pytest
from mtg_draft_ai.api import Drafter, Packs, DraftInfo, Picker, Card


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
    drafter = Drafter(picker, draft_info)
    picked = drafter.pick([1, 2, 3])

    assert picked == PICKED_CARD
    assert drafter.cards_owned == [PICKED_CARD]
    picker.pick.assert_called_with(pack=[1, 2, 3], cards_owned=[], draft_info=draft_info)


def test_picker_invalid_pick(draft_info, picker):
    with pytest.raises(ValueError) as excinfo:
        picker.pick.return_value = 'Ace of Spades'
        drafter = Drafter(picker, draft_info)
        drafter.pick(pack=[1, 2, 3])
    assert 'Drafter made invalid pick Ace of Spades' in str(excinfo.value)


def test_packs_get():
    packs = Packs(pack_contents=[[[1, 2, 3], [4, 5, 6]],
                                 [[7, 8, 9], [10, 11, 12]]])
    assert packs.get_pack(phase=0, starting_seat=1) == [4, 5, 6]


def test_invalid_picker():
    class InvalidPicker(Picker):
        pass

    with pytest.raises(TypeError):
        InvalidPicker()


def test_card_from_raw_data():
    name = 'Abhorrent Overlord'
    props = {
        'color_identity': 'B',
        'tags': ['Reanimator - Payoff', 'Big', 'Keyword', 'Tier 2', 'Ramp - Payoff'],
        'types': ['Creature'],
        'mana_cost': ["5", "B", "B"]
    }
    card = Card.from_raw_data(name, props)

    assert card.name == name
    assert card.color_id == 'B'
    assert card.power_tier == 2
    assert card.tags == [('Reanimator', 'Payoff'), ('Ramp', 'Payoff')]
    assert card.types == ['Creature']
