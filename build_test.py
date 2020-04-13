import sys
from mtg_draft_ai import draftlog, deckbuild, display, synergy
from mtg_draft_ai.api import read_cube_toml

output_file = 'output/comm_build.html' if len(sys.argv) < 3 else sys.argv[2]

cube_list = read_cube_toml('cube_81183_tag_data.toml')
cards_by_name = {c.name: c for c in cube_list}
#drafters = draftlog.load_drafters_from_log(log_file, card_list=cube_list)
#decks = [deckbuild.best_two_color_synergy_build(d.cards_owned) for d in drafters]

card_pool_names = [
    "Skinshifter",
    "Pack Guardian",
    "Supreme Phantom",
    "Ninja of the Deep Hours",
    "Negate",
    "Familiar's Ruse",
    "Thought Courier",
    "Riddleform",
    "Grazing Gladehart",
    "Filigree Familiar",
    "Prey Upon",
    "Foul Orchard",
    "Llanowar Wastes",
    "Sulfur Falls",
    "Killing Glare",
    "Wizard's Retort",
    "Higure, the Still Wind",
    "Rattlechains",
    "Centaur's Herald",
    "Harbinger of the Tides",
    "Essence Flux",
    "Territorial Allosaurus",
    "Greenwarden of Murasa",
    "Foundry of the Consuls",
    "Scrounging Bandar",
    "Woodland Stream",
    "Kiri-Onna",
    "Isolated Chapel",
    "Highland Lake",
    "Sidisi, Brood Tyrant",
    "Naru Meha, Master Wizard",
    "Ludevic's Test Subject",
    "Bounding Krasis",
    "Opt",
    "Mana Leak",
    "Simic Signet",
    "Dissolve",
    "Supreme Will",
    "Kessig Cagebreakers",
    "Birds of Paradise",
    "River Hoopoe",
    "Crawling Sensation",
    "Temple of Mystery",
    "Submerged Boneyard",
    "Battlefield Forge",
]

uw_pool_names = [
    "Brago, King Eternal",
    "Pianna, Nomad Captain",
    "Rattlechains",
    "Curious Obsession",
    "Phalanx Leader",
    "Soulherder",
    "Temple of Enlightenment",
    "Skinshifter",
    "Gird for Battle",
    "Gideon's Reproach",
    "Voyage's End",
    "Golgari Signet",
    "Kessig Cagebreakers",
    "Titania, Protector of Argoth",
    "Sulfurous Springs",
    "Ninja of the Deep Hours",
    "Lantern Kami",
    "Nebelgast Herald",
    "Divine Visitation",
    "Higure, the Still Wind",
    "Augury Owl",
    "Tower Geist",
    "Fireblade Artist",
    "Memorial to Glory",
    "Piston Sledge",
    "Pacification Array",
    "Kami of Ancient Law",
    "Deadeye Harpooner",
    "Magmatic Force",
    "Highland Lake",
    "Cloudblazer",
    "Valorous Stance",
    "Favored Hoplite",
    "Skyscanner",
    "Quickling",
    "Drogskol Captain",
    "Foundry of the Consuls",
    "Oppressive Rays",
    "Fettergeist",
    "Brittle Effigy",
    "Essence Flux",
    "Brushland",
    "Cultivator's Caravan",
    "Clifftop Retreat",
    "Isolated Chapel",
]

card_pool = [cards_by_name[name] for name in uw_pool_names]

deck = deckbuild.best_two_color_synergy_build(card_pool)


def deck_to_html(deck):
    html = display.default_style()

    deck_graph = synergy.create_graph(deck, remove_isolated=False)
    #sorted_deck = [tup[0] for tup in synergy.sorted_centralities(deck_graph)]

    html += 'Deck - # Edges: {} \n'.format(len(deck_graph.edges))
    html += '<div>\n{}</div>\n'.format(display.cards_to_html(deck))

    return html

html = deck_to_html(deck)

leftovers = [c for c in card_pool if c not in deck]
html += 'Leftovers'
html += '<div>\n{}</div>\n'.format(display.cards_to_html(leftovers))

with open(output_file, 'w') as f:
    f.write(html)
print('Deckbuild HTML written to {}'.format(output_file))
