import random
from mtg_draft_ai.api import *


class RandomPicker:
    def pick(self, pack, cards_owned, draft_info):
        return pack[random.randint(0, len(pack) - 1)]

