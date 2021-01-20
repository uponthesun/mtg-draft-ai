from .cube_data import CubeData
from mtg_draft_ai.brains import SynergyPowerFixingPicker
from mtg_draft_ai.brains import PowerFixingPicker


# For now these are "constants" because they shouldn't be mutated and are used across multiple views.
CUBES = [
    CubeData.load(
        name='NWO Cube',
        cube_id=81183,
        cube_file_name='cube_81183_tag_data.toml',
        fixer_data_file_name='cube_81183_fixer_data.toml',
        image_urls_file_name='cube_81183_image_urls.toml',
        picker_class=SynergyPowerFixingPicker,
        autobuild_enabled=True
    ),
    CubeData.load(
        name='Galaxy Brain Cube',
        cube_id=6949,
        cube_file_name='cube_6949_tag_data.toml',
        fixer_data_file_name='cube_6949_fixer_data.toml',
        image_urls_file_name='cube_6949_image_urls.toml',
        picker_class=PowerFixingPicker,
        autobuild_enabled=False
    ),
    CubeData.load(
        name='FIRE Cube',
        cube_id=4,
        cube_file_name='fire_cube_tag_data.toml',
        fixer_data_file_name='fire_cube_fixer_data.toml',
        image_urls_file_name='fire_cube_image_urls.toml',
        picker_class=PowerFixingPicker,
        autobuild_enabled=False
    )
]
CUBES_BY_ID = {c.cube_id: c for c in CUBES}
