"""Implementations of Picker, which (hopefully) use intelligent strategies to make draft picks."""

import collections
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


_GSPRating = collections.namedtuple('Rating', ['card', 'color_combo', 'total_edges',
                                               'pool_size', 'common_neighbors', 'default'])


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

    @staticmethod
    def factory(card_list):
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
        return Factory(GreedySynergyPicker, kwargs)

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
                # Number of edges added by the candidate.
                #new_edges = _num_new_edges(syn_graph, candidate)

                pool_size = len(cards_with_candidate)

                # Number of nodes in global graph which neighbor both the candidate and the card pool.
                # Does not count cards already in the pool as neighbors.
                common_neighbors = len(self._card_pool_common_neighbors(on_color_cards, candidate, color_combo))
                default = self.default_ratings[candidate]

                candidates.append(_GSPRating(candidate, color_combo, total_edges, pool_size,
                                             common_neighbors, default))

        # Lexicographic sort of the fields in the rating tuple (excluding the card and color combo)
        candidates.sort(key=lambda tup: tup[2:], reverse=True)
        return candidates

    def _card_pool_common_neighbors(self, card_pool, candidate, colors):
        neighbors = set()
        for card in card_pool:
            neighbors.update(self.common_neighbors[candidate][card])

        # Only count on-color neighbors not already in the pool, and in the color combo
        neighbors = {c for c in neighbors
                     if c not in card_pool
                     if synergy.castable(c, colors)}
        return neighbors


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


def _num_new_edges(graph, node):
    if node not in graph.nodes:
        return 0
    return nx.degree(graph, node)
