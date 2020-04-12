import logging
from multiprocessing.pool import ThreadPool
import os
import pickle
import statistics
import urllib

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import transaction
from django.conf import settings

from . import models
from . import draft_converter
from mtg_draft_ai.controller import create_packs
from mtg_draft_ai.api import DraftInfo, Drafter, read_cube_toml
from mtg_draft_ai.brains import GreedyPowerAndSynergyPicker
from mtg_draft_ai.deckbuild import best_two_color_synergy_build
from mtg_draft_ai import synergy
import requests
import toml


CUBE_FILE = os.path.join(settings.DRAFTS_APP_DIR, 'cube_81183_tag_data.toml')
IMAGE_URLS_FILE = os.path.join(settings.DRAFTS_APP_DIR, 'cube_81183_image_urls.toml')
FIXER_DATA_FILE = os.path.join(settings.DRAFTS_APP_DIR, 'cube_81183_fixer_data.toml')

CUBE_LIST = read_cube_toml(CUBE_FILE, FIXER_DATA_FILE)
CARDS_BY_NAME = {c.name: c for c in CUBE_LIST}
PICKER_FACTORY = GreedyPowerAndSynergyPicker.factory(CUBE_LIST)
LOGGER = logging.getLogger(__name__)


def _initialize_image_url_cache():
    # Load cache from disk
    cache = toml.load(IMAGE_URLS_FILE)

    # Filter out cards which are no longer in the cube list
    cache = {k: v for k, v in cache.items() if k in CARDS_BY_NAME}

    # Get URLs for new cards
    missing_cards = [name for name in CARDS_BY_NAME if name not in cache]
    with ThreadPool(10) as tp:
        urls = tp.map(_scryfall_image_url, missing_cards)

    for card_name, url in zip(missing_cards, urls):
        cache[card_name] = url

    # Write cache back out to disk
    with open(IMAGE_URLS_FILE, 'w') as f:
        toml.dump(cache, f)

    return cache


def _scryfall_image_url(name):
    try:
        r = requests.get('https://api.scryfall.com/cards/named', params={'exact': name})
        card_json = r.json()
        if 'card_faces' in card_json and 'image_uris' in card_json['card_faces'][0]:
            # Case for double-faced cards
            # TODO: nice to have - show both sides of a DFC
            return card_json['card_faces'][0]['image_uris']['normal']
        return card_json['image_uris']['normal']
    except Exception as e:
        print('Failed to get image uri for card: {}'.format(card_json))
        raise e


IMAGE_URL_CACHE = _initialize_image_url_cache()


class StaleReadError(Exception):
    pass


# /
def index(request):
    return render(request, 'drafts/index.html', {})


# /draft
@transaction.atomic
def create_draft(request):
    # TODO: Provide option to choose draft size
    human_drafter_names = request.POST['human_drafter_names'].split('\n')
    human_drafter_names = [name.strip() for name in human_drafter_names if len(name.strip()) > 0]
    num_humans = len(human_drafter_names)
    num_bots = int(request.POST['num_bot_drafters']) if 'num_bot_drafters' in request.POST else 5

    draft_info = DraftInfo(card_list=CUBE_LIST, num_drafters=num_humans + num_bots, num_phases=3, cards_per_pack=15)
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

    human_drafters = [models.Drafter(draft=new_draft, bot=False, name=name) for name in human_drafter_names]
    # TODO: for now picker state isn't saved to improve performance; we might need to in the future.
    bot_drafters = [models.Drafter(draft=new_draft, bot=True, bot_state=pickle.dumps(Drafter(None, draft_info)),
                                   name='Bot') for _ in range(0, num_bots)]
    drafters = _even_mix(human_drafters, bot_drafters)

    for i in range(0, draft_info.num_drafters):
        drafters[i].seat = i
        drafters[i].save()

    return HttpResponseRedirect(reverse('show_draft', kwargs={'draft_id': new_draft.id}))


# /draft/<int:draft_id>
def show_draft(request, draft_id):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafters = models.Drafter.objects.filter(draft=draft)
    human_drafters = [d for d in drafters if not d.bot]
    num_bots = len([d for d in drafters if d.bot])
    context = {'human_drafters': human_drafters, 'num_bots': num_bots, 'draft_id': draft_id}
    return render(request, 'drafts/draft_start.html', context)


