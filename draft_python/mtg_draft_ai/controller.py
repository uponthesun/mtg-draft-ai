import random
from mtg_draft_ai.api import *


class DraftController:

    def __init__(self, draft_info, drafters, packs):
        self.draft_info = draft_info
        self.drafters = drafters
        self.packs = packs

    @staticmethod
    def create(draft_info, drafters):
        if draft_info.num_drafters != len(drafters):
            raise ValueError('Exactly {} drafters required, but got {}'
                             .format(draft_info.num_drafters, len(drafters)))
        packs = create_packs(draft_info)
        return DraftController(draft_info=draft_info, drafters=drafters, packs=packs)

    def run_draft(self):
        for phase in range(0, self.draft_info.num_phases):
            print('====== Phase {} ======'.format(phase))
            direction = 1 if phase % 2 == 0 else -1

            for pick in range(0, self.draft_info.cards_per_pack):
                print('== Pick {} =='.format(pick))

                for drafter in range(0, self.draft_info.num_drafters):
                    pack_index = (pick * direction + drafter) % self.draft_info.num_drafters
                    if pack_index < 0:
                        pack_index += self.draft_info.num_drafters
                    print('Drafter {} picking from pack with original seat {}'
                          .format(drafter, pack_index))

                    pack = self.packs.get(phase=phase, starting_seat=pack_index)
                    print(pack)
                    picked = self.drafters[drafter].pick(pack)
                    print('Picked: {}\n'.format(picked))
                    pack.remove(picked)


def create_packs(draft_info):
    cards_needed = draft_info.num_drafters * draft_info.num_phases * draft_info.cards_per_pack
    if cards_needed > len(draft_info.card_list):
        raise ValueError('Too many cards required for draft configuration: {}'.format(draft_info))

    shuffled_list = draft_info.card_list.copy()
    random.shuffle(shuffled_list)

    pack_contents = []
    for phase in range(0, draft_info.num_phases):
        packs_for_phase = []
        pack_contents.append(packs_for_phase)
        for seat in range(0, draft_info.num_drafters):
            start = (phase * draft_info.num_drafters + seat) * draft_info.cards_per_pack
            end = start + draft_info.cards_per_pack
            packs_for_phase.append(shuffled_list[start:end])  # packs are slices of shuffled list

    return Packs(pack_contents=pack_contents)


def read_cube_list(filename):
    with open(filename, 'r') as f:
        return [l.rstrip() for l in f.readlines()]
