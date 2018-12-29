"""Data types and interfaces which represent basic concepts in Magic drafting."""

import abc


class Card:
    """Identifying information and other relevant attributes of a single Magic card."""

    def __init__(self, name):
        """
        Args:
            name (str): The card's name.
        """
        self.name = name

    def __repr__(self):
        return 'C: {}'.format(self.name)

    def __eq__(self, other):
        return self.name == other.name


class Drafter:
    """Makes picks and tracks cards already picked."""

    def __init__(self, picker):
        """
        Args:
            picker: A Picker implementation. This Drafter instance will delegate
                all picking decisions to picker.
        """
        self.picker = picker
        self.cards_owned = []

    def pick(self, pack):
        """Picks a card by delegating to self.picker, and adds it to owned cards.

        Args:
            pack (list of Card): The current pack to pick a card out of.

        Returns:
            Card: The picked card.
        """
        pick = self.picker.pick(pack=pack.copy(), cards_owned=self.cards_owned.copy())
        if pick not in pack:
            raise ValueError('Drafter made invalid pick {} from pack {}'.format(pick, pack))

        self.cards_owned.append(pick)
        return pick

    def __repr__(self):
        return 'Cards owned: {} Picker state: {}'.format(self.cards_owned, self.picker)


class Picker(abc.ABC):
    """Makes pick decisions given a pack and cards already owned.

    Documents and partially enforces the contract between Drafter and Picker implementations.
    """

    @abc.abstractmethod
    def pick(self, pack, cards_owned):
        """Implementations should return the picked Card.

        Implementations do not need to modify the state of either pack or cards_owned,
        as doing so will have no effect on the draft state.

        Args:
            pack (list of Card): The current pack to pick a card out of.
            cards_owned (list of Card): The cards already owned.

        Returns:
            Card: The picked card.
        """
        pass


class DraftInfo:
    """The information available to all drafters that does not change during the draft."""

    def __init__(self, card_list, num_drafters, num_phases, cards_per_pack):
        """
        Args:
            card_list (list of Card): A list of all cards in the cube.
            num_drafters (int): Number of drafters (aka number of seats in the draft).
            num_phases (int): Number of draft phases (e.g. there are 3 phases in a typical draft).
            cards_per_pack (int): Number of cards in each pack.
        """
        self.card_list = card_list
        self.num_drafters = num_drafters
        self.num_phases = num_phases
        self.cards_per_pack = cards_per_pack


class Packs:
    """The collection of all packs used in a draft, organized by phase and seat.

    Wrapper class for the backing data structure for the pack contents, which is a
    list of list of list of Cards, organized as follows:

    Outermost list: one element for each phase of the draft
    Second-level list: one element for each seat in the draft (aka each drafter)
    Innermost list of Cards: one specific pack
    """

    def __init__(self, pack_contents):
        """
        Args:
            pack_contents (list of list of list of Card): The raw pack contents. Should already
                be randomized and organized into phases and seats.
        """
        self.pack_contents = pack_contents

    def get(self, phase, starting_seat):
        """Gets a specific pack.

        Args:
            phase (int): The current draft phase.
            starting_seat (int): The seat index that this pack would have been at during the
                start of the current draft phase.

        Returns:
            list of Card: A specific pack.
        """
        return self.pack_contents[phase][starting_seat]
