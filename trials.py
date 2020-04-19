import argparse
from collections import namedtuple
import contextlib
import os
import statistics

from mtg_draft_ai.controller import *
from mtg_draft_ai.api import *
from mtg_draft_ai.brains import *
from mtg_draft_ai import draftlog, deckbuild, display


def main():
    parser = argparse.ArgumentParser(description='Run N full drafts + deckbuilds for each, with all logs saved.')
    parser.add_argument('n', type=int, help='Number of drafts to run')
    parser.add_argument('--card-data', type=str, help='Card data TOML file', default='cube_81183_tag_data.toml')
    parser.add_argument('--fixer-data', type=str, help='Fixer data TOML file', default='cube_81183_fixer_data.toml')
    parser.add_argument('-d', '--dir', type=str, help='Output directory for files', default='output')

    args = parser.parse_args()

    cube_list = read_cube_toml(args.card_data, args.fixer_data)
    draft_info = DraftInfo(card_list=cube_list, num_drafters=6, num_phases=3, cards_per_pack=15)
    #drafter_factory = SynergyPowerFixingPicker.factory(cube_list)
    drafter_factory = PowerFixingPicker.factory(cube_list)

    deck_metrics = []
    for i in range(0, args.n):
        deck_metrics += run_trial(name=i, output_dir=args.dir, draft_info=draft_info, drafter_factory=drafter_factory,
                                  deckbuild_fn=deckbuild.best_two_color_synergy_build)

    edge_counts = [dm.num_edges for dm in deck_metrics]
    avg_power_values = [dm.avg_power for dm in deck_metrics]

    print('Mean # of edges: {}'.format(statistics.mean(edge_counts)))
    print('Median # of edges: {}'.format(statistics.median(edge_counts)))
    print('Mean avg deck power: {}'.format(statistics.mean(avg_power_values)))
    print('Median avg deck power: {}'.format(statistics.median(avg_power_values)))


DeckMetrics = namedtuple('DeckMetrics', ['num_edges', 'avg_power'])


def run_trial(name, output_dir, draft_info, drafter_factory, deckbuild_fn):
    draft_log_file = os.path.join(output_dir, 'draft-log_{}.txt'.format(name))
    draft_html_file = os.path.join(output_dir, 'draft_{}.html'.format(name))
    draft_debug_file = os.path.join(output_dir, 'draft-debug_{}.txt'.format(name))
    build_html_file = os.path.join(output_dir, 'build_{}.html'.format(name))
    build_debug_file = os.path.join(output_dir, 'build-debug_{}.txt'.format(name))

    drafters = [Drafter(drafter_factory.create(), draft_info) for _ in range(0, draft_info.num_drafters)]

    # Run draft, redirecting output to debug file
    with open(draft_debug_file, 'w') as f:
        with contextlib.redirect_stdout(f):
            controller = DraftController.create(draft_info, drafters)
            controller.run_draft()

            print('\n\nFinal state:')
            for drafter in drafters:
                print('{}\n'.format(drafter))

    # Write draft log - toml file recording all picks in draft
    with open(draft_log_file, 'w') as f:
        f.write(draftlog.dumps_log(drafters, draft_info))
    print('Draft log written to {}'.format(draft_log_file))

    # Write draft.html - HTML display of full draft from every seat
    html = draftlog.log_to_html(draft_log_file)
    with open(draft_html_file, 'w') as f:
        f.write(html)
    print('Draft HTML written to {}'.format(draft_html_file))

    # Run deckbuild, redirecting output to debug file
    with open(build_debug_file, 'w') as f:
        with contextlib.redirect_stdout(f):
            #decks = [deckbuild_fn(d.cards_owned) for d in drafters]
            decks = [d.cards_owned for d in drafters]

    # Write build.html - HTML display of final built decks for every seat
    with open(build_html_file, 'w') as f:
        f.write(decks_to_html(decks))
    print('Build HTML written to {}'.format(build_html_file))

    # Return # of edges in each deck
    return [DeckMetrics(num_edges=edges_in_deck(d), avg_power=avg_power(d)) for d in decks]


def edges_in_deck(deck):
    deck_graph = synergy.create_graph(deck)
    return len(deck_graph.edges)


def avg_power(deck):
    return statistics.mean([power_rating(card) for card in deck
                            if 'land' not in card.types])


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


if __name__ == '__main__':
    main()
