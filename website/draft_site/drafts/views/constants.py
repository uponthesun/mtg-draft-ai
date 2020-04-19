import os

from django.conf import settings

from ..cube_data import CubeData
from mtg_draft_ai.brains import SynergyPowerFixingPicker
from mtg_draft_ai.brains import PowerFixingPicker


_cube_id = '6949'
_data_dir = os.path.join(settings.DRAFTS_APP_DIR, 'cubedata')
_cube_file_path = os.path.join(_data_dir, 'cube_{}_tag_data.toml'.format(_cube_id))
_image_urls_file_path = os.path.join(_data_dir, 'cube_{}_image_urls.toml'.format(_cube_id))
_fixer_data_file_path = os.path.join(_data_dir, 'cube_{}_fixer_data.toml'.format(_cube_id))

# Maybe these are stretching the definition of constants, but for now these are values that shouldn't be mutated,
# and need to be used by multiple different views.
# TODO: Redesign this when adding support for multiple cubes.
CUBE_DATA = CubeData.load(_cube_file_path, _image_urls_file_path, _fixer_data_file_path)
PICKER_FACTORY = PowerFixingPicker.factory()
