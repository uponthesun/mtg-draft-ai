import random
from mtg_draft_ai.api import *


class DraftController:
    """Runs a draft by asking each drafter to pick from the right pack in the right order."""

    def __init__(self, draft_info, drafters, packs):
        """Basic init method which does no manipulation of its parameters.

        For most cases, use DraftController.create instead, which creates shuffled packs
        from the card list.

        Args:
            draft_info (api.DraftInfo): Config about the draft, which will not change
                during the draft.
            drafters (list of api.Drafter): The Drafters, which may have different Picker
                implementations.
            packs (api.Packs): The Packs to use for this draft. Should already be initialized.
        """
        self.draft_info = draft_info
        self.drafters = drafters
        self.packs = packs

    @staticmethod
    def create(draft_info, drafters):
        """Creates a DraftController with shuffled packs generated from the card list.

        Args:
            draft_info (api.DraftInfo): Config about the draft, which will not change
                during the draft.
            drafters (list of api.Drafter): The Drafters, which may have different Picker
                implementations.
        Returns:
            DraftController: A DraftController initialized with shuffled packs.
        """
        if draft_info.num_drafters != len(drafters):
            raise ValueError('Exactly {} drafters required, but got {}'
                             .format(draft_info.num_drafters, len(drafters)))
        packs = create_packs(draft_info)
        return DraftController(draft_info=draft_info, drafters=drafters, packs=packs)

    def run_draft(self):
        """Runs a draft by asking each drafter to pick from the right pack in the right order.

        Throughout the drafting process, mutates self.packs as each pick is made.
        Each Drafter in self.drafters will update its own list of picked cards, which can be used
        to view the final result of the draft.
        """

        # "Draft phase" is commonly referred to as "Pack" by magic players, e.g. "Pack 1 pick 5".
        # A typical draft has 3 draft phases.
        for phase in range(0, self.draft_info.num_phases):
            print('====== Phase {} ======'.format(phase))
            # Alternate passing directions based on phase, starting with passing left.
            direction = 1 if phase % 2 == 0 else -1

            # "Pick index" is the "pick 1" part of "Pack 1 pick 5". In each phase, we repeat
            # picking a card and passing until we've picked all the cards in the pack.
            for pick in range(0, self.draft_info.cards_per_pack):
                print('== Pick {} =='.format(pick))

                # Have each drafter make a pick.
                for drafter in range(0, self.draft_info.num_drafters):
                    # Implement "passing" packs after each pick by shifting the index of the pack
                    # assigned to each drafter by the pick index. We add when passing left,
                    # and subtract when passing right (picture the packs staying in place,
                    # and the drafters standing up and walking around the table).
                    # Then we apply modulus (since the packs are passed in a circle).
                    pack_index = (pick * direction + drafter) % self.draft_info.num_drafters

                    # The mod of a negative number will remain negative, e.g. -11 mod 8 = -3,
                    # but we want to use the positive equivalent to find the index into the packs,
                    # so we add num_drafters if it's a negative number. So in our example, -3
                    # would become 5. This represents starting at seat 0 and finding the drafter
                    # 3 seats to the left, which would be the drafter at seat 5.
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
    """Creates a collection of shuffled packs to be used for one draft.

    Args:
        draft_info (api.DraftInfo): Contains card list and draft config used to create packs.

    Returns:
        api.Packs: A collection of shuffled packs.
    """
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
    """Reads a cube list from a file and returns it as a list of Cards.

    Args:
        filename (str): Path (relative or absolute) to file containing cube list. File should
            be plain text, with one card name per line.

    Returns:
        list of Card: The list of cards from the file.
    """
    with open(filename, 'r') as f:
        return [Card(name=l.rstrip()) for l in f.readlines()]
