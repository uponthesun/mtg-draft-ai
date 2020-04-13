import sys
from collections import namedtuple
from mtg_draft_ai import draftlog, deckbuild, display, synergy
from mtg_draft_ai.api import read_cube_toml
from mtg_draft_ai.brains import *
import contextlib
import os
import statistics


#log_file = sys.argv[1]
#output_file = 'output/build.html' if len(sys.argv) < 3 else sys.argv[2]

cube_list = read_cube_toml('cube_81183_tag_data.toml')
#drafters = draftlog.load_drafters_from_log(log_file, card_list=cube_list)

output_dir = 'output/build_trials/refined_cent'
num_trials = 100

DeckMetrics = namedtuple('DeckMetrics', ['num_edges', 'avg_power'])


def edges_in_deck(deck):
    deck_graph = synergy.create_graph(deck)
    return len(deck_graph.edges)


def avg_power(deck):
    return statistics.mean([GreedyPowerAndSynergyPicker._power_rating(card) for card in deck])


def decks_to_html(decks):
    html = display.default_style()

    i = 0
    for deck in decks:
        deck_graph = synergy.create_graph(deck, remove_isolated=False)
        sorted_deck = [tup[0] for tup in synergy.sorted_centralities(deck_graph)]

        html += 'Deck {} - # Edges: {} \n'.format(i, len(deck_graph.edges))
        html += '<div>\n{}</div>\n'.format(display.cards_to_html(sorted_deck))
        i += 1

    return html


deck_metrics = []


for i in range(0, num_trials):
    log_file = 'output/draft-log_{}.txt'.format(i)
    build_html_file = os.path.join(output_dir, 'build_{}.html'.format(i))
    build_debug_file = os.path.join(output_dir, 'build-debug_{}.txt'.format(i))

    drafters = draftlog.load_drafters_from_log(log_file, card_list=cube_list)

    # Run deckbuild, redirecting output to debug file
    with open(build_debug_file, 'w') as f:
        with contextlib.redirect_stdout(f):
            decks = [deckbuild.best_two_color_synergy_build(d.cards_owned) for d in drafters]

    # Write build.html - HTML display of final built decks for every seat
    with open(build_html_file, 'w') as f:
        f.write(decks_to_html(decks))
    print('Build HTML written to {}'.format(build_html_file))

    # Return # of edges in each deck
    deck_metrics += [DeckMetrics(num_edges=edges_in_deck(d), avg_power=avg_power(d)) for d in decks]


edge_counts = [dm.num_edges for dm in deck_metrics]
avg_power_values = [dm.avg_power for dm in deck_metrics]

print('Mean # of edges: {}'.format(statistics.mean(edge_counts)))
print('Median # of edges: {}'.format(statistics.median(edge_counts)))
print('Mean avg deck power: {}'.format(statistics.mean(avg_power_values)))
print('Median avg deck power: {}'.format(statistics.median(avg_power_values)))
