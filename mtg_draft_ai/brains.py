"""Implementations of Picker, which (hopefully) use intelligent strategies to make draft picks."""

import abc
import copy
import random
import networkx as nx
from mtg_draft_ai import synergy
from mtg_draft_ai.api import Card, Picker


COLOR_PAIRS = ['WU', 'WB', 'WR', 'WG', 'UB', 'UR', 'UG', 'BR', 'BG', 'RG']
COLOR_TRIOS = ['WUB', 'UBR', 'BRG', 'RGW', 'GWU', 'WBR', 'URG', 'BGW', 'RWU', 'GUB']


class RandomPicker(Picker):
    """Makes totally random picks. Used for prototyping purposes."""

    def pick(self, pack, cards_owned, draft_info):
        """Makes a random pick from a pack.

        Args:
            pack (List[Card]): The current pack to pick a card out of.
            cards_owned (List[Card]): The cards already owned.
            draft_info (DraftInfo): Information about the draft configuration.

        Returns:
            Card: The picked card.
        """
        return pack[random.randint(0, len(pack) - 1)]


class Factory:

    def __init__(self, output_class, kwargs):
        self.output_class = output_class
        self.kwargs = kwargs

    def create(self):
        return self.output_class(**self.kwargs)


class RatedCard:
    """Rating data for a card + two-color combo. Used by TwoColorComboRatingsPicker."""

    def __init__(self, card, color_combo, components, rating=None):
        """
        Args:
            card (Card): The card being rated.
            color_combo (str): The color combo.
            components (Dict[str, float]): Component values which will be inputs into the rating.
            rating (float): The rating for this color combo.
        """
        self.card = card
        self.color_combo = color_combo
        self.components = components
        self.rating = rating


class ConstantWeight:

    def __init__(self, weight):
        self.weight = weight

    def compute(self, cards_owned, draft_info):
        return self.weight


class LinearProgressWeight:

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def compute(self, cards_owned, draft_info):
        progress = len(cards_owned) / (draft_info.num_phases * draft_info.cards_per_pack)

        return self.start + progress * (self.end - self.start)


class ComponentRater(abc.ABC):
    """Defines interface for a Rater for a specific component such as power delta, synergy delta, etc."""

    def __init__(self, weight=ConstantWeight(1)):
        """
        Args:
            weight (float): Weight of this component when calculating the final rating.
        """
        self.weight = weight

    @abc.abstractmethod
    def name(self):
        pass

    @abc.abstractmethod
    def rate(self, card, color_combo, cards_owned, draft_info):
        """Returns the rating for this component only."""
        pass

    @abc.abstractmethod
    def normalize(self, value, all_values, color_combo, cards_owned):
        """Maps the given value into the real number range [0, 1]."""
        pass


class TwoColorComboRatingsPicker(Picker):
    """
    Picker with modular components. Evaluates two-color combinations only for now.

    Does the following steps:
    1). Generates component ratings for each card x two-color combo
    2). Normalizes each component rating into the real number range [0, 1]
    3). Generates final rating via weighted average of components.
    """

    ROUND_NUM_DIGITS = 3

    def __init__(self, component_raters):
        self.component_raters = component_raters

    def pick(self, pack, cards_owned, draft_info):
        ranked_candidates = self.ratings(pack, cards_owned, draft_info)
        return ranked_candidates[0].card if len(ranked_candidates) > 0 else pack[0]

    def ratings(self, pack, cards_owned, draft_info):
        cards_with_rating_components = self._raw_rating_components(pack, cards_owned, draft_info)
        cards_with_normalized_rating_components = self._normalized_ratings(cards_with_rating_components, cards_owned)
        rated_cards = self._final_ratings(cards_with_normalized_rating_components, cards_owned, draft_info)
        sorted_rated_cards = sorted(rated_cards, key=lambda rc: rc.rating, reverse=True)

        return sorted_rated_cards

    def _raw_rating_components(self, pack, cards_owned, draft_info):
        raw_rating_components = []

        for color_combo in COLOR_PAIRS:
            on_color_candidates = [c for c in pack if synergy.castable(c, color_combo) or fixes_for(c, color_combo)]

            for candidate in on_color_candidates:
                rating_components = {cr.name(): cr.rate(candidate, color_combo, cards_owned, draft_info)
                                     for cr in self.component_raters}
                raw_rating_components.append(RatedCard(card=candidate, color_combo=color_combo,
                                             components=rating_components))
        random.shuffle(raw_rating_components) # Randomize order to avoid biasing towards certain colors in case of ties
        return raw_rating_components

    def _normalized_ratings(self, cards_with_rating_components, cards_owned):
        normalized_ratings = [copy.copy(r) for r in cards_with_rating_components]

        for component_rater in self.component_raters:
            key = component_rater.name()
            all_values = [rating.components[key] for rating in normalized_ratings]
            for rating in normalized_ratings:
                normalized_value = component_rater.normalize(rating.components[key], all_values,
                                                                   rating.color_combo, cards_owned)
                rating.components[key] = round(normalized_value, self.ROUND_NUM_DIGITS)

        return normalized_ratings

    def _final_ratings(self, cards_with_normalized_rating_components, cards_owned, draft_info):
        final_ratings = [copy.copy(r) for r in cards_with_normalized_rating_components]

        denominator = sum(cr.weight.compute(cards_owned, draft_info) for cr in self.component_raters)
        for card_to_rate in final_ratings:
            numerator = sum(cr.weight.compute(cards_owned, draft_info) * card_to_rate.components[cr.name()]
                            for cr in self.component_raters)
            card_to_rate.rating = round(numerator / denominator, self.ROUND_NUM_DIGITS)

        return final_ratings


