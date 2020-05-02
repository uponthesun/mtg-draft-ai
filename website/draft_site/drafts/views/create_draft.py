import pickle
import random

from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse

from .. import models
from .constants import CUBES_BY_ID
from mtg_draft_ai.controller import create_packs
from mtg_draft_ai.api import Drafter


# /draft/create
@transaction.atomic
def create_draft(request):
    defaults = {
        'cube_select': None,  # required
        'human_drafter_names': 'Ash Ketchum\n',
        'num_bot_drafters': 5
    }
    params = {k: request.POST.get(k, default=v) for k, v in defaults.items()}

    cube_id = int(params['cube_select'])
    raw_human_drafter_names = params['human_drafter_names'].split('\n')
    human_drafter_names = [name.strip() for name in raw_human_drafter_names if len(name.strip()) > 0]
    num_bots = int(params['num_bot_drafters'])

    new_draft = _create_and_save_draft_models(cube_id, human_drafter_names, num_bots)

    return HttpResponseRedirect(reverse('show_draft', kwargs={'draft_id': new_draft.id}))


# Helper functions below

def _make_initial_bot_picks(draft):
    bots = draft.drafter_set.filter(bot=True).all()

    can_pick_bots = [b for b in bots if b.current_pack() is not None]
    while any(can_pick_bots):
        for b in can_pick_bots:
            pass

        can_pick_bots = [b for b in bots if b.current_pack() is not None]

    pass


def _create_and_save_draft_models(cube_id, human_drafter_names, num_bots):
    num_humans = len(human_drafter_names)

    # Create and save Draft model objects
    new_draft = models.Draft(cube_id=cube_id, num_drafters=num_humans + num_bots, num_phases=3, cards_per_pack=15)
    new_draft.save()

    # Create and save Card model objects for this draft
    draft_info = new_draft.to_draft_info(CUBES_BY_ID[cube_id].cards)
    packs = create_packs(draft_info)
    for phase in range(0, new_draft.num_phases):
        for start_seat in range(0, new_draft.num_drafters):
            pack = packs.get_pack(phase=phase, starting_seat=start_seat)
            for card in pack:
                db_card = models.Card(draft=new_draft, name=card.name, phase=phase, start_seat=start_seat)
                db_card.save()

    # Create and save Drafter model objects for this draft
    human_drafters = [models.Drafter(draft=new_draft, bot=False, name=name) for name in human_drafter_names]
    random.shuffle(human_drafters)
    # TODO: for now picker state isn't saved to improve performance; we might need to in the future.
    bot_drafters = [models.Drafter(draft=new_draft, bot=True, bot_state=pickle.dumps(Drafter(None, draft_info)),
                                   name='Bot') for _ in range(0, num_bots)]
    drafters = _even_mix(human_drafters, bot_drafters)
    for i in range(0, len(drafters)):
        drafters[i].seat = i
        drafters[i].save()

    return new_draft


def _even_mix(list_a, list_b):
    """Given two lists, mixes them 'evenly', maximizing the total distance between elements from the same list."""
    total_len = len(list_a) + len(list_b)
    increment = total_len / len(list_a)

    result = [None] * total_len

    i = 0
    for e in list_a:
        result[int(i)] = e
        i += increment

    list_b_copy = list_b.copy()
    for i in range(0, len(result)):
        # Assumes value of list_a are not None
        if result[i] is None:
            result[i] = list_b_copy.pop(0)

    return result
