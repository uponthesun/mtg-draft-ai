from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ... import models


# /api/draft/<int:draft_id>/seat/<int:seat>/waiting-for-drafters
def waiting_for_drafters(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=seat)

    human_drafters = drafter.draft.drafter_set.filter(bot=False)
    waiting_for_drafters = [{'seat': d.seat, 'name': d.name} for d in human_drafters
                            if d.current_phase < drafter.current_phase or
                            d.current_phase == drafter.current_phase and d.current_pick < drafter.current_pick]

    return JsonResponse({'drafters': waiting_for_drafters})