class CardsOwnedPowerRater(ComponentRater):
    """Rates the total power of the pool for a color combo, not counting the candidate card."""

    def name(self):
        return 'cards_owned_power'

    def rate(self, card, color_combo, cards_owned, draft_info):
        on_color_cards_owned = [c for c in cards_owned if synergy.castable(c, color_combo)]
        return sum([power_rating(c) for c in on_color_cards_owned])

    def normalize(self, value, all_values, color_combo, cards_owned):
        max_value = max(all_values)
        return value / max_value if max_value > 0 else 0


class PowerDeltaRater(ComponentRater):
    """Rates the power of candidate card."""

    def name(self):
        return 'power_delta'

    def rate(self, card, color_combo, cards_owned, draft_info):
        return power_rating(card)

    def normalize(self, value, all_values, color_combo, cards_owned):
        return value


class SynergyDeltaRater(ComponentRater):
    """Rates the synergy edges added to the pool by the candidate card for a color combo."""

    def name(self):
        return 'syn_edges_delta'

    def rate(self, card, color_combo, cards_owned, draft_info):
        on_color_cards_owned = [c for c in cards_owned if synergy.castable(c, color_combo)]
        cards_with_candidate = on_color_cards_owned + [card]
        syn_graph = synergy.create_graph(cards_with_candidate)
        edges_delta = syn_graph.degree[card] if card in syn_graph else 0
        return edges_delta

    def normalize(self, value, all_values, color_combo, cards_owned):
        max_value = max(all_values)
        return value / max_value if max_value > 0 else 0


class CardsOwnedSynergyRater(ComponentRater):
    """Rates the total synergy edges of the pool for a color combo, not counting the candidate card."""

    def name(self):
        return 'cards_owned_syn_edges'

    def rate(self, card, color_combo, cards_owned, draft_info):
        on_color_cards_owned = [c for c in cards_owned if synergy.castable(c, color_combo)]
        syn_graph = synergy.create_graph(on_color_cards_owned)

        return len(syn_graph.edges)

    def normalize(self, value, all_values, color_combo, cards_owned):
        max_value = max(all_values)
        return value / max_value if max_value > 0 else 0


class CommonNeighborsRater(ComponentRater):
    """
    Rates how many common neighbors are shared between your pool and the candidate card for a color combo.

    This is a measure of how well the candidate fits with your card pool in the larger context of the format, which
    especially helps for early picks when you don't have many cards yet.
    """

    def __init__(self, common_neighbors, weight=ConstantWeight(1)):
        super().__init__(weight=weight)
        self.common_neighbors = common_neighbors

    def name(self):
        return 'common_neighbors_weighted'

    def rate(self, card, color_combo, cards_owned, draft_info):
        on_color_cards_owned = [c for c in cards_owned if synergy.castable(c, color_combo)]

        neighbor_count = 0
        for c in on_color_cards_owned:
            valid_neighbors = [n.name for n in self.common_neighbors[card][c]
                               if synergy.castable(n, color_combo)
                               if n not in cards_owned]
            neighbor_count += len(valid_neighbors)

        return neighbor_count

    def normalize(self, value, all_values, color_combo, cards_owned):
        max_value = max(all_values)
        return value / max_value if max_value > 0 else 0


