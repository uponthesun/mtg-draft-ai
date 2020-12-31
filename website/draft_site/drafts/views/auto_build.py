import statistics

from django.shortcuts import render, get_object_or_404

from .. import models
from ..constants import CUBES_BY_ID
from mtg_draft_ai.brains import power_rating
from mtg_draft_ai.deckbuild import best_two_color_synergy_build
from mtg_draft_ai import synergy


# /draft/<int:draft_id>/seat/<int:seat>/auto-build
def auto_build(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=seat)
    cube_data = CUBES_BY_ID[draft.cube_id]

    # Convert from DB objects to Card objects with metadata
    pool = [cube_data.card_by_name(c.name) for c in drafter.owned_cards()]

    built_deck = best_two_color_synergy_build(pool)
    deck_graph = synergy.create_graph(built_deck, remove_isolated=False)
    leftovers = [c for c in pool if c not in built_deck]
    power_ratings = [power_rating(c) for c in built_deck if 'land' not in c.types]

    context = {
        'draft': draft,
        'drafter': drafter,
        'seat_range': range(0, draft.num_drafters),  # Used by header
        'built_deck_images': [cube_data.get_image_url(c.name) for c in built_deck],
        'leftovers_images': [cube_data.get_image_url(c.name) for c in leftovers],
        'num_edges': len(deck_graph.edges),
        'avg_power': round(statistics.mean(power_ratings), 2),
        'power_histogram': _card_power_histogram(power_ratings),
    }

    deck_exports_context = {
        'deck_card_names': [(c.name, cube_data.card_by_name(c.name).card_set) for c in built_deck],
        'leftovers_card_names': [(c.name, cube_data.card_by_name(c.name).card_set) for c in leftovers],
        'textarea_rows': len(pool) + 1,
    }
    return render(request, 'drafts/auto_build.html', {**context, **deck_exports_context})


def _card_power_histogram(power_ratings):
    """Return a list of (rating, frequency) pairs, sorted by rating in descending order."""
    histogram = {}
    for rating in power_ratings:
        histogram.setdefault(rating, 0)
        histogram[rating] += 1

    return sorted(histogram.items(), reverse=True)
