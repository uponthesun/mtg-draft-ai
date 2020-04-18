"""Implementations of Picker, which (hopefully) use intelligent strategies to make draft picks."""

import abc
import collections
import copy
from dataclasses import dataclass
import random
import statistics
from typing import Dict
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


# Rating = collections.namedtuple('Rating', ['card', 'color_combo', 'rating', 'components'])
@dataclass
class RatedCard:
    card: Card
    color_combo: str
    components: Dict[str, float]
    rating: float = None


class ComponentRater(abc.ABC):

    def __init__(self, weight=1):
        self.weight = weight

    @abc.abstractmethod
    def name(self):
        pass

    @abc.abstractmethod
    def rate(self, card, color_combo, cards_owned, draft_info):
        pass

    @abc.abstractmethod
    def normalize(self, value, all_values, color_combo, cards_owned):
        pass


class TwoColorComboRatingsPicker(Picker):
    ROUND_NUM_DIGITS = 3

    def __init__(self, component_raters):
        self.component_raters = component_raters

    def pick(self, pack, cards_owned, draft_info):
        ranked_candidates = self.ratings(pack, cards_owned, draft_info)
        return ranked_candidates[0].card if len(ranked_candidates) > 0 else pack[0]

    def ratings(self, pack, cards_owned, draft_info):
        cards_with_rating_components = self._raw_rating_components(pack, cards_owned, draft_info)
        cards_with_normalized_rating_components = self._normalized_ratings(cards_with_rating_components, cards_owned)
        rated_cards = self._final_ratings(cards_with_normalized_rating_components)
        sorted_rated_cards = sorted(rated_cards, key=lambda rc: rc.rating, reverse=True)

        return sorted_rated_cards

    def _raw_rating_components(self, pack, cards_owned, draft_info):
        raw_rating_components = []

        for color_combo in COLOR_PAIRS:
            on_color_candidates = [c for c in pack if synergy.castable(c, color_combo)]

            for candidate in on_color_candidates:
                rating_components = {cr.name(): cr.rate(candidate, color_combo, cards_owned, draft_info)
                                     for cr in self.component_raters}
                raw_rating_components.append(RatedCard(card=candidate, color_combo=color_combo,
                                             components=rating_components))
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

    def _final_ratings(self, cards_with_normalized_rating_components):
        final_ratings = [copy.copy(r) for r in cards_with_normalized_rating_components]

        denominator = sum(cr.weight for cr in self.component_raters)
        for card_to_rate in final_ratings:
            numerator = sum(cr.weight * card_to_rate.components[cr.name()] for cr in self.component_raters)
            card_to_rate.rating = round(numerator / denominator, self.ROUND_NUM_DIGITS)

        return final_ratings


class CardsOwnedPowerRater(ComponentRater):

    def name(self):
        return 'cards_owned_power'

    def rate(self, card, color_combo, cards_owned, draft_info):
        on_color_cards_owned = [c for c in cards_owned if synergy.castable(c, color_combo)]
        return sum([power_rating(c) for c in on_color_cards_owned])

    def normalize(self, value, all_values, color_combo, cards_owned):
        return value / max(1, len(cards_owned))


class PowerDeltaRater(ComponentRater):

    def name(self):
        return 'power_delta'

    def rate(self, card, color_combo, cards_owned, draft_info):
        return power_rating(card)

    def normalize(self, value, all_values, color_combo, cards_owned):
        return value


class SynergyDeltaRater(ComponentRater):

    def name(self):
        return 'syn_edges_delta'

    def rate(self, card, color_combo, cards_owned, draft_info):
        on_color_cards_owned = [c for c in cards_owned if synergy.castable(c, color_combo)]
        cards_with_candidate = on_color_cards_owned + [card]
        syn_graph = synergy.create_graph(cards_with_candidate)
        edges_delta = syn_graph.degree[card] if card in syn_graph else 0
        return edges_delta

    def normalize(self, value, all_values, color_combo, cards_owned):
        return value / max(1, len(cards_owned))


class CardsOwnedSynergyRater(ComponentRater):

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

    def __init__(self, common_neighbors, weight=1):
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


