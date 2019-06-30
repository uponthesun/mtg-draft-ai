"""Implementations of Picker, which (hopefully) use intelligent strategies to make draft picks."""

import collections
import math
import random
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
                # common_neighbors = self._common_neighbors(on_color_cards, candidate, color_combo)

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

    def _common_neighbors(self, card_pool, candidate, colors):
        """Sums # of common neighbors between candidate and each card in the pool."""

        neighbors = set()

        for c in card_pool:
            valid_neighbors = [n.name for n in self.common_neighbors[candidate][c]
                               if synergy.castable(n, colors)
                               if n not in card_pool]
            neighbors.update(valid_neighbors)

        return len(neighbors)


_GSPRating = collections.namedtuple('Rating', ['card', 'color_combo', 'total_edges',
                                               'common_neighbors_weighted', 'edges_delta', 'default'])


_CombinedRating = collections.namedtuple('CombinedRating', ['card', 'color_combo', 'rating',
                                                            'power_delta', 'total_power', 'edges_delta', 'total_edges',
                                                            'common_neighbors_weighted', 'raw_values'])


class GreedyPowerAndSynergyPicker(GreedySynergyPicker):

    def pick(self, pack, cards_owned, draft_info):
        synergy_ratings = self._ratings(pack, cards_owned, draft_info)
        combined_ratings = GreedyPowerAndSynergyPicker._combined_ratings(synergy_ratings, cards_owned)
        combined_ratings.sort(key=lambda cr: cr.rating, reverse=True)

        # replace full card object with just card name for more readable output
        printable_candidates = [str(_CombinedRating(tup[0].name, *tup[1:])) for tup in combined_ratings]
        print('\nrankings:\n{}'.format('\n'.join(printable_candidates)))

        return pack[0] if len(combined_ratings) == 0 else combined_ratings[0].card

    @classmethod
    def _combined_ratings(cls, synergy_ratings, cards_owned):
        pool_total_power_by_color_pair = {}
        for color_pair in COLOR_PAIRS:
            on_color_cards = [c for c in cards_owned if synergy.castable(c, color_pair)]
            total_power = sum([cls._power_rating(c) for c in on_color_cards])
            pool_total_power_by_color_pair[color_pair] = total_power

        raw_ratings = []
        for r in synergy_ratings:
            power_delta = cls._power_rating(r.card)
            # round to correct for floating point arithmetic imprecision
            total_power = round(pool_total_power_by_color_pair[r.color_combo] + power_delta, 2)

            raw_values = {'power_delta': power_delta, 'total_power': total_power,
                          'edges_delta': r.edges_delta, 'total_edges': r.total_edges,
                          'common_neighbors_weighted': r.common_neighbors_weighted}

            raw_ratings.append((r, raw_values))

        return cls._normalize_ratings(raw_ratings)

    @staticmethod
    def _power_rating(card):
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
    def _normalize_ratings(raw_ratings):
        if not raw_ratings:
            return []

        synergy_ratings, raw_values = zip(*raw_ratings)

        # all elements should have the same fields
        fields = raw_values[0].keys()

        max_values = {}
        for field in fields:
            max_values[field] = max([rv[field] for rv in raw_values])

        final_ratings = []

        for synergy_rating, raws in raw_ratings:
            card = synergy_rating.card
            color_combo = synergy_rating.color_combo

            normalized_values = {k: _normalize(v, max_values[k]) for k, v in raws.items()}
            power_delta = raws['power_delta']  # don't normalize power since it's already in [0, 1]
            total_power = normalized_values['total_power']
            edges_delta = normalized_values['edges_delta']
            total_edges = normalized_values['total_edges']
            common_neighbors_weighted = normalized_values['common_neighbors_weighted']

            rating = round(power_delta + total_power + edges_delta + total_edges + common_neighbors_weighted, 3)

            final_ratings.append(_CombinedRating(card, color_combo, rating, power_delta, total_power,
                                                 edges_delta, total_edges, common_neighbors_weighted, raws))
        return final_ratings


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


def sigmoid(x, k=0.5, x0=5):
    return round(1 / (1 + math.exp(-k * (x - x0))), 3)
