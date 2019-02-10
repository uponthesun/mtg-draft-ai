import itertools
from mtg_draft_ai import synergy
from networkx.algorithms import community


_NONLANDS_IN_DECK = 23
_CORE_MINIMUM = 17


def build(card_pool_graph):
    card_pool = list(card_pool_graph.nodes)

    top_comms = _top_comms(card_pool_graph, 10)
    core = _build_core(card_pool_graph, top_comms)
    print('Core size: {} Core: {}'.format(len(core), core))

    remaining_cards = card_pool.copy()
    for card in core:
        remaining_cards.remove(card)

    return _brute_force_build(card_pool_graph, core, remaining_cards)


def best_two_color_build(card_pool, build_fn=build):
    print('\nBuilding pool: {}'.format([c.name for c in card_pool]))

    candidates = []
    graph = synergy.create_graph(card_pool)

    for colors in ['WU', 'WB', 'WR', 'WG', 'UB', 'UR', 'UG', 'BR', 'BG', 'RG']:
        try:
            on_color = [c for c in card_pool if synergy.castable(c, colors)]
            on_color_subgraph = graph.subgraph(on_color)
            deck_for_colors = build_fn(on_color_subgraph)

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


def _brute_force_build(graph, core, remaining_cards):
    num_needed = _NONLANDS_IN_DECK - len(core)
    if num_needed > len(remaining_cards):
        raise DeckbuildError('Need {} more cards, but only {} remaining'
                             .format(num_needed, len(remaining_cards)))

    best_build = []
    max_edges = 0
    for combo in itertools.combinations(remaining_cards, num_needed):
        potential_build = core + list(combo)
        subgraph = graph.subgraph(potential_build)
        if len(subgraph.edges) > max_edges:
            best_build, max_edges = potential_build, len(subgraph.edges)

    return best_build


def _build_core(graph, top_comms):
    top_comm_combo = None
    top_density = None

    for combo in _powerset(top_comms):
        cards_in_combo = list(itertools.chain(*combo))
        num_cards = len(cards_in_combo)

        if num_cards < _CORE_MINIMUM:
            continue

        combo_subgraph = graph.subgraph(cards_in_combo)
        if num_cards > _NONLANDS_IN_DECK:
            ranked_cards = synergy.sorted_centralities(combo_subgraph)
            cards_in_combo = [tup[0] for tup in ranked_cards[:_NONLANDS_IN_DECK]]
            combo_subgraph = graph.subgraph(cards_in_combo)

        density = len(combo_subgraph.edges) / len(cards_in_combo)
        if top_comm_combo is None or density > top_density:
            top_comm_combo, top_density = cards_in_combo, density

    if top_comm_combo is None:
        raise DeckbuildError('Unable to build a deck core of between {} and {} cards'
                             .format(_CORE_MINIMUM, _NONLANDS_IN_DECK))

    return top_comm_combo


def _top_comms(graph, n=10):
    if len(graph.nodes) == 0 or len(graph.edges) == 0:
        return []

    comms = [c for c in community.greedy_modularity_communities(graph)
             if len(c) > 1]
    comms.sort(key=lambda c: len(graph.subgraph(c).edges) / len(c), reverse=True)
    return comms[:n]


def _powerset(iterable):
    """"powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)

    Taken directly from: https://docs.python.org/3/library/itertools.html
    """
    s = list(iterable)
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s)+1))
