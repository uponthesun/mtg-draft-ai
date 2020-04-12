from django.shortcuts import render, get_object_or_404

from .. import models
from .constants import CUBE_DATA, PICKER_FACTORY


# /draft/<int:draft_id>/seat/<int:seat>
def show_seat(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=seat)

    current_pack = drafter.current_pack()
    sorted_owned_cards = sorted(drafter.owned_cards(), key=lambda c: (c.phase, c.picked_at))

    # Generate bot recommendations
    bot_ratings = _get_bot_ratings(draft, current_pack, sorted_owned_cards)

    # Are we waiting on any picks?
    waiting_for_drafters = _get_humans_who_need_to_pick(drafter)

    context = {
        'draft': draft,
        'drafter': drafter,
        'seat_range': range(0, draft.num_drafters),  # Used by header
        'cards': [(c, CUBE_DATA.get_image_url(c.name)) for c in current_pack],
        'owned_cards': [(c, CUBE_DATA.get_image_url(c.name)) for c in sorted_owned_cards],
        'bot_ratings': bot_ratings,
        'waiting_for_drafters': waiting_for_drafters,
        'draft_complete': (drafter.current_phase == draft.num_phases),
    }

    return render(request, 'drafts/show_pack.html', context)


def _get_humans_who_need_to_pick(drafter):
    human_drafters = drafter.draft.drafter_set.filter(bot=False)
    return [d for d in human_drafters
            if d.current_phase < drafter.current_phase or
            d.current_phase == drafter.current_phase and d.current_pick < drafter.current_pick]


def _get_bot_ratings(draft, current_pack, owned_cards):
    pack_converted = [CUBE_DATA.card_by_name(c.name) for c in current_pack]
    owned_converted = [CUBE_DATA.card_by_name(c.name) for c in owned_cards]
    draft_info = draft.to_draft_info(CUBE_DATA.cards)
    # TODO: fix interface for getting ratings
    return PICKER_FACTORY.create()._get_ratings(pack_converted, owned_converted, draft_info)
