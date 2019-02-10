from mtg_draft_ai import synergy


_NONLANDS_IN_DECK = 23
_CORE_MINIMUM = 17


def centralities_build(card_pool_graph):
    if len(card_pool_graph.nodes) < _NONLANDS_IN_DECK:
        raise DeckbuildError('Not enough cards')

    ranked_cards = synergy.sorted_centralities(card_pool_graph)
    centrality_build = [tup[0] for tup in ranked_cards[:_NONLANDS_IN_DECK]]
    return card_pool_graph.subgraph(centrality_build)


def best_two_color_build(card_pool, build_fn=centralities_build):
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