class SynergyAndPowerPicker(TwoColorComboRatingsPicker):

    def __init__(self, common_neighbors):
        component_raters = [
            CardsOwnedPowerRater(),
            PowerDeltaRater(),
            CardsOwnedSynergyRater(),
            SynergyDeltaRater(),
            CommonNeighborsRater(common_neighbors=common_neighbors)
        ]
        super().__init__(component_raters)

    @classmethod
    def factory(cls, card_list):
        kwargs = {'common_neighbors': all_common_neighbors(card_list)}
        return Factory(cls, kwargs)


class GreedySynergyPicker(Picker):
    """Attempts to maximize number of synergy edges, for the color pair with the most edges in its pool."""

    def __init__(self, default_ratings, common_neighbors):
        """Basic init method which does no manipulation of its parameters.

        For most cases, use GreedySynergyPicker.factory(card_list).create() instead.

        Args:
            default_ratings ({Card: float}): A default rating for each card.
            common_neighbors ({Card: {Card: List[Card]}}): Generated by all_common_neighbors function
        """
        self.default_ratings = default_ratings
        self.common_neighbors = common_neighbors

    @classmethod
    def factory(cls, card_list):
        """Creates a factory for GreedySynergyPicker instances.

        Performs potentially expensive precomputations, which can be reused to create multiple instances.

        Args:
            card_list (List[Card]): List of all cards in the cube.

        Returns:
            Factory: a factory for GreedySynergyPicker instances, with a no-arguments create() method.
        """
        syn_graph = synergy.create_graph(card_list)

        # Default rating is currently based on centrality, but likely we could find a better measure.
        defaults = nx.eigenvector_centrality(syn_graph)
        for card in card_list:
            defaults.setdefault(card, 0)

        common_neighbors = all_common_neighbors(syn_graph, card_list)

        kwargs = {'default_ratings': defaults,
                  'common_neighbors': common_neighbors}
        return Factory(cls, kwargs)

    def pick(self, pack, cards_owned, draft_info):
        ranked_candidates = self._ratings(pack, cards_owned, draft_info)

        # replace full card object with just card name for more readable output
        printable_candidates = [str(_GSPRating(tup[0].name, *tup[1:])) for tup in ranked_candidates]
        print('\nrankings: {}'.format('\n'.join(printable_candidates)))

        return pack[0] if len(ranked_candidates) == 0 else ranked_candidates[0][0]

    def _ratings(self, pack, cards_owned, draft_info):
        candidates = []

        for color_combo in COLOR_PAIRS:
            on_color_cards = [c for c in cards_owned if synergy.castable(c, color_combo)]
            on_color_candidates = [c for c in pack if synergy.castable(c, color_combo)]

            for candidate in on_color_candidates:
                cards_with_candidate = on_color_cards + [candidate]
                syn_graph = synergy.create_graph(cards_with_candidate)

                # Number of edges in the graph for the card pool plus the candidate.
                total_edges = len(syn_graph.edges)

                # Measure of improvement of future pick quality based on common neighbors between pool and candidate.
                common_neighbors_weighted = self._common_neighbors_weighted(on_color_cards, candidate, color_combo)

                edges_delta = syn_graph.degree[candidate] if candidate in syn_graph else 0

                default = self.default_ratings[candidate]

                candidates.append(_GSPRating(candidate, color_combo, total_edges, common_neighbors_weighted,
                                             edges_delta, default))

        # Lexicographic sort of the fields in the rating tuple (excluding the card and color combo)
        candidates.sort(key=lambda tup: tup[2:], reverse=True)
        return candidates

    def _common_neighbors_weighted(self, card_pool, candidate, colors):
        """Sums # of common neighbors between candidate and each card in the pool."""
        neighbor_count = 0

        for c in card_pool:
            valid_neighbors = [n.name for n in self.common_neighbors[candidate][c]
                               if synergy.castable(n, colors)
                               if n not in card_pool]
            neighbor_count += len(valid_neighbors)

        return neighbor_count


