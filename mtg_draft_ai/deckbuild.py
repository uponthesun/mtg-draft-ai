"""Deckbuilding functions."""

from mtg_draft_ai import synergy
import networkx as nx


_NONLANDS_IN_DECK_DEFAULT = 23

_COLOR_COMBOS = ['WU', 'WB', 'WR', 'WG', 'UB', 'UR', 'UG', 'BR', 'BG', 'RG']

def _comm_score(current_graph, comm):
    build_with_comm = list(current_graph.nodes) + list(comm)
    graph_with_comm = synergy.create_graph(build_with_comm, remove_isolated=False)
    edges_added = len(graph_with_comm.edges) - len(current_graph.edges)
    return edges_added / len(comm)


def _num_nonlands(current_build):
    return len([c for c in current_build if 'land' not in c.types])


def _communities_build(card_pool_graph, target_playables):
    """Builds a deck by trying combinations of communities. Ignores all other factors (including color).

    Outline of algorithm:

    1). Split the on-color cards into communities using networkx's greedy_modular_communities
    2). Find the "best" community to add based on # of edges it would add / # nodes
    3). Add the entire community to the pool
    4). Repeat 2-3 until we have >= the target number of playables
    5). Cut cards one by one based on lowest centrality score in the graph for the pool
    until we have the target number of playables

    Args:
        card_pool_graph (networkx.Graph): A synergy graph of Cards as the card pool to build from.
        target_playables (int): The number of nonland cards to include in the deck. Utility lands can still be
            included if they are beneficial, but don't count towards this total.

    Returns:
        List[Card]: The build for the given pool pool of cards.
    """
    if _num_nonlands(card_pool_graph.nodes) < target_playables:
        raise DeckbuildError('Not enough nonland cards')

    communities = nx.algorithms.community.greedy_modularity_communities(card_pool_graph)

    # Add the community with the best ratio of edges added to nodes added. Repeat until we have >=
    # the target number of playables.
    current_build = []
    while _num_nonlands(current_build) < target_playables:
        current_graph = synergy.create_graph(current_build, remove_isolated=False)
        communities.sort(key=lambda c: _comm_score(current_graph, c), reverse=True)
        current_build.extend(communities.pop(0))

    current_build_graph = synergy.create_graph(current_build, remove_isolated=False, freeze=False)

    # Cut least-central cards one by one until we're at the final number of playables
    while _num_nonlands(current_build_graph.nodes) > target_playables:
        centralities = synergy.sorted_centralities(current_build_graph)
        least_central_card = centralities[-1][0]
        current_build_graph.remove_node(least_central_card)

    return list(current_build_graph.nodes)


def _centralities_build(card_pool_graph, target_playables):
    """Builds a deck by taking the top N most central cards. Ignores all other factors (including color).

    Args:
        card_pool_graph (networkx.Graph): A synergy graph of Cards as the card pool to build from.
        target_playables (int): The number of nonland cards to include in the deck. Utility lands can still be
            included if they are beneficial, but don't count towards this total.

    Returns:
        List[Card]: The build for the given pool pool of cards.
    """
    if len(card_pool_graph.nodes) < target_playables:
        raise DeckbuildError('Not enough cards')

    ranked_cards = synergy.sorted_centralities(card_pool_graph)
    centrality_build = [tup[0] for tup in ranked_cards[:target_playables]]
    return centrality_build


def best_two_color_synergy_build(card_pool, build_fn=_communities_build):
    """Attempts to find the 2-color build of the given pool with the most synergy edges.

    Args:
        card_pool (List[Card]): The card pool to build.
        build_fn (function): A function which builds a deck, given a synergy graph for a 2-color subset
            of the total card pool.

    Returns:
        List[Card]: The best build found among all 2-color combinations for this pool.
    """

    print('\nBuilding pool: {}'.format([c.name for c in card_pool]))

    # By default we aim for 23 nonland playables, but if no color combo has enough, we instead
    # aim for whatever the highest number is among all color combos.
    max_num_playables = 0
    for colors in _COLOR_COMBOS:
        on_color = [c for c in card_pool if synergy.castable(c, colors)]
        num_nonlands = _num_nonlands(on_color)
        if num_nonlands > max_num_playables:
            max_num_playables = num_nonlands
    target_num_playables = min(max_num_playables, _NONLANDS_IN_DECK_DEFAULT)

    candidates = []
    graph = synergy.create_graph(card_pool, remove_isolated=False)

    for colors in _COLOR_COMBOS:
        try:
            # We include utility lands in the graph since they should affect card choices.
            on_color_with_utility_lands = [c for c in card_pool
                        if synergy.castable(c, colors) and not ('land' in c.types and not c.tags)]
            on_color_subgraph = graph.subgraph(on_color_with_utility_lands)
            deck_for_colors = build_fn(on_color_subgraph, target_num_playables)
            deck_subgraph = graph.subgraph(deck_for_colors)

            candidates.append((deck_for_colors, len(deck_subgraph.edges)))
        except DeckbuildError as e:
            print('Failed to build color combo {}, continuing. Reason: {}'.format(colors, e))
            pass

    if not candidates:
        raise DeckbuildError('No build found')

    candidates.sort(key=lambda tup: tup[1:], reverse=True)
    printable_candidates = [([c.name for c in tup[0]], *tup[1:]) for tup in candidates]
    print('Deck candidates:')
    print('\n'.join([str(pc) for pc in printable_candidates]))

    return candidates[0][0]


class DeckbuildError(Exception):
    pass
