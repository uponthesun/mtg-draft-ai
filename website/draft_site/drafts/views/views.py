import logging
import os
import pickle
import random
import statistics

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import transaction
from django.conf import settings

from drafts.cube_data import CubeData
from drafts import models
from drafts import draft_converter
from mtg_draft_ai.controller import create_packs
from mtg_draft_ai.api import DraftInfo, Drafter
from mtg_draft_ai.brains import GreedyPowerAndSynergyPicker
from mtg_draft_ai.deckbuild import best_two_color_synergy_build
from mtg_draft_ai import synergy

CUBE_FILE = os.path.join(settings.DRAFTS_APP_DIR, 'cube_81183_tag_data.toml')
IMAGE_URLS_FILE = os.path.join(settings.DRAFTS_APP_DIR, 'cube_81183_image_urls.toml')
FIXER_DATA_FILE = os.path.join(settings.DRAFTS_APP_DIR, 'cube_81183_fixer_data.toml')

CUBE_DATA = CubeData.load(CUBE_FILE, IMAGE_URLS_FILE, FIXER_DATA_FILE)
PICKER_FACTORY = GreedyPowerAndSynergyPicker.factory(CUBE_DATA.cards)

LOGGER = logging.getLogger(__name__)


class StaleReadError(Exception):
    pass


# /
def index(request):
    return render(request, 'drafts/index.html', {})


def _create_and_save_draft_models(human_drafter_names, num_bots):
    num_humans = len(human_drafter_names)

    # Create and save Draft model objects
    new_draft = models.Draft(num_drafters=num_humans + num_bots, num_phases=3, cards_per_pack=15)
    new_draft.save()

    # Create and save Card model objects for this draft
    draft_info = new_draft.to_draft_info(CUBE_DATA.cards)
    print(new_draft)
    print(draft_info)
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


# /draft
@transaction.atomic
def create_draft(request):
    defaults = {
        'human_drafter_names': 'Ash Ketchum\n',
        'num_bot_drafters': 5
    }
    params = {k: request.POST.get(k, default=v) for k, v in defaults.items()}
    raw_human_drafter_names = params['human_drafter_names'].split('\n')
    human_drafter_names = [name.strip() for name in raw_human_drafter_names if len(name.strip()) > 0]
    num_bots = int(params['num_bot_drafters'])
    new_draft = _create_and_save_draft_models(human_drafter_names, num_bots)

    return HttpResponseRedirect(reverse('show_draft', kwargs={'draft_id': new_draft.id}))


# /draft/<int:draft_id>
def show_draft(request, draft_id):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafters = draft.drafter_set.all()

    context = {
        'human_drafters': [d for d in drafters if not d.bot],
        'num_bots': len([d for d in drafters if d.bot]),
        'draft': draft,
    }
    return render(request, 'drafts/draft_start.html', context)


# /draft/<int:draft_id>/seat/<int:seat>
def show_seat(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=seat)

    pack_index = _get_pack_index(draft, drafter)
    cards = draft.card_set.filter(phase=drafter.current_phase, start_seat=pack_index, picked_by__isnull=True)
    owned_cards = draft.card_set.filter(picked_by=drafter)
    sorted_owned_cards = sorted(owned_cards, key=lambda c: (c.phase, c.picked_at))
    
    # Generate bot recommendations
    # TODO: fix interface for getting ratings
    pack_converted = [CUBE_DATA.card_by_name(c.name) for c in cards]
    owned_converted = [CUBE_DATA.card_by_name(c.name) for c in owned_cards]
    draft_info = draft.to_draft_info(CUBE_DATA.cards)
    bot_ratings = PICKER_FACTORY.create()._get_ratings(pack_converted, owned_converted, draft_info)

    # Are we waiting on any picks?
    human_drafters = draft.drafter_set.filter(bot=False)
    waiting_for_drafters = [d for d in human_drafters
                            if d.current_phase < drafter.current_phase or
                            d.current_phase == drafter.current_phase and d.current_pick < drafter.current_pick]

    context = {
        'draft': draft,
        'drafter': drafter,
        'seat_range': range(0, draft.num_drafters),  # Used by header
        'cards': [(c, CUBE_DATA.get_image_url(c.name)) for c in cards],
        'owned_cards': [(c, CUBE_DATA.get_image_url(c.name)) for c in sorted_owned_cards],
        'bot_ratings': bot_ratings,
        'waiting_for_drafters': waiting_for_drafters,
        'draft_complete': (drafter.current_phase == draft.num_phases),
    }

    return render(request, 'drafts/show_pack.html', context)


# /draft/<int:draft_id>/seat/<int:seat>/autobuild
def auto_build(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=seat)
    owned_cards = draft.card_set.filter(picked_by=drafter)

    # Convert from DB objects to Card objects with metadata
    pool = [CUBE_DATA.card_by_name(c.name) for c in owned_cards]

    built_deck = best_two_color_synergy_build(pool)
    deck_graph = synergy.create_graph(built_deck, remove_isolated=False)
    leftovers = [c for c in pool if c not in built_deck]
    # TODO: fix interface
    avg_power = statistics.mean([GreedyPowerAndSynergyPicker._power_rating(c) for c in built_deck
                                 if 'land' not in c.types])

    context = {
        'draft': draft,
        'drafter': drafter,
        'seat_range': range(0, draft.num_drafters),  # Used by header
        'built_deck_images': [CUBE_DATA.get_image_url(c.name) for c in built_deck],
        'leftovers_images': [CUBE_DATA.get_image_url(c.name) for c in leftovers],
        'deck_card_names': [c.name for c in built_deck],
        'leftovers_card_names': [c.name for c in leftovers],
        'num_edges': len(deck_graph.edges),
        'avg_power': round(avg_power, 2),
        'textarea_rows': len(owned_cards) + 1,
    }
    return render(request, 'drafts/autobuild.html', context)


# /draft/<int:draft_id>/seat/<int:seat>/all-picks
def all_picks(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=seat)

    output = draft_converter.convert_drafter(drafter)

    context = {
        'draft': draft,
        'drafter': drafter,
        'seat_range': range(0, draft.num_drafters),
        'output': output,
    }
    return render(request, 'drafts/show_all_picks.html', context)


# /draft/pick-card/<int:draft_id>
def pick_card(request, draft_id):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = draft.drafter_set.get(seat=request.POST['seat'])
    picked_card = get_object_or_404(models.Card, id=request.POST['picked_card_id'])
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


def _make_bot_picks(draft, phase, pick):
    bot_drafters = sorted(draft.drafter_set.filter(bot=True), key=lambda d: d.seat)
    for db_drafter in bot_drafters:
        pack_index = _get_pack_index(draft, db_drafter, phase, pick)
        db_pack = draft.card_set.filter(phase=phase, start_seat=pack_index, picked_by__isnull=True)
        pack = [CUBE_DATA.card_by_name(c.name) for c in db_pack]

        drafter = pickle.loads(db_drafter.bot_state)
        # TODO: for now picker state isn't saved to improve performance; we might need to in the future.
        drafter.picker = PICKER_FACTORY.create()
        picked_card = drafter.pick(pack)

        picked_db_card = next(c for c in db_pack if c.name == picked_card.name)
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