_GSPRating = collections.namedtuple('Rating', ['card', 'color_combo', 'total_edges',
                                               'common_neighbors_weighted', 'edges_delta', 'default'])


_CombinedRating = collections.namedtuple('CombinedRating', ['card', 'color_combo', 'rating',
                                                            'power_delta', 'total_power', 'edges_delta', 'total_edges',
                                                            'common_neighbors_weighted'])


_FixerRating = collections.namedtuple('FixerRating', ['card', 'color_combo', 'rating', 'num_oncolor_playables',
                                                      'num_picks_made', 'num_oncolor_lands'])


class GreedyPowerAndSynergyPicker(GreedySynergyPicker):

    def pick(self, pack, cards_owned, draft_info):
        all_ratings = self._get_ratings(pack, cards_owned, draft_info)
        #print('\nrankings:\n{}'.format('\n'.join([str(r) for r in all_ratings])))

        return pack[0] if len(all_ratings) == 0 else all_ratings[0].card

    # currently depended on by the show_seat view. TODO: formalize this interface
    def _get_ratings(self, pack, cards_owned, draft_info):
        land_fixers = [c for c in pack if c.fixer_color_id and 'land' in c.types]
        regular_cards = [c for c in pack if c not in land_fixers]

        # Create ratings for the "regular cards", i.e. not the land fixers
        synergy_ratings = super()._ratings(regular_cards, cards_owned, draft_info)
        raw_combined_ratings = self._raw_combined_ratings(synergy_ratings, cards_owned)
        normalized_ratings = self._normalize_ratings(raw_combined_ratings, cards_owned)
        composite_ratings = self._composite_ratings(normalized_ratings)

        # Create ratings for land fixers
        land_fixer_ratings = self._land_fixer_ratings(land_fixers, cards_owned)

        all_ratings = composite_ratings + land_fixer_ratings
        all_ratings.sort(key=lambda cr: cr.rating, reverse=True)
        return all_ratings

    @staticmethod
    def _land_fixer_ratings(land_fixers, cards_owned):
        num_picks_made = len(cards_owned)

        ratings = []
        for card in land_fixers:
            on_color_playables = [c for c in cards_owned
                                  if synergy.castable(c, card.fixer_color_id) and
                                  'land' not in c.types]
            on_color_fixing_lands = [c for c in cards_owned
                                     if 'land' in c.types and c.fixer_color_id == card.fixer_color_id]
            num_oncolor_playables = len(on_color_playables)
            num_oncolor_lands = len(on_color_fixing_lands)
            rating = _fixer_rating(num_oncolor_playables, num_picks_made, num_oncolor_lands)
            ratings.append(_FixerRating(card=card, color_combo=card.fixer_color_id, rating=rating,
                                        num_oncolor_playables=num_oncolor_playables, num_picks_made=num_picks_made,
                                        num_oncolor_lands=num_oncolor_lands))
        return ratings

    @classmethod
    def _raw_combined_ratings(cls, synergy_ratings, cards_owned):
        """Generate power ratings (power_delta, total_power) for each card."""

        # Sum up total power rating of current cards owned for each color pair
        pool_total_power_by_color_pair = {}
        for color_pair in COLOR_PAIRS:
            on_color_cards = [c for c in cards_owned if synergy.castable(c, color_pair)]
            total_power = sum([cls._power_rating(c) for c in on_color_cards])
            pool_total_power_by_color_pair[color_pair] = total_power

        raw_ratings = []
        for r in synergy_ratings:
            power_delta = cls._power_rating(r.card)
            total_power = pool_total_power_by_color_pair[r.color_combo] + power_delta

            raw_combined_rating = _CombinedRating(r.card, r.color_combo, rating=None,
                                                  power_delta=power_delta, total_power=total_power,
                                                  edges_delta=r.edges_delta, total_edges=r.total_edges,
                                                  common_neighbors_weighted=r.common_neighbors_weighted)
            raw_ratings.append(raw_combined_rating)
        return raw_ratings

    @staticmethod
    def _power_rating(card):
        """Assign numerical power value for each power tier."""

        # These values are pretty arbitrary, but they feel like reasonable defaults
        # in lieu of a data-driven tuning process or theoretical basis for assigning them.
        # TODO: it's possible we should read these directly from the tags instead, so the cube owner has full control.
        values_by_tier = {
            1: 1,
            2: 0.7,
            3: 0.4,
            4: 0.1,
            None: 0
        }
        if card.power_tier not in values_by_tier:
            raise ValueError('Undefined power tier: {}'.format(card.power_tier))
        return values_by_tier[card.power_tier]

    @staticmethod
    def _composite_ratings(normalized_ratings):
        # Average all of the different power measures into a composite power rating.
        # Then, average the different synergy measures into a composite synergy rating.
        # Finally, average the composite power and synergy ratings into a final rating.
        composite_ratings = []
        for nr in normalized_ratings:
            power_rating = statistics.mean([nr.power_delta, nr.total_power])
            synergy_rating = statistics.mean([nr.edges_delta, nr.total_edges, nr.common_neighbors_weighted])
            rating = round(statistics.mean([power_rating, synergy_rating]), 3)
            composite_ratings.append(nr._replace(rating=rating))
        return composite_ratings

    @staticmethod
    def _normalize_ratings(raw_ratings, cards_owned):
        """Normalizes the given list of ratings.

        'Normalization' here means converting all of the values for a field to proportional values in
        the range of [0, 1]. For some fields there are straightforward ways to determine the practical
        maximum value to divide by. For the ones which there aren't, we use the max value for that field
        in the raw ratings list, making those "relative fields". For relative fields, a normalized value
        of 1 means the original value was the highest in this list of values, not that it was the
        theoretical maximum for that field.

        We assume all values are >= 0. For relative fields, if the max value is 0,
        then all normalized values will be 0 as well.

        Args:
            raw_ratings (List[_CombinedRating]): Raw combined power and synergy ratings.
            cards_owned (List[Card]): Cards currently owned.

        Returns:
            List[_CombinedRatings]: Normalized combined power and synergy ratings.
        """
        if not raw_ratings:
            return []

        max_values = {
            'power_delta': 1.0,
            'edges_delta': len(cards_owned)
        }
        relative_fields = ['total_power', 'total_edges', 'common_neighbors_weighted']
        for field in relative_fields:
            max_values[field] = max([getattr(r, field) for r in raw_ratings])

        fields = relative_fields + list(max_values.keys())
        normalized_ratings = []
        for raw_rating in raw_ratings:
            norm_values = {}
            for field in fields:
                raw_value = getattr(raw_rating, field)
                max_value = max_values[field]
                norm_values[field] = _normalize(raw_value, max_value)

            normalized_ratings.append(raw_rating._replace(**norm_values))
        return normalized_ratings


