import logging
import pickle

from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import transaction

from .constants import CUBES_BY_ID
from .. import models

LOGGER = logging.getLogger(__name__)


class StaleReadError(Exception):
    pass


# /draft/<int:draft_id>/pick-card
def pick_card(request, draft_id):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=request.POST['seat'])
    picked_card = get_object_or_404(models.Card, id=request.POST['picked_card_id'])
    # We use the phase and pick from the POST data to prevent making two picks by submitting multiple times.
    phase = int(request.POST['phase'])
    pick = int(request.POST['pick'])

    try:
        with transaction.atomic():
            drafter.make_pick(picked_card, phase, pick)

            _make_bot_picks(drafter, phase, pick)
    except StaleReadError:
        LOGGER.info('Stale read occurred when picking card, transaction was rolled back')

    return HttpResponseRedirect(reverse('show_seat', kwargs={'draft_id': draft_id, 'seat': request.POST['seat']}))


# Helper functions below

def _make_bot_picks(human_drafter, phase, pick):
    draft = human_drafter.draft

    cube_data = CUBES_BY_ID[draft.cube_id]

    next_drafter = human_drafter.receiving_from()

    while next_drafter.bot and next_drafter.current_pack() is not None:
        db_pack = next_drafter.current_pack()
        pack = [cube_data.card_by_name(c.name) for c in db_pack]

        mtg_ai_drafter = pickle.loads(next_drafter.bot_state)
        # TODO: for now picker state isn't saved to improve performance; we might need to in the future.
        mtg_ai_drafter.picker = cube_data.picker_factory.create()

        picked_card = mtg_ai_drafter.pick(pack)

        picked_db_card = next(c for c in db_pack if c.name == picked_card.name)
        next_drafter.bot_state = pickle.dumps(mtg_ai_drafter)
        next_drafter.make_pick(picked_db_card, phase, pick)

        next_drafter = next_drafter.receiving_from()
