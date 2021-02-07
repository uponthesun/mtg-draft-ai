import statistics

from django.shortcuts import render, get_object_or_404

from .. import models
from ..constants import CUBES_BY_ID
from .. import deck_export
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
    # TODO: fix interface
    avg_power = statistics.mean([power_rating(c) for c in built_deck
                                 if 'land' not in c.types])

    context = {
        'draft': draft,
        'drafter': drafter,
        'seat_range': range(0, draft.num_drafters),  # Used by header
        'built_deck_images': [cube_data.get_image_urls(c.name) for c in built_deck],
        'leftovers_images': [cube_data.get_image_urls(c.name) for c in leftovers],
        'num_edges': len(deck_graph.edges),
        'avg_power': round(avg_power, 2),
    }

    deck_exports_context = {
        'cockatrice_export': deck_export.cockatrice(built_deck, leftovers),
        'encoded_deckbuild_ui_export': deck_export.deckbuild_ui(built_deck, leftovers, cube_data, encoded=True),
        'textarea_rows': len(pool) + 1,
    }
    return render(request, 'drafts/auto_build.html', {**context, **deck_exports_context})
