import logging
import statistics

from django.shortcuts import render, get_object_or_404

from .constants import CUBE_DATA, PICKER_FACTORY
from .. import models
from .. import draft_converter
from mtg_draft_ai.brains import GreedyPowerAndSynergyPicker
from mtg_draft_ai.deckbuild import best_two_color_synergy_build
from mtg_draft_ai import synergy

LOGGER = logging.getLogger(__name__)


# /
def index(request):
    return render(request, 'drafts/index.html', {})


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

    current_pack = drafter.current_pack()
    owned_cards = draft.card_set.filter(picked_by=drafter)
    sorted_owned_cards = sorted(owned_cards, key=lambda c: (c.phase, c.picked_at))

    # Generate bot recommendations
    # TODO: fix interface for getting ratings
    pack_converted = [CUBE_DATA.card_by_name(c.name) for c in current_pack]
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
        'cards': [(c, CUBE_DATA.get_image_url(c.name)) for c in current_pack],
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
