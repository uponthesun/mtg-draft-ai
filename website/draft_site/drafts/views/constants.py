import os

from django.conf import settings

from ..cube_data import CubeData
from mtg_draft_ai.brains import SynergyAndPowerPicker

_data_dir = os.path.join(settings.DRAFTS_APP_DIR, 'cubedata')
_cube_file_path = os.path.join(_data_dir, 'cube_81183_tag_data.toml')
_image_urls_file_path = os.path.join(_data_dir, 'cube_81183_image_urls.toml')
_fixer_data_file_path = os.path.join(_data_dir, 'cube_81183_fixer_data.toml')

# Maybe these are stretching the definition of constants, but for now these are values that shouldn't be mutated,
# and need to be used by multiple different views.
# TODO: Redesign this when adding support for multiple cubes.
CUBE_DATA = CubeData.load(_cube_file_path, _image_urls_file_path, _fixer_data_file_path)
PICKER_FACTORY = SynergyAndPowerPicker.factory()
