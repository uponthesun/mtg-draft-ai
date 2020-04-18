"""Deckbuilding functions."""

from collections import namedtuple
import itertools

from mtg_draft_ai import synergy

import networkx as nx


_NONLANDS_IN_DECK_DEFAULT = 23

_TWO_COLOR_COMBOS = ['WU', 'WB', 'WR', 'WG', 'UB', 'UR', 'UG', 'BR', 'BG', 'RG']
_THREE_COLOR_COMBOS = ['WUB', 'WUR', 'WUG', 'WBR', 'WBG', 'WRG', 'UBR', 'UBG', 'URG', 'BRG']
_COLOR_COMBOS = _TWO_COLOR_COMBOS + _THREE_COLOR_COMBOS


def _num_nonlands(current_build):
    return len([c for c in current_build if 'land' not in c.types])


_CardSwap = namedtuple('CardSwap', ['card_to_remove', 'card_to_add', 'improvement'])


def _find_best_swap(current_build, candidates_to_add, candidates_to_remove=None):
    initial_candidates_to_remove = candidates_to_remove or current_build
    # Only consider nonlands for swaps
    initial_candidates_to_remove = [c for c in initial_candidates_to_remove if not 'land' in c.types]
    candidates_to_add = [c for c in candidates_to_add if not 'land' in c.types]

    card_to_add = None
    card_to_remove = None
    max_improvement = 0

    for card in candidates_to_add:
        build_with_card = current_build + [card]
        graph_with_card = synergy.create_graph(build_with_card, remove_isolated=False)
        current_removal_candidates = [c for c in initial_candidates_to_remove if c in build_with_card]

        card_degree = graph_with_card.degree(card)
        worst_card, worst_degree = min([(c, graph_with_card.degree(c)) for c in current_removal_candidates],
                                       key=lambda tup: tup[1])
        improvement = card_degree - worst_degree

        if not card_to_add or improvement > max_improvement:
            card_to_add, card_to_remove, max_improvement = card, worst_card, improvement

    return _CardSwap(card_to_remove=card_to_remove, card_to_add=card_to_add, improvement=max_improvement)


def _refine_build(current_build, leftovers):
    """Improves on current build by trying 1-for-1 swaps of leftover cards with cards in the current build.

    Checks all leftover cards to see if there exists a 1-for-1 swap with the worst card in the current build
    that improves the build. Makes the swap that causes the largest such improvement. Repeat until there is none.
    Removed cards aren't considered for re-adding, so the process is guaranteed to terminate.
    """
    while True:
        card_swap = _find_best_swap(current_build, leftovers)

        if card_swap.card_to_add and card_swap.improvement > 0:
            current_build.remove(card_swap.card_to_remove)
            current_build.append(card_swap.card_to_add)
            leftovers.remove(card_swap.card_to_add)
        else:
            break

    return current_build


def _comm_score(current_graph, comm):
    build_with_comm = list(current_graph.nodes) + list(comm)
    graph_with_comm = synergy.create_graph(build_with_comm, remove_isolated=False)
    edges_added = len(graph_with_comm.edges) - len(current_graph.edges)
    return edges_added / len(comm)


