import sys
from mtg_draft_ai.controller import *
from mtg_draft_ai.api import *
from mtg_draft_ai.brains import *
from mtg_draft_ai import display
from mtg_draft_ai.deckbuild import best_two_color_build

output_file = 'draft.html' if len(sys.argv) < 2 else sys.argv[1]

cube_list = read_cube_toml('cube_81183_tag_data.toml')

draft_info = DraftInfo(card_list=cube_list, num_drafters=6, num_phases=3, cards_per_pack=15)

gsp_factory = GreedySynergyPicker.factory(cube_list)
drafters = [Drafter(gsp_factory.create(), draft_info) for i in range(0, draft_info.num_drafters)]

controller = DraftController.create(draft_info, drafters)
controller.run_draft()

print('\n\nFinal state:')
for drafter in drafters:
    print('{}\n'.format(drafter))


output_html = """
<style>
card-image {
    display: inline;
    margin: 1px;
}
</style>
"""

#decks = [best_two_color_build(d.cards_owned) for d in drafters]

i = 0
for drafter in drafters:
    output_html += 'Drafted Pool {}\n'.format(i)
    for phase in range(0, 3):
        cards_in_phase = drafter.cards_owned[phase * 15 : (phase + 1) * 15]
        output_html += '<div>\n{}</div>\n'.format(display.cards_to_html(cards_in_phase))

    deck = best_two_color_build(drafter.cards_owned)
    deck_graph = synergy.create_graph(deck)
    deck_with_degrees = [(c.name, deck_graph.degree(c) if c in deck_graph else 0) for c in deck]
    deck_with_degrees.sort(key=lambda tup: tup[1], reverse=True)
    print('\n'.join([str(tup) for tup in deck_with_degrees]))
    deck_card_names = [tup[0] for tup in deck_with_degrees]

    output_html += 'Deck {} - # Edges: {} \n'.format(i, len(deck_graph.edges))
    output_html += '<div>\n{}</div>\n'.format(display.card_names_to_html(deck_card_names))
    i += 1

    with open(output_file, 'w') as f:
        f.write(output_html)