class FixingLandsRater(ComponentRater):
    """
    Rates mana fixing for a color combo (lands only for now).

    Generally the rating is higher the more playables you have, and the later in the draft it is.
    The more fixing lands you already have, the lower it is.
    """

    def name(self):
        return 'land_fixer'

    def rate(self, card, color_combo, cards_owned, draft_info):
        num_picks_made = len(cards_owned)
        if num_picks_made == 0:
            return 0

        if not fixes_for(card, color_combo):
            return 0

        num_oncolor_nonlands = len([c for c in cards_owned
                                    if synergy.castable(c, color_combo)
                                    if 'land' not in c.types])
        num_oncolor_fixer_lands = len([c for c in cards_owned if fixes_for(c, color_combo)])

        # Hand-tuned lower bound, no strong theoretical justification, but supported by intuition
        # that improving your mana always has value
        lower_bound = 0.3
        # Hand-tuned / arbitrary starting offset, which makes it rate fixers lower initially and higher later on.
        # Having more fixers already increases the offset which decreases the rating.
        offset = 3 + num_oncolor_fixer_lands
        oncolor_nonlands_proportion_with_offset = max(0, (num_oncolor_nonlands - offset)) / num_picks_made

        return lower_bound + (1 - lower_bound) * oncolor_nonlands_proportion_with_offset

    def normalize(self, value, all_values, color_combo, cards_owned):
        return value

    @staticmethod
    def _fixes_for(card, color_combo):
        if not ('land' in card.types and card.fixer_color_id):
            return False
        return set(color_combo).issubset(set(card.fixer_color_id))


class SynergyPowerFixingPicker(TwoColorComboRatingsPicker):
    """Current best known configuration for 'New World Order' cube (81183)."""

    def __init__(self, common_neighbors):
        component_raters = [
            CardsOwnedPowerRater(weight=LinearProgressWeight(start=1, end=2)),
            PowerDeltaRater(weight=LinearProgressWeight(start=2, end=1)),
            CardsOwnedSynergyRater(weight=LinearProgressWeight(start=1, end=2)),
            SynergyDeltaRater(weight=LinearProgressWeight(start=1, end=2)),
            CommonNeighborsRater(common_neighbors=common_neighbors, weight=LinearProgressWeight(start=2, end=1)),
            # Weight is equal to sum of weights for power delta + synergy delta + common neighbors,
            # which are generally all 0 for fixing lands.
            FixingLandsRater(weight=ConstantWeight(5))
        ]
        super().__init__(component_raters)

    @classmethod
    def factory(cls, card_list):
        kwargs = {'common_neighbors': all_common_neighbors(card_list)}
        return Factory(cls, kwargs)


class PowerFixingPicker(TwoColorComboRatingsPicker):
    """WIP configuration for 'Galaxy Brain Cube' (6949)."""

    def __init__(self):
        component_raters = [
            CardsOwnedPowerRater(),
            PowerDeltaRater(),
            FixingLandsRater()
        ]
        super().__init__(component_raters)

    @classmethod
    def factory(cls, card_list):
        return Factory(cls, {})


def all_common_neighbors(cards):
    """Computes common neighbors for all pairs of cards.

    Args:
        cards (List[Card]): Cards to compute common neighbors for. (May include
            cards not in the graph.)

    Returns:
        {Card: {Card: List[Card]}}: dict which allows lookup of a list of common neighbors for any pair of cards.
    """
    graph = synergy.create_graph(cards)

    common_neighbors = {}
    for i in range(0, len(cards) - 1):
        for j in range(i + 1, len(cards)):
            c1, c2 = cards[i], cards[j]
            common_neighbors.setdefault(c1, {}).setdefault(c2, {})
            common_neighbors.setdefault(c2, {}).setdefault(c1, {})
            if (c1 not in graph) or (c2 not in graph):
                continue

            neighbors = list(nx.common_neighbors(graph, c1, c2))
            common_neighbors[c1][c2] = neighbors
            common_neighbors[c2][c1] = neighbors

    return common_neighbors


def power_rating(card):
    """Assign numerical power value for each power tier."""

    # These values are pretty arbitrary, but they feel like reasonable defaults
    # in lieu of a data-driven tuning process or theoretical basis for assigning them.
    # TODO: make this configurable per cube
    values_by_tier = {
        0: 1.3,
        1: 1.0,
        2: 0.7,
        3: 0.4,
        4: 0.1,
        None: 0.01 # Add a tiny amount for untagged cards to let bots at least stay in colors for untagged cubes
    }
    if card.power_tier not in values_by_tier:
        raise ValueError('Undefined power tier: {}'.format(card.power_tier))
    return values_by_tier[card.power_tier]


def fixes_for(card, color_combo):
    if not ('land' in card.types and card.fixer_color_id):
        return False
    return set(color_combo).issubset(set(card.fixer_color_id))
