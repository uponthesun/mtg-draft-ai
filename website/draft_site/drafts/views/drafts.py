from django.shortcuts import render

from .. import models
from ..constants import CUBES_BY_ID


# /drafts
def drafts(request):
    all_drafts = sorted(models.Draft.objects.order_by('-id')[:100], key=lambda d: d.id, reverse=True)
    human_drafters_by_draft_id = {}
    for drafter in models.Drafter.objects.filter(draft_id__in=[draft.id for draft in all_drafts], bot=False):
        human_drafters_by_draft_id.setdefault(drafter.draft_id, [])
        human_drafters_by_draft_id[drafter.draft_id].append(drafter)

    drafts_table = [(draft, CUBES_BY_ID[draft.cube_id].name, ', '.join([h.name for h in human_drafters_by_draft_id[draft.id]]))
                    for draft in all_drafts]

    return render(request, 'drafts/drafts.html', {'drafts_table': drafts_table})
