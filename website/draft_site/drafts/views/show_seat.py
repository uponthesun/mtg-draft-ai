from django.shortcuts import render, get_object_or_404

from .. import models
from .constants import CUBES_BY_ID


# /draft/<int:draft_id>/seat/<int:seat>
def show_seat(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=seat)
    cube_data = CUBES_BY_ID[draft.cube_id]

    basic_context = {
        'draft': draft,
        'drafter': drafter,
        'seat_range': range(0, draft.num_drafters),  # Used by header
        'waiting_for_drafters': drafter.waiting_for_drafters(),
        #'waiting': drafter.current_pack() is None,
        'draft_complete': (drafter.current_phase == draft.num_phases),
        'autobuild_enabled': cube_data.autobuild_enabled
    }

    current_pack = drafter.current_pack() or []
    sorted_owned_cards = sorted(drafter.owned_cards(), key=lambda c: (c.phase, c.picked_at))
    # Generate bot recommendations
    bot_ratings = _get_bot_ratings(draft, current_pack, sorted_owned_cards)
    component_keys = list(bot_ratings[0].components.keys()) if len(bot_ratings) > 0 else []
    bot_ratings_column_names = ['Name', 'Rating', 'Colors'] + component_keys
    bot_ratings_table = [[r.card.name, r.rating, r.color_combo] + [r.components[k] for k in component_keys]
                         for r in bot_ratings]

    current_pack_context = {
        'cards': [(c, cube_data.get_image_url(c.name)) for c in current_pack],
        'owned_cards': [(c, cube_data.get_image_url(c.name)) for c in sorted_owned_cards],
        'bot_ratings_column_names': bot_ratings_column_names,
        'bot_ratings_table': bot_ratings_table,
    }

    return render(request, 'drafts/show_seat.html', {**basic_context, **current_pack_context})


def _get_bot_ratings(draft, current_pack, owned_cards):
    cube_data = CUBES_BY_ID[draft.cube_id]

    pack_converted = [cube_data.card_by_name(c.name) for c in current_pack]
    owned_converted = [cube_data.card_by_name(c.name) for c in owned_cards]
    draft_info = draft.to_draft_info(cube_data.cards)
    # TODO: fix interface for getting ratings
    return cube_data.picker_factory.create().ratings(pack_converted, owned_converted, draft_info)
