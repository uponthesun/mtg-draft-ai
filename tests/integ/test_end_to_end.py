import contextlib
import itertools
import os

from mtg_draft_ai.controller import *
from mtg_draft_ai.api import *
from mtg_draft_ai.brains import *
from .. import TEST_DATA_DIR


CUBE_LIST_PATH = os.path.join(TEST_DATA_DIR, 'cube_81183_tag_data.toml')
FIXER_DATA_PATH = os.path.join(TEST_DATA_DIR, 'cube_81183_fixer_data.toml')

CUBE_LIST = read_cube_toml(CUBE_LIST_PATH, FIXER_DATA_PATH)


def test_full_draft():
    draft_info = DraftInfo(card_list=CUBE_LIST, num_drafters=6, num_phases=3, cards_per_pack=15)
    drafter_factory = SynergyPowerFixingPicker.factory(CUBE_LIST)
    drafters = [Drafter(drafter_factory.create(), draft_info) for _ in range(0, draft_info.num_drafters)]
    controller = DraftController.create(draft_info, drafters)
    original_cards_in_packs = _flatten_one_level(_flatten_one_level(controller.packs.pack_contents))

    # Reduce noise by redirecting stdout
    # TODO: Fix logging in draft controller so we don't have to redirect stdout
    with open(os.devnull, 'w') as f:
        with contextlib.redirect_stdout(f):
            controller.run_draft()

    combined_final_pools = _flatten_one_level([d.cards_owned for d in controller.drafters])
    # All cards in drafters' pools should be unique
    assert len(combined_final_pools) == len(set(combined_final_pools))
    # Drafters should only have cards that were in the original packs
    assert set(combined_final_pools) == set(original_cards_in_packs)


def _flatten_one_level(l):
    return list(itertools.chain(*l))
