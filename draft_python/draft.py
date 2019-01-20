import sys
from mtg_draft_ai.controller import *
from mtg_draft_ai.api import *
from mtg_draft_ai.brains import *
from mtg_draft_ai import display

output_file = 'draft.html' if len(sys.argv) < 2 else sys.argv[1]

cube_list = read_cube_toml('cube_81183_tag_data.toml')

draft_info = DraftInfo(card_list=cube_list, num_drafters=6, num_phases=3, cards_per_pack=15)

gsp_factory = GreedySynergyPicker.factory(cube_list)
drafters = [Drafter(gsp_factory.create()) for i in range(0, draft_info.num_drafters)]

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


i = 0
for drafter in drafters:
    output_html += 'Deck {}\n'.format(i)
    for phase in range(0, 3):
        cards_in_phase = drafter.cards_owned[phase * 15 : (phase + 1) * 15]
        output_html += '<div>\n{}</div>\n'.format(display.cards_to_html(cards_in_phase))
    i += 1

with open(output_file, 'w') as f:
    f.write(output_html)
