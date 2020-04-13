"""Data types and interfaces which represent basic concepts in Magic drafting."""

import abc
import toml


class Card:
    """Identifying information and other relevant attributes of a single Magic card."""

    def __init__(self, name, color_id=None, types=None, mana_cost=None, tags=None, power_tier=None,
                 fixer_color_id=None):
        """
        Args:
            name (str): The card's name.
            color_id (str): The card's color identity, as read from cubetutor. E.g. a cube owner
                can assign R for Bomat Courier.
            types (List[str]): The card's supertypes.
            tags (List[(str, str)]): List of applicable tags for this card, as read from cubetutor.
                Currently, only two-part tags are supported, in the format: <Category> - <Subcategory>
                e.g.: Lifegain - Payoff
                Defaults to [].
            power_tier (int): Power level tier as tagged by cube maintainer (currently values 1-4 allowed).
        """
        tags = [] if tags is None else tags

        self.name = name
        self.color_id = color_id
        self.types = types
        self.mana_cost = mana_cost
        self.tags = tags
        self.power_tier = power_tier
        self.fixer_color_id=fixer_color_id

    def full_repr(self):
        return '{}: {}'.format(self.__class__.__name__, repr(self.__dict__))

    def __repr__(self):
        return 'C: {}'.format(self.name)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)

    @staticmethod
    def from_raw_data(name, properties):
        raw_tags = properties['tags']
        tags = []
        power_tier = None

        for raw_tag in raw_tags:
            # Currently, the only tags we use are:
            # - power level tags in the format: "Tier N"
            # - synergy tags in the format: "Theme - Role"
            if raw_tag.startswith('Tier'):
                power_tier = int(raw_tag.split(' ')[1])
            else:
                split = raw_tag.split('-')
                if len(split) == 2:
                    k, v = split
                    tags.append((k.strip(), v.strip()))

        return Card(name, color_id=properties['color_identity'], types=properties['types'],
                    mana_cost=properties['mana_cost'], tags=tags, power_tier=power_tier)


class Drafter:
    """Makes picks and tracks cards already picked."""

    def __init__(self, picker, draft_info):
        """
        Args:
            picker: A Picker implementation. This Drafter instance will delegate
                all picking decisions to picker.
        """
        self.picker = picker
        self.draft_info = draft_info
        self.cards_owned = []
        self.pack_history = []

    def pick(self, pack):
        """Picks a card by delegating to self.picker, and adds it to owned cards.

        Args:
            pack (List[Card]): The current pack to pick a card out of.

        Returns:
            Card: The picked card.
        """
        pack_snapshot = pack.copy()
        self.pack_history.append(pack_snapshot)
        pick = self.picker.pick(pack=pack.copy(), cards_owned=self.cards_owned.copy(),
                                draft_info=self.draft_info)
        if pick not in pack:
            raise ValueError('Drafter made invalid pick {} from pack {}'.format(pick, pack))

        self.cards_owned.append(pick)
        return pick

    def __repr__(self):
        return 'Cards owned: {} Picker state: {}'.format([str(card) for card in self.cards_owned],
                                                         self.picker)


class Picker(abc.ABC):
    """Makes pick decisions given a pack and cards already owned.

    Documents and partially enforces the contract between Drafter and Picker implementations.
    """

    @abc.abstractmethod
    def pick(self, pack, cards_owned, draft_info):
        """Implementations should return the picked Card.

        Implementations do not need to modify the state of either pack or cards_owned,
        as doing so will have no effect on the draft state.

        Args:
            pack (List[Card]): The current pack to pick a card out of.
            cards_owned (List[Card]): The cards already owned.
            draft_info (DraftInfo): Information about the draft configuration.

        Returns:
            Card: The picked card.
        """
        pass


class DraftInfo:
    """The information available to all drafters that does not change during the draft."""

    def __init__(self, card_list, num_drafters, num_phases, cards_per_pack):
        """
        Args:
            card_list (List[Card]): A list of all cards in the cube.
            num_drafters (int): Number of drafters (aka number of seats in the draft).
            num_phases (int): Number of draft phases (e.g. there are 3 phases in a typical draft).
            cards_per_pack (int): Number of cards in each pack.
        """
        self.card_list = card_list
        self.num_drafters = num_drafters
        self.num_phases = num_phases
        self.cards_per_pack = cards_per_pack

    def num_cards_in_draft(self):
        return self.num_drafters * self.num_phases * self.cards_per_pack

    def __str__(self):
        return 'num_drafters: {}, num_phases: {}, cards_per_pack: {}'.format(
            self.num_drafters, self.num_phases, self.cards_per_pack)


class Packs:
    """The collection of all packs used in a draft, organized by phase and seat.

    Wrapper class for the backing data structure for the pack contents, which is a
    List[List[List[Card]]], organized as follows:

    Outermost list: one element for each phase of the draft
    Second-level list: one element for each seat in the draft (aka each drafter)
    Innermost List[Card]: one specific pack
    """

    def __init__(self, pack_contents):
        """
        Args:
            pack_contents (list of list of List[Card]): The raw pack contents. Should already
                be randomized and organized into phases and seats.
        """
        self.pack_contents = pack_contents

    def get_pack(self, phase, starting_seat):
        """Gets a specific pack.

        Args:
            phase (int): The current draft phase.
            starting_seat (int): The seat index that this pack would have been at during the
                start of the current draft phase.

        Returns:
            List[Card]: A specific pack.
        """
        return self.pack_contents[phase][starting_seat]


def read_cube_toml(filename, fixer_data_filename=None):
    """Reads cube data from a toml file and returns it as a List[Card].

    Args:
        filename (str): Path (relative or absolute) to file containing cube list. File must
            be in the TOML format.
        fixer_data_filename (str): Path (relative or absolute) to file containing color identity data
            for fixer lands. File should contain a dict of card name: color id, in the TOML format.

    Returns:
        List[Card]: The List[Card] from the file.
    """
    raw_data = toml.load(filename)
    cube_list = [Card.from_raw_data(*tup) for tup in raw_data.items()]

    if fixer_data_filename:
        fixers = toml.load(fixer_data_filename)
        for card in cube_list:
            if card.name in fixers:
                card.fixer_color_id = fixers[card.name]

    return cube_list