# /draft/<int:draft_id>/seat/<int:seat>
def show_seat(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = models.Drafter.objects.get(draft=draft, seat=seat)

    pack_index = _get_pack_index(draft, drafter)
    cards = models.Card.objects.filter(draft=draft, phase=drafter.current_phase,
                                       start_seat=pack_index, picked_by__isnull=True)
    owned_cards = models.Card.objects.filter(draft=draft, picked_by=drafter)
    sorted_owned_cards = sorted(owned_cards, key=lambda c: (c.phase, c.picked_at))

    cards_with_images = [(c, _image_url(c.name)) for c in cards]
    owned_cards_with_images = [(c, _image_url(c.name)) for c in sorted_owned_cards]
    draft_complete = (drafter.current_phase == draft.num_phases)
    
    # Generate bot recommendations
    # TODO: fix interface for getting ratings
    pack_converted = [CARDS_BY_NAME[c.name] for c in cards]
    owned_converted = [CARDS_BY_NAME[c.name] for c in owned_cards]
    draft_info = DraftInfo(card_list=CUBE_LIST, num_drafters=6, num_phases=3, cards_per_pack=15)
    bot_ratings = PICKER_FACTORY.create()._get_ratings(pack_converted, owned_converted, draft_info)

    # Are we waiting on any picks?
    drafters = models.Drafter.objects.filter(draft=draft, bot=False)
    waiting_for_drafters = [d for d in drafters if d.current_phase < drafter.current_phase or
                            d.current_phase == drafter.current_phase and d.current_pick < drafter.current_pick]

    context = {'cards': cards_with_images, 'draft': draft,
               'phase': drafter.current_phase, 'pick': drafter.current_pick,
               'owned_cards': owned_cards_with_images, 'seat_range': range(0, draft.num_drafters),
               'drafter': drafter,
               'draft_complete': draft_complete,
               'bot_ratings': bot_ratings, 'waiting_for_drafters': waiting_for_drafters}

    return render(request, 'drafts/show_pack.html', context)


# /draft/<int:draft_id>/seat/<int:seat>/autobuild
def auto_build(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = models.Drafter.objects.get(draft=draft, seat=seat)
    owned_cards = models.Card.objects.filter(draft=draft, picked_by=drafter)

    # Convert from DB objects to Card objects with metadata
    pool = [CARDS_BY_NAME[c.name] for c in owned_cards]

    built_deck = best_two_color_synergy_build(pool)
    deck_graph = synergy.create_graph(built_deck, remove_isolated=False)
    leftovers = [c for c in pool if c not in built_deck]

    built_deck_images = [_image_url(c.name) for c in built_deck]
    leftovers_images = [_image_url(c.name) for c in leftovers]
    num_edges = len(deck_graph.edges)
    avg_power = statistics.mean([GreedyPowerAndSynergyPicker._power_rating(c) for c in built_deck
                                 if 'land' not in c.types])

    deck_card_names = [c.name for c in built_deck]
    leftovers_card_names = [c.name for c in leftovers]
    textarea_rows = len(owned_cards) + 1

    context = {'built_deck_images': built_deck_images, 'leftovers_images': leftovers_images,
               'num_edges': num_edges, 'avg_power': round(avg_power, 2), 'draft_id': draft_id,
               'bot_seat_range': range(1, draft.num_drafters), 'deck_card_names': deck_card_names,
               'leftovers_card_names': leftovers_card_names, 'textarea_rows': textarea_rows,
               'seat_range': range(0, draft.num_drafters), 'drafter': drafter, 'draft': draft}
    return render(request, 'drafts/autobuild.html', context)


# /draft/<int:draft_id>/seat/<int:seat>/all-picks
def all_picks(request, draft_id, seat):
    draft = get_object_or_404(models.Draft, pk=draft_id)
    drafter = models.Drafter.objects.get(draft=draft, seat=seat)

    output = draft_converter.convert_drafter(drafter)

    context = {'seat_range': range(0, draft.num_drafters), 'drafter': drafter, 'draft': draft, 'output': output}
    return render(request, 'drafts/show_all_picks.html', context)


# /draft/pick-card/<int:draft_id>
def pick_card(request, draft_id):
    try:
        with transaction.atomic():
            draft = get_object_or_404(models.Draft, pk=draft_id)
            drafter = models.Drafter.objects.get(draft=draft, seat=request.POST['seat'])
            picked_card = models.Card.objects.get(id=request.POST['picked_card_id'])
            phase = int(request.POST['phase'])
            pick = int(request.POST['pick'])

            _save_pick(draft, drafter, picked_card, phase, pick)

            # TODO: Use drafter field to designate primary instead of hardcoding it as seat 0
            if drafter.seat == 0:
                _make_bot_picks(draft, phase, pick)
    except StaleReadError:
        LOGGER.info('Stale read occurred when picking card, transaction was rolled back')

    return HttpResponseRedirect(reverse('show_seat', kwargs={'draft_id': draft_id, 'seat': request.POST['seat']}))


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


def _image_url(card_name):
    """ Gets the image URL for a card name from cache if present, otherwise falls back to the API URL. """
    if card_name in IMAGE_URL_CACHE:
        return IMAGE_URL_CACHE[card_name]

    # Fall back to using the API if we don't have the image URL cached (e.g. when viewing old drafts)
    query_string = urllib.parse.urlencode({'format': 'image', 'exact': card_name})
    return 'https://api.scryfall.com/cards/named?' + query_string


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
