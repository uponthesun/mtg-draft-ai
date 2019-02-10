import sys
from mtg_draft_ai import draftlog, deckbuild, display, synergy
from mtg_draft_ai.api import read_cube_toml

log_file = sys.argv[1]
output_file = 'deckbuild.html' if len(sys.argv) < 3 else sys.argv[2]

cube_list = read_cube_toml('cube_81183_tag_data.toml')
drafters = draftlog.load_drafters_from_log(log_file, card_list=cube_list)

html = display.default_style()

i = 0
for drafter in drafters:
    """
    html += 'Drafted Pool {}\n'.format(i)
    for phase in range(0, 3):
        cards_in_phase = drafter.cards_owned[phase * 15 : (phase + 1) * 15]
        html += '<div>\n{}</div>\n'.format(display.cards_to_html(cards_in_phase))
    """
    deck = deckbuild.best_two_color_build(drafter.cards_owned)
    deck_graph = synergy.create_graph(deck)
    sorted_deck = [(tup[0].name, tup[1]) for tup in synergy.sorted_centralities(deck_graph)]

    print('\n'.join([str(tup) for tup in sorted_deck]))
    deck_card_names = [tup[0] for tup in sorted_deck]

    html += 'Deck {} - # Edges: {} \n'.format(i, len(deck_graph.edges))
    html += '<div>\n{}</div>\n'.format(display.card_names_to_html(deck_card_names))
    i += 1

    with open(output_file, 'w') as f:
        f.write(html)
