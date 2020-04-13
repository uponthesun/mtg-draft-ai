from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ... import models


# /api/draft/<int:draft_id>/seat/<int:seat>/waiting-for-drafters
def waiting_for_drafters(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=seat)

    return JsonResponse({
        'drafters': [{'seat': d.seat, 'name': d.name} for d in drafter.waiting_for_drafters()]
    })
