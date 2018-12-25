import random


class RandomPicker:
    def pick(self, pack, cards_owned):
        return pack[random.randint(0, len(pack) - 1)]

