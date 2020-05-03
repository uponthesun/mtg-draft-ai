from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ... import models


# /draft/<int:draft_id>/seat/<int:seat>/is-pack-available
def is_pack_available(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=seat)

    return JsonResponse({
        'available': drafter.current_pack() is not None
    })