def _fixer_rating(num_oncolor_nonlands, num_picks_made, num_oncolor_fixer_lands):
    """Rates the value of a fixer land based on the current state of the draft.

    Returns a value in [0, 1]. The higher % of current cards are on-color nonlands,
    the higher the rating, since it's more likely there will be enough playables. The more
    on-color fixer lands we already have, the lower the rating, since we don't need fixing as badly.
    """
    if num_picks_made == 0:
        return 0

    # Hand-tuned lower bound, no strong theoretical justification, but supported by intuition
    # that improving your mana always has value
    lower_bound = 0.3
    offset = 1 + num_oncolor_fixer_lands

    return max(0, lower_bound + (1 - lower_bound) * (num_oncolor_nonlands - offset) / num_picks_made)


def _normalize(value, max_value):
    return round(value / max_value, 3) if max_value != 0 else 0


def all_common_neighbors(cards):
    """Computes common neighbors for all pairs of cards.

    Args:
        graph (networkx.Graph): The graph to compute common neighbors for.
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
    # TODO: it's possible we should read these directly from the tags instead, so the cube owner has full control.
    values_by_tier = {
        1: 1,
        2: 0.7,
        3: 0.4,
        4: 0.1,
        None: 0
    }
    if card.power_tier not in values_by_tier:
        raise ValueError('Undefined power tier: {}'.format(card.power_tier))
    return values_by_tier[card.power_tier]
