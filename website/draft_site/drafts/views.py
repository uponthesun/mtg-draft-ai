import logging
import os
import pickle
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.db import transaction
from django.conf import settings

from . import models
from mtg_draft_ai.controller import create_packs
from mtg_draft_ai.api import DraftInfo, Drafter, read_cube_toml
from mtg_draft_ai.brains import GreedySynergyPicker


CUBE_FILE = os.path.join(settings.DRAFTS_APP_DIR, 'cube_81183_tag_data.toml')
CUBE_LIST = read_cube_toml(CUBE_FILE)
CARDS_BY_NAME = {c.name: c for c in CUBE_LIST}
PICKER_FACTORY = GreedySynergyPicker.factory(CUBE_LIST)
LOGGER = logging.getLogger(__name__)


class StaleReadError(Exception):
    pass


# /
def index(request):
    return render(request, 'drafts/index.html', {})


# /draft
@transaction.atomic
def create_draft(request):
    draft_info = DraftInfo(card_list=CUBE_LIST, num_drafters=6, num_phases=3, cards_per_pack=15)
    packs = create_packs(draft_info)

    new_draft = models.Draft(num_drafters=draft_info.num_drafters, num_phases=draft_info.num_phases,
                             cards_per_pack=draft_info.cards_per_pack)
    new_draft.save()

    for phase in range(0, draft_info.num_phases):
        for start_seat in range(0, draft_info.num_drafters):
            pack = packs.get_pack(phase=phase, starting_seat=start_seat)
            for card in pack:
                db_card = models.Card(draft=new_draft, name=card.name, phase=phase, start_seat=start_seat)
                db_card.save()

    # Create human drafter in DB
    models.Drafter(draft=new_draft, seat=0, bot=False).save()
    # Create bot drafters in DB
    # Seat 0 is the human drafter, so start at seat 1
    for i in range(1, draft_info.num_drafters):
        # TODO: for now picker state isn't saved to improve performance; we might need to in the future.
        bot_drafter = Drafter(None, draft_info)
        db_bot_drafter = models.Drafter(draft=new_draft, seat=i, bot=True, bot_state=pickle.dumps(bot_drafter))
        db_bot_drafter.save()

    return HttpResponseRedirect(reverse('show_draft', args=[new_draft.id]))


# /draft/<int:draft_id>
def show_draft(request, draft_id):
    return show_seat(request, draft_id, seat=0)


# /draft/<int:draft_id>/seat/<int:seat>
def show_seat(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = models.Drafter.objects.get(draft=draft, seat=seat)

    pack_index = _get_pack_index(draft, drafter)
    cards = models.Card.objects.filter(draft=draft, phase=drafter.current_phase,
                                       start_seat=pack_index, picked_by__isnull=True)
    owned_cards = models.Card.objects.filter(draft=draft, picked_by=drafter)
    sorted_owned_cards = sorted(owned_cards, key=lambda c: (c.phase, c.picked_at))

    context = {'cards': cards, 'draft_id': draft_id,
               'phase': drafter.current_phase, 'pick': drafter.current_pick,
               'owned_cards': sorted_owned_cards, 'bot_seat_range': range(1, draft.num_drafters),
               'human_drafter': seat == 0, 'current_seat': seat}

    return render(request, 'drafts/show_pack.html', context)


# /draft/pick-card/<int:draft_id>
def pick_card(request, draft_id):
    try:
        with transaction.atomic():
            draft = get_object_or_404(models.Draft, pk=draft_id)
            drafter = models.Drafter.objects.get(draft=draft, seat=0)
            picked_card = models.Card.objects.get(id=request.POST['picked_card_id'])
            phase = int(request.POST['phase'])
            pick = int(request.POST['pick'])

            _save_pick(draft, drafter, picked_card, phase, pick)

            _make_bot_picks(draft, phase, pick)
    except StaleReadError:
        LOGGER.info('Stale read occurred when picking card, transaction was rolled back')

    return HttpResponseRedirect(reverse('show_draft', args=[draft_id]))


def _make_bot_picks(draft, phase, pick):
    bot_drafters = sorted(models.Drafter.objects.filter(draft=draft, bot=True),
                          key=lambda d: d.seat)
    for db_drafter in bot_drafters:
        pack_index = _get_pack_index(draft, db_drafter, phase, pick)
        db_pack = models.Card.objects.filter(draft=draft, phase=phase,
                                             start_seat=pack_index, picked_by__isnull=True)
        pack = [CARDS_BY_NAME[c.name] for c in db_pack]

        drafter = pickle.loads(db_drafter.bot_state)
        # TODO: for now picker state isn't saved to improve performance; we might need to in the future.
        drafter.picker = PICKER_FACTORY.create()
        picked_card = drafter.pick(pack)

        picked_db_card = next(c for c in db_pack if c.name == picked_card.name)
        # TODO: for now picker state isn't saved to improve performance; we might need to in the future.
        drafter.picker = None
        db_drafter.bot_state = pickle.dumps(drafter)
        _save_pick(draft, db_drafter, picked_db_card, phase, pick)


def _save_pick(draft, drafter, card, phase, pick):
    updated_count = models.Card.objects \
        .filter(id=card.id, picked_by__isnull=True) \
        .update(picked_by=drafter, picked_at=drafter.current_pick)

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


def _get_pack_index(draft, drafter, phase=None, pick=None):
    phase = phase or drafter.current_phase
    pick = pick or drafter.current_pick

    # Alternate passing directions based on phase, starting with passing left.
    direction = 1 if phase % 2 == 0 else -1

    # Implement "passing" packs after each pick by shifting the index of the pack
    # assigned to each drafter by the pick index. We add when passing left,
    # and subtract when passing right (picture the packs staying in place,
    # and the drafters standing up and walking around the table).
    # Then we apply modulus (since the packs are passed in a circle).
    pack_index = (pick * direction + drafter.seat) % draft.num_drafters

    # The mod of a negative number will remain negative, e.g. -11 mod 8 = -3,
    # but we want to use the positive equivalent to find the index into the packs,
    # so we add num_drafters if it's a negative number. So in our example, -3
    # would become 5. This represents starting at seat 0 and finding the drafter
    # 3 seats to the left, which would be the drafter at seat 5.
    if pack_index < 0:
        pack_index += draft.num_drafters

    return pack_index
