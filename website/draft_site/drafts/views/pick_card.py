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
            _save_pick(draft, drafter, picked_card, phase, pick)

            # TODO: Use drafter field to designate primary instead of hardcoding it as seat 0
            if drafter.seat == 0:
                _make_bot_picks(draft, phase, pick)
    except StaleReadError:
        LOGGER.info('Stale read occurred when picking card, transaction was rolled back')

    return HttpResponseRedirect(reverse('show_seat', kwargs={'draft_id': draft_id, 'seat': request.POST['seat']}))


# Helper functions below

def _make_bot_picks(draft, phase, pick):
    bot_drafters = sorted(draft.drafter_set.filter(bot=True), key=lambda d: d.seat)
    for db_drafter in bot_drafters:
        db_pack = db_drafter.current_pack()
        cube_data = CUBES_BY_ID['6949']
        pack = [cube_data.card_by_name(c.name) for c in db_pack]

        drafter = pickle.loads(db_drafter.bot_state)
        # TODO: for now picker state isn't saved to improve performance; we might need to in the future.
        drafter.picker = cube_data.picker_factory.create()
        picked_card = drafter.pick(pack)

        picked_db_card = next(c for c in db_pack if c.name == picked_card.name)
        drafter.picker = None
        db_drafter.bot_state = pickle.dumps(drafter)
        _save_pick(draft, db_drafter, picked_db_card, phase, pick)


def _save_pick(draft, drafter, card, phase, pick):
    updated_count = models.Card.objects \
        .filter(id=card.id, picked_by__isnull=True) \
        .update(picked_by=drafter, picked_at=pick)

    if updated_count != 1:
        raise StaleReadError('Card already picked: draft {}, seat {}, phase {}, pick {}'.format(
                             draft.id, drafter.seat, phase, pick))

    new_pick = pick + 1
    new_phase = phase
    if new_pick >= draft.cards_per_pack:
        new_pick = 0
        new_phase = phase + 1

    updated_count = models.Drafter.objects \
        .filter(id=drafter.id, current_phase=phase, current_pick=pick) \
        .update(current_phase=new_phase, current_pick=new_pick, bot_state=drafter.bot_state)

    if updated_count != 1:
        raise StaleReadError('Drafter already updated: draft {}, seat {}, phase {}, pick {}'.format(
                             draft.id, drafter.seat, phase, pick))
