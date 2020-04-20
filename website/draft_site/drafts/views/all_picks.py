from django.shortcuts import render, get_object_or_404

from .constants import CUBES_BY_ID
from .. import models


# /draft/<int:draft_id>/seat/<int:seat>/all-picks
def all_picks(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=seat)
    cube_data = CUBES_BY_ID[draft.cube_id]

    picks, pack_history = _convert_drafter(drafter)
    picks_urls = [cube_data.get_image_url(name) for name in picks]
    pack_leftovers_urls = [[cube_data.get_image_url(name) for name in pack] for pack in pack_history]

    context = {
        'draft': draft,
        'drafter': drafter,
        'seat_range': range(0, draft.num_drafters),  # Used by header
        'picks_with_packs': zip(picks_urls, pack_leftovers_urls),
    }
    return render(request, 'drafts/all_picks.html', context)


# Helper functions below

def _convert_drafter(db_drafter):
    draft = db_drafter.draft
    drafters = models.Drafter.objects.filter(draft=draft)

    picks_table = []
    for d in drafters:
        picks = models.Card.objects.filter(draft=draft, picked_by=d)
        sorted_picks = sorted(picks, key=lambda c: (c.phase, c.picked_at))
        picks_table.append([c.name for c in sorted_picks])

    picks = []
    pack_leftovers = []
    for phase in range(0, draft.num_phases):
        direction = -1 if phase % 2 == 0 else 1

        for pick in range(0, draft.cards_per_pack):
            r = db_drafter.seat
            c = phase * draft.cards_per_pack + pick
            pack_contents = []

            for i in range(0, draft.cards_per_pack - pick):
                pack_contents.append(picks_table[r][c])
                r = (r + direction) % draft.num_drafters
                c += 1
            picks.append(pack_contents.pop(0))
            pack_leftovers.append(pack_contents)

    return picks, pack_leftovers
