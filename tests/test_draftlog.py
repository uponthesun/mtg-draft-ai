import os
import pytest
from io import StringIO

from mtg_draft_ai import draftlog
from mtg_draft_ai.controller import DraftController, read_cube_toml
from mtg_draft_ai.api import DraftInfo, Drafter
from mtg_draft_ai.brains import RandomPicker


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


@pytest.fixture
def draft_info():
    cube_list = read_cube_toml(os.path.join(TEST_DATA_DIR, 'cube_81183_tag_data.toml'))
    return DraftInfo(card_list=cube_list,
                     cards_per_pack=5, num_phases=3, num_drafters=4)


@pytest.fixture
def controller(draft_info):
    drafters = [Drafter(RandomPicker(), draft_info) for _ in range(0, 4)]
    return DraftController.create(draft_info=draft_info, drafters=drafters, debug=False)


def test_log_full_draft(controller):
    drafters = controller.drafters
    controller.run_draft()

    # Use in-memory buffer instead of actual file
    log_file = StringIO(draftlog.dumps_log(drafters, controller.draft_info))
    loaded_drafters = draftlog.load_drafters_from_log(log_file)

    # loaded_drafters use card names, not full card objects, since it doesn't depend on a tagged data file.
    # for assertions, compare card names to the loaded strings.
    for drafter, loaded in zip(drafters, loaded_drafters):
        assert [c.name for c in drafter.cards_owned] == loaded.cards_owned
        for pack, loaded_pack in zip(drafter.pack_history, loaded.pack_history):
            assert [c.name for c in pack] == loaded_pack


def test_log_to_html(controller):
    controller.run_draft()
    log_file = StringIO(draftlog.dumps_log(controller.drafters, controller.draft_info))

    # It's difficult to actually validate the output html, so just a minimal assertion here
    html = draftlog.log_to_html(log_file)
    assert 'scryfall' in html
