import itertools
from mtg_draft_ai import synergy
from networkx.algorithms import community


_NONLANDS_IN_DECK = 23
_CORE_MINIMUM = 17


def best_two_color_build(card_pool):
    print('\nBuilding pool: {}'.format([c.name for c in card_pool]))

    candidates = []
    graph = synergy.create_graph(card_pool)

    for colors in ['WU', 'WB', 'WR', 'WG', 'UB', 'UR', 'UG', 'BR', 'BG', 'RG']:
        try:
            build_for_colors = build(card_pool, colors)
            subgraph = graph.subgraph(build_for_colors)
            candidates.append((build_for_colors, len(subgraph.edges)))
        except DeckbuildError as e:
            pass

    if not candidates:
        raise DeckbuildError('No build found')

    candidates.sort(key=lambda tup: tup[1:], reverse=True)
    printable_candidates = [([c.name for c in tup[0]], *tup[1:]) for tup in candidates]
    print('Deck candidates:')
    print('\n'.join([str(pc) for pc in printable_candidates]))

    return candidates[0][0]


def build(card_pool, colors=None):
    print('Building {}'.format(colors))
    if colors:
        card_pool = [c for c in card_pool if synergy.castable(c, colors)]

    G = synergy.create_graph(card_pool)

    top_comms = _top_comms(G, 10)
    core = _build_core(G, top_comms)

    remaining_cards = card_pool.copy()
    for card in core:
        remaining_cards.remove(card)

    return _brute_force_build(G, core, remaining_cards)


class DeckbuildError(Exception):
    pass


def _brute_force_build(graph, core, remaining_cards):
    num_needed = _NONLANDS_IN_DECK - len(core)
    if num_needed > len(remaining_cards):
        raise DeckbuildError('Need {} more cards, but only {} remaining'
                             .format(num_needed, len(remaining_cards)))

    best_build = ([], 0)
    for combo in itertools.combinations(remaining_cards, num_needed):
        potential_build = core + list(combo)
        subgraph = graph.subgraph(potential_build)
        rated_build = (potential_build, len(subgraph.edges))

        if rated_build[1:] > best_build[1:]:
            best_build = rated_build

    return best_build[0]


def _build_core(graph, top_comms):
    top_comm_combo = None

    for combo in _powerset(top_comms):
        cards_in_combo = list(itertools.chain(*combo))
        num_cards = len(cards_in_combo)

        if _CORE_MINIMUM <= num_cards <= _NONLANDS_IN_DECK:
            density = len(graph.subgraph(cards_in_combo).edges) / len(cards_in_combo)
            if top_comm_combo is None or density > top_comm_combo[1]:
                top_comm_combo = (combo, density)

    if top_comm_combo is None:
        raise DeckbuildError('Unable to build a deck core of between {} and {} cards'
                             .format(_CORE_MINIMUM, _NONLANDS_IN_DECK))

    return list(itertools.chain(*top_comm_combo[0]))


def _top_comms(graph, n=10):
    if len(graph.nodes) == 0:
        return []

    comms = [c for c in community.greedy_modularity_communities(graph)
             if len(c) > 1]
    comms_by_density = [(len(graph.subgraph(c).edges) / len(c), c) for c in comms]
    comms_by_density.sort(reverse=True)

    return [tup[1] for tup in comms_by_density[:n]]


def _powerset(iterable):
    """"powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"""
    s = list(iterable)
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s)+1))
