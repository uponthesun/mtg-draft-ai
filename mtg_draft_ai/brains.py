"""Implementations of Picker, which (hopefully) use intelligent strategies to make draft picks."""

import collections
import random
import statistics
import networkx as nx
from mtg_draft_ai import synergy
from mtg_draft_ai.api import Picker


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


class GreedyPowerAndSynergyPicker(GreedySynergyPicker):

    def pick(self, pack, cards_owned, draft_info):
        synergy_ratings = super()._ratings(pack, cards_owned, draft_info)

        raw_combined_ratings = self._raw_combined_ratings(synergy_ratings, cards_owned)
        normalized_ratings = self._normalize_ratings(raw_combined_ratings)
        composite_ratings = self._composite_ratings(normalized_ratings)
        composite_ratings.sort(key=lambda cr: cr.rating, reverse=True)

        # replace full card object with just card name for more readable output
        printable_candidates = [str(_CombinedRating(tup[0].name, *tup[1:])) for tup in composite_ratings]
        print('\nrankings:\n{}'.format('\n'.join(printable_candidates)))

        return pack[0] if len(composite_ratings) == 0 else composite_ratings[0].card



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
            2: 0.8,
            3: 0.6,
            4: 0.3,
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
    def _normalize_ratings(raw_ratings):
        """Normalizes the given list of ratings.

        'Normalization' here means converting all of the values for a field to proportional values in
        the range of [0, 1]. We do this by finding the max value for that field in this list, and
        dividing all values for that field by the max value.

        Note that this means that a normalized value of 1 means the original value was the highest in
        this list of values, not that it was the theoretical maximum for that field.

        We assume all values are >= 0, and if the max value is 0, then all normalized values will be 0 as well.

        Args:
            raw_ratings (List[_CombinedRating]): Raw combined power and synergy ratings.

        Returns:
            List[_CombinedRatings]: Normalized combined power and synergy ratings.
        """
        if not raw_ratings:
            return []

        fields = ['power_delta', 'total_power', 'edges_delta', 'total_edges', 'common_neighbors_weighted']
        max_values = {}
        for field in fields:
            max_values[field] = max([getattr(r, field) for r in raw_ratings])

        normalized_ratings = []
        for raw_rating in raw_ratings:
            norm_values = {}
            for field in fields:
                raw_value = getattr(raw_rating, field)
                max_value = max_values[field]
                norm_values[field] = _normalize(raw_value, max_value)

            normalized_ratings.append(raw_rating._replace(**norm_values))
        return normalized_ratings


def _normalize(value, max_value):
    return round(value / max_value, 3) if max_value != 0 else 0


def all_common_neighbors(graph, cards):
    """Computes common neighbors for all pairs of cards.

    Args:
        graph (networkx.Graph): The graph to compute common neighbors for.
        cards (List[Card]): Cards to compute common neighbors for. (May include
            cards not in the graph.)

    Returns:
        {Card: {Card: List[Card]}}: dict which allows lookup of a list of common neighbors for any pair of cards.
    """
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
