from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ... import models


# /draft/<int:draft_id>/queued_packs
def queued_packs(request, draft_id):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafters = sorted(draft.drafter_set.all(), key=lambda d: d.seat)

    result = []

    for i in range(0, len(drafters)):
        drafter = drafters[i]
        # Use array indices instead of calling drafter._receiving_from to avoid extra queries
        receiving_from = drafters[(i - drafter.direction()) % len(drafters)]

        # TODO: simplify
        if receiving_from.current_phase == drafter.current_phase:
            receiving_from_current_pick = receiving_from.current_pick
        elif receiving_from.current_phase > drafter.current_phase:
            receiving_from_current_pick = draft.cards_per_pack
        else:
            receiving_from_current_pick = -1

        queued_packs_for_drafter = (receiving_from_current_pick - drafter.current_pick) + 1
        result.append({'seat': drafter.seat, 'name': drafter.name, 'queued_packs': queued_packs_for_drafter})

    return JsonResponse({'drafters': result})
