from django.shortcuts import render, get_object_or_404

from .. import models

from mtg_draft_ai.api import Drafter
from mtg_draft_ai.draftlog import drafters_to_html


# /draft/<int:draft_id>/seat/<int:seat>/all-picks
def all_picks(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=seat)

    output = _convert_drafter(drafter)

    context = {
        'draft': draft,
        'drafter': drafter,
        'seat_range': range(0, draft.num_drafters),  # Used by header
        'output': output,
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
    cards_owned = picks_table[db_drafter.seat]

    pack_history = []
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
            pack_history.append(pack_contents)

    result = Drafter(None, None)
    result.cards_owned = cards_owned
    result.pack_history = pack_history

    return drafters_to_html([result], headers=False)
