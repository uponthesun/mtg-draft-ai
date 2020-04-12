import os

from django.conf import settings

from ..cube_data import CubeData
from mtg_draft_ai.brains import GreedyPowerAndSynergyPicker


_cube_file = os.path.join(settings.DRAFTS_APP_DIR, 'cube_81183_tag_data.toml')
_image_urls_file = os.path.join(settings.DRAFTS_APP_DIR, 'cube_81183_image_urls.toml')
_fixer_data_file = os.path.join(settings.DRAFTS_APP_DIR, 'cube_81183_fixer_data.toml')

# Maybe these are stretching the definition of constants, but for now these are values that shouldn't be mutated,
# and need to be used by multiple different views.
# TODO: Redesign this when adding support for multiple cubes.
CUBE_DATA = CubeData.load(_cube_file, _image_urls_file, _fixer_data_file)
PICKER_FACTORY = GreedyPowerAndSynergyPicker.factory(CUBE_DATA.cards)
