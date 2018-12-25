class Card:

    def __init__(self, name):
        self.name = name


class Drafter:

    def __init__(self, picker):
        self.picker = picker
        self.cards_owned = []

    def pick(self, pack):
        pick = self.picker.pick(pack=pack, cards_owned=self.cards_owned.copy())
        if pick not in pack:
            raise ValueError('Drafter made invalid pick {} from pack {}'.format(pick, pack))

        self.cards_owned.append(pick)
        return pick

    def __repr__(self):
        return 'Cards owned: {} Picker state: {}'.format(self.cards_owned, self.picker)


class DraftInfo:

    def __init__(self, card_list, num_drafters, num_phases, cards_per_pack):
        self.card_list = card_list
        self.num_drafters = num_drafters
        self.num_phases = num_phases
        self.cards_per_pack = cards_per_pack


class Packs:

    def __init__(self, pack_contents):
        self.pack_contents = pack_contents

    def get(self, phase, starting_seat):
        return self.pack_contents[phase][starting_seat]
