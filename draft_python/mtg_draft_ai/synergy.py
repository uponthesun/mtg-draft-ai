import networkx as nx


def create_graph(cards):
    G = nx.Graph()
    G.add_nodes_from(cards)

    bp_graphs = {}

    for card in cards:
        for theme, role in card.tags:
            bp_graphs.setdefault(theme, {})
            bp_graphs[theme].setdefault(role, set()).add(card)

    for theme, roles in bp_graphs.items():
        partitions = list(roles.values())
        if len(partitions) != 2:
            raise ValueError('Enabler/Payoff is only tagging scheme supported currently')

        for card_1 in partitions[0]:
            for card_2 in partitions[1]:
                if card_1 != card_2:
                    G.add_edge(card_1, card_2)

    G.remove_nodes_from(list(nx.isolates(G)))
    return nx.freeze(G)


def colors_subgraph(graph, colors):
    on_color = [card for card in graph.nodes if _castable(card.color_id, colors)]
    return graph.subgraph(on_color)


def sorted_centralities(graph, centrality_measure=nx.eigenvector_centrality):
    centralities = centrality_measure(graph)
    return _sort_dict_by_values(centralities, reverse=True)


def _castable(color_id, colors):
    return set(color_id).issubset(set(colors)) or color_id == 'C'


# sorts items in a dictionary by their values
def _sort_dict_by_values(d, reverse=False):
    return sorted(list(d.items()), key=lambda tup: tup[1], reverse=reverse)
