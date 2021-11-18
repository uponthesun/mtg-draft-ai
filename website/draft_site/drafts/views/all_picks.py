from django.shortcuts import render, get_object_or_404

from ..constants import CUBES_BY_ID
from .. import models


# /draft/<int:draft_id>/seat/<int:seat>/all-picks
def all_picks(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=seat)
    cube_data = CUBES_BY_ID[draft.cube_id]

    picks, pack_history = _convert_drafter(drafter)
    picks_urls = [cube_data.get_image_urls(c.name) for c in picks]
    pack_leftovers_urls = [[cube_data.get_image_urls(c.name) for c in pack] for pack in pack_history]

    context = {
        'draft': draft,
        'drafter': drafter,
        'cube_name': cube_data.name,
        'cubecobra_url': cube_data.cubecobra_url,
        'seat_range': range(0, draft.num_drafters),  # Used by header
        'picks_with_packs': zip(picks_urls, pack_leftovers_urls),
    }
    return render(request, 'drafts/all_picks.html', context)


# Helper functions below

def _convert_drafter(drafter):
    draft = drafter.draft

    picks = sorted(drafter.owned_cards(), key=lambda c: (c.phase, c.picked_at))
    pack_leftovers = []
    for phase in range(0, drafter.current_phase + 1):
        pick_range_end = drafter.current_pick if drafter.current_phase == phase else draft.cards_per_pack
        for pick in range(0, pick_range_end):
            direction = -1 if phase % 2 == 0 else 1
            pack_index = (drafter.seat - pick * direction) % draft.num_drafters
            original_pack = draft.card_set.filter(phase=phase, start_seat=pack_index)

            pack_at_that_time = [c for c in original_pack if c.picked_at is None or c.picked_at >= pick]
            pick_from_pack = picks[phase * draft.cards_per_pack + pick]
            leftovers = [c for c in pack_at_that_time if c.name != pick_from_pack.name]
            pack_leftovers.append(leftovers)

    return picks, pack_leftovers
