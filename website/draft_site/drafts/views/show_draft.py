from django.shortcuts import render, get_object_or_404

from .. import models
from ..constants import CUBES_BY_ID


# /draft/<int:draft_id>
def show_draft(request, draft_id):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafters = draft.drafter_set.all()
    cube_name = CUBES_BY_ID[draft.cube_id].name

    context = {
        'human_drafters': [d for d in drafters if not d.bot],
        'num_bots': len([d for d in drafters if d.bot]),
        'draft': draft,
        'cube_name': cube_name
    }
    return render(request, 'drafts/show_draft.html', context)