def _communities_build(card_pool_graph, main_colors, splash_colors=[]):
    """Builds a deck by trying combinations of communities. Ignores all other factors (including color).

    Outline of algorithm:

    1). Split the on-color cards into communities using networkx's greedy_modular_communities
    2). Find the "best" community to add based on # of edges it would add / # nodes
    3). Add the entire community to the pool
    4). Repeat 2-3 until we have >= the target number of playables
    5). Cut cards one by one based on lowest centrality score in the graph for the pool
    until we have the target number of playables
    6). Check leftovers to see if any cards should be swapped with the worst cards in current build

    Args:
        card_pool_graph (networkx.Graph): A synergy graph of Cards as the card pool to build from.
        target_playables (int): The number of nonland cards to include in the deck. Utility lands can still be
            included if they are beneficial, but don't count towards this total.

    Returns:
        List[Card]: The build for the given pool pool of cards.
    """
    if _num_nonlands(card_pool_graph.nodes) < _NONLANDS_IN_DECK_DEFAULT:
        return list(card_pool_graph.nodes)

    current_build = []

    fixers = [c for c in card_pool_graph
              if _fixer_for_colors(c, list(main_colors) + list(splash_colors)) and
              # Don't count splashed fixers
              not _splashed(c, splash_colors)]
    nonland_fixers = [c for c in fixers if 'land' not in c.types]
    land_fixers = [c for c in fixers if 'land' in c.types]

    # Heuristic: start with all nonland fixers in build if there are splash colors. They may get cut later.
    if splash_colors:
        current_build.extend(nonland_fixers)

    # Add the community with the best ratio of edges added to nodes added. Repeat until we have >=
    # the target number of playables.
    communities = nx.algorithms.community.greedy_modularity_communities(card_pool_graph)
    while _num_nonlands(current_build) < _NONLANDS_IN_DECK_DEFAULT:
        current_graph = synergy.create_graph(current_build, remove_isolated=False)
        communities.sort(key=lambda c: _comm_score(current_graph, c), reverse=True)
        current_build.extend(communities.pop(0))

    # Cut least-central cards one by one until we're at the final number of playables
    current_build_graph = synergy.create_graph(current_build, remove_isolated=False, freeze=False)
    while _num_nonlands(current_build_graph.nodes) > _NONLANDS_IN_DECK_DEFAULT:
        centralities = synergy.sorted_centralities(current_build_graph)
        least_central_card = centralities[-1][0]
        current_build_graph.remove_node(least_central_card)

    # "Refine" build by trying out leftovers one by one and swapping with worst card if they improve the build
    current_build = list(current_build_graph.nodes)
    leftovers = [c for c in card_pool_graph.nodes if c not in current_build]
    current_build = _refine_build(current_build, leftovers)
    leftovers = [c for c in card_pool_graph.nodes if c not in current_build]

    # Replace splashed cards with non-splashed cards if we're over our limit
    if splash_colors:
        nonland_fixers_in_build = [c for c in current_build if c in nonland_fixers]
        num_fixers = len(nonland_fixers_in_build) + len(land_fixers)
        max_splash_cards = max(0, num_fixers - 4)

        current_splash_cards = [c for c in current_build if _splashed(c, splash_colors)]
        while len(current_splash_cards) > max_splash_cards:
            nonsplash_leftovers = [c for c in leftovers if not _splashed(c, splash_colors)]
            card_swap = _find_best_swap(current_build, candidates_to_add=nonsplash_leftovers,
                                        candidates_to_remove=current_splash_cards)

            if not card_swap.card_to_add:
                raise DeckbuildError('No build found for splashing {} (not enough fixers)'.format(splash_colors))

            current_build.remove(card_swap.card_to_remove)
            current_splash_cards.remove(card_swap.card_to_remove)
            current_build.append(card_swap.card_to_add)
            leftovers.remove(card_swap.card_to_add)

    final_build_colors = _colors_from_pool(current_build)
    final_fixer_lands = [c for c in land_fixers if _fixer_for_colors(c, final_build_colors)]

    return current_build + final_fixer_lands


def best_two_color_synergy_build(card_pool, build_fn=_communities_build):
    """Attempts to find the 2-color build of the given pool with the most synergy edges.

    Args:
        card_pool (List[Card]): The card pool to build.
        build_fn (function): A function which builds a deck, given a synergy graph for a 2-color subset
            of the total card pool.

    Returns:
        List[Card]: The best build found among all 2-color combinations for this pool.
    """

    candidates = []
    graph = synergy.create_graph(card_pool, remove_isolated=False)

    for colors in _COLOR_COMBOS:
        for main_colors in itertools.combinations(colors, 2):
            splash_colors = [c for c in colors if c not in main_colors]

            on_color_subgraph = graph.subgraph(_relevant_cards(card_pool, main_colors, splash_colors))

            try:
                deck_for_colors = build_fn(on_color_subgraph, main_colors, splash_colors)

                candidates.append((deck_for_colors, len(graph.subgraph(deck_for_colors).edges)))
            except DeckbuildError as e:
                print('Failed to build color combo {} splash {}, continuing. Reason: {}'
                      .format(main_colors, splash_colors, e))
                pass

    if not candidates:
        raise DeckbuildError('No build found')

    candidates.sort(key=lambda tup: tup[1:], reverse=True)
    return candidates[0][0]


def _splashed(card, splash_colors):
    return True if set(splash_colors).intersection(set(card.mana_cost)) else False


def _relevant_cards(card_pool, main_colors, splash_colors):
    colors = list(main_colors) + list(splash_colors)
    return [c for c in card_pool
            # on-color nonlands
            if synergy.castable(c, main_colors) and 'land' not in c.types or
            # splashable nonlands
            synergy.castable(c, colors) and _splashable(c, splash_colors) and 'land' not in c.types or
            # fixers and on-color utility lands
            'land' in c.types and (_fixer_for_colors(c, colors) or c.tags)]


def _fixer_for_colors(card, colors):
    # A fixer's colors don't have to overlap completely with your colors for it to help you, e.g.
    # a WUR land can help a UR deck or a URG deck. It helps as long as the size of the intersection > 1.
    return card.fixer_color_id and len(set(card.fixer_color_id) & set(colors)) > 1


def _splashable(card, splash_colors):
    # TODO: we could make this overridable through tags
    if 'creature' in card.types and _cmc(card) < 3:
        return False

    for s in splash_colors:
        if card.mana_cost.count(s) > 1:
            return False
    return True


def _cmc(card):
    generic_costs = [cost for cost in card.mana_cost if cost.isdigit()]
    color_costs = [cost for cost in card.mana_cost if not cost.isdigit()]

    generic_cmc = int(generic_costs[0]) if generic_costs else 0

    return len(color_costs) + generic_cmc


def _colors_from_pool(card_pool):
    # Get all symbols from all costs aside from generic costs
    all_symbols = set([s for s in itertools.chain(*[c.mana_cost for c in card_pool]) if not s.isdigit()])
    return ''.join(sorted(all_symbols))


class DeckbuildError(Exception):
    pass
