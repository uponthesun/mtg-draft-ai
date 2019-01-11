"""Implementations of Picker, which (hopefully) use intelligent strategies to make draft picks."""

import random
from mtg_draft_ai.api import Picker


class RandomPicker(Picker):
    """Makes totally random picks. Used for prototyping purposes."""

    def pick(self, pack, cards_owned):
        """Makes a random pick from a pack.

        Args:
            pack (list of Card): The current pack to pick a card out of.
            cards_owned (list of Card): The cards already owned.

        Returns:
            Card: The picked card.
        """
        return pack[random.randint(0, len(pack) - 1)]
