from mtg_draft_ai.api import *
from mtg_draft_ai import synergy

cards = read_cube_toml('cube_81183_tag_data.toml')
G = synergy.create_graph(cards)
