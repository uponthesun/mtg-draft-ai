import os
import pytest
from mtg_draft_ai.synergy import *
from mtg_draft_ai.api import *


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


# Cards:
# Abzan Battle Priest, Ajani's Pridemate, Blood Artist, Stromkirk Condemned,
# Azorius Signet, Lightning Helix, Call to the Feast
@pytest.fixture
def cards():
    file_path = os.path.join(TEST_DATA_DIR, 'test_synergy_cards.toml')
    return read_cube_toml(file_path)


@pytest.fixture
def graph(cards):
    return create_graph(cards)


def test_create_graph(graph):
    node_names = [card.name for card in graph.nodes]
    # Nodes with no edges aren't in the graph
    assert node_names == ['Abzan Battle Priest', "Ajani's Pridemate", 'Blood Artist', 'Stromkirk Condemned',
                          'Lightning Helix', 'Call to the Feast']

    priest, pridemate, artist, stromkirk, helix, call = graph.nodes
    assert set(graph.edges) == {(priest, pridemate), (pridemate, artist), (pridemate, helix), (pridemate, call),
                                (artist, stromkirk), (stromkirk, call)}


def test_colors_subgraph(graph):
    subgraph = colors_subgraph(graph, 'WB')
    node_names = [card.name for card in subgraph.nodes]
    # Nodes with no edges aren't in the graph
    assert node_names == ['Abzan Battle Priest', "Ajani's Pridemate", 'Blood Artist', 'Stromkirk Condemned',
                          'Call to the Feast']

    priest, pridemate, artist, stromkirk, call = subgraph.nodes
    assert set(subgraph.edges) == {(priest, pridemate), (pridemate, artist), (pridemate, call),
                                   (artist, stromkirk), (stromkirk, call)}


def test_sorted_centralities(graph):
    centralities = sorted_centralities(graph)
    cards = [tup[0] for tup in centralities]
    values = [tup[1] for tup in centralities]

    for card in cards:
        assert card in graph.nodes

    assert sorted(values, reverse=True) == values
