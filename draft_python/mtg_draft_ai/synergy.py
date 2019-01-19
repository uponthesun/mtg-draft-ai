"""Synergy graph creation and analysis."""

import networkx as nx


def create_graph(cards):
    """Creates a synergy graph for the given list of card objects.

    Each card is a node, and two cards are connected by an edge if one tagged as an Enabler and
    one is tagged as a Payoff for the same theme. Example tag:
    Lifegain - Enabler
    Lifegain - Payoff

    Args:
        cards (list of api.Card): list of cards to use as nodes in the graph.

    Returns:
        NetworkX graph object representing the synergy graph.
    """
    G = nx.Graph()
    G.add_nodes_from(cards)

    bp_graphs = {}

    for card in cards:
        for theme, role in card.tags:
            bp_graphs.setdefault(theme, {})
            bp_graphs[theme].setdefault(role, set()).add(card)

    for theme, roles in bp_graphs.items():
        partitions = list(roles.values())
        if len(partitions) > 2:
            raise ValueError('Enabler/Payoff is only tagging scheme supported currently')
        elif len(partitions) < 2:
            continue

        for card_1 in partitions[0]:
            for card_2 in partitions[1]:
                if card_1 != card_2:
                    G.add_edge(card_1, card_2)

    G.remove_nodes_from(list(nx.isolates(G)))
    return nx.freeze(G)


def colors_subgraph(graph, colors):
    """Creates a subgraph containing only cards castable with the given colors.

    Includes colorless cards.

    Args:
        graph (networkx.Graph): The graph to create a subgraph from.
        colors (str): String representation of the available colors of mana, e.g. 'RG' or 'UWR'.

    Returns:
        The subgraph of cards castable using only those colors of mana.
    """
    on_color = [card for card in graph.nodes if _castable(card.color_id, colors)]
    return graph.subgraph(on_color)


def sorted_centralities(graph, centrality_measure=nx.eigenvector_centrality):
    """Computes centralities for all nodes of a graph and returns them sorted highest to lowest.

    A centrality measure is a way to measure the importance of a node in a graph.
    Defaults to NetworkX's eigenvector centrality implementation; any NetworkX centrality
    function can be provided instead.

    Args:
        graph (networkx.Graph): The graph to compute centralities for.
        centrality_measure (fn): A function which computes centrality for all nodes of the graph.

    Returns:
        list of (api.Card, float): Tuples of (card, centrality) sorted by centrality
    """
    centralities = centrality_measure(graph)
    return _sort_dict_by_values(centralities, reverse=True)


def _castable(color_id, colors):
    return set(color_id).issubset(set(colors)) or color_id == 'C'


# sorts items in a dictionary by their values
def _sort_dict_by_values(d, reverse=False):
    return sorted(list(d.items()), key=lambda tup: tup[1], reverse=reverse)
