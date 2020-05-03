import logging

from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import transaction

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
            _make_bot_picks(drafter)
            _advance_phase_if_needed(draft)
    except StaleReadError:
        LOGGER.info('Stale read occurred when picking card, transaction was rolled back')

    return HttpResponseRedirect(reverse('show_seat', kwargs={'draft_id': draft_id, 'seat': request.POST['seat']}))


# Helper functions below

def _make_bot_picks(human_drafter):
    draft = human_drafter.draft

    all_drafters = sorted(draft.drafter_set.all(), key=lambda d: d.seat)

    current_seat = (human_drafter.seat + human_drafter.direction()) % draft.num_drafters

    while all_drafters[current_seat].bot:
        all_drafters[current_seat].make_bot_pick()
        current_seat = (current_seat + human_drafter.direction()) % draft.num_drafters


def _advance_phase_if_needed(draft):
    all_drafters = draft.drafter_set.all()
    drafters_done_with_phase = [d for d in all_drafters if d.current_pick >= draft.cards_per_pack]

    if len(drafters_done_with_phase) == len(all_drafters):
        # TODO: move current phase to draft model
        for drafter in all_drafters:
            drafter.advance_phase()

    if draft.eager_picks_enabled(all_drafters):
        draft.make_initial_bot_picks()
