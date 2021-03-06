import sys
from mtg_draft_ai import draftlog, deckbuild, display, synergy
from mtg_draft_ai.api import read_cube_toml

log_file = sys.argv[1]
output_file = 'output/build.html' if len(sys.argv) < 3 else sys.argv[2]

cube_list = read_cube_toml('cube_81183_tag_data.toml')
drafters = draftlog.load_drafters_from_log(log_file, card_list=cube_list)

decks = [deckbuild.best_two_color_synergy_build(d.cards_owned) for d in drafters]


def decks_to_html(decks):
    html = display.default_style()

    i = 0
    for deck in decks:
        deck_graph = synergy.create_graph(deck, remove_isolated=False)
        sorted_deck = [tup[0] for tup in synergy.sorted_centralities(deck_graph)]

        html += 'Deck {} - # Edges: {} \n'.format(i, len(deck_graph.edges))
        html += '<div>\n{}</div>\n'.format(display.cards_to_html(sorted_deck))
        i += 1

    return html


with open(output_file, 'w') as f:
    f.write(decks_to_html(decks))
print('Deckbuild HTML written to {}'.format(output_file))
