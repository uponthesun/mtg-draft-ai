from mtg_draft_ai.controller import *
from mtg_draft_ai.api import *
from mtg_draft_ai.brains import RandomPicker


cube_list = read_cube_list('new_cube.txt')

print(cube_list)

draft_info = DraftInfo(card_list=cube_list, num_drafters=6, num_phases=3, cards_per_pack=15)

drafters = [Drafter(RandomPicker()) for i in range(0, draft_info.num_drafters)]

controller = DraftController.create(draft_info, drafters)
controller.run_draft()

print('\n\nFinal state:')
for drafter in drafters:
    print('{}\n'.format(drafter))
