import toml
from mtg_draft_ai.display import card_names_to_html, default_style
from mtg_draft_ai.api import DraftInfo, Drafter


def dumps_log(drafters, draft_info):
    """Writes pick history of drafters into a toml log file.

    Args:
        drafters (List[Drafter]): Drafters to create log for.
        draft_info (DraftInfo): Draft config to record.

    Returns:
        str: TOML string containing every pick for every drafter, as well as the draft info.
    """
    full_draft = []
    i = 0
    for d in drafters:
        picks = [{'pack': [c.name for c in pack], 'pick': pick.name} for pack, pick in zip(d.pack_history, d.cards_owned)]
        full_draft.append({'drafter': i, 'picks': picks})
        i += 1

    draft_info_dict = draft_info.__dict__.copy()
    draft_info_dict.pop('card_list')

    return toml.dumps({'draft_info': draft_info_dict, 'full_draft': full_draft})


def load_drafters_from_log(log_file, card_list=None):
    """Returns a list of drafters, with pick history, reconstructed from log file.

    Args:
        log_file: File-like object to load the log from.
        card_list (List[Card]): Optional - specify in order to return full Card objects instead of just names.

    Returns:
        By default, returned pick history contains card names only. If card_list is provided,
        contains full card objects instead.
    """
    log_obj = toml.load(log_file)

    draft_info = DraftInfo(card_list=card_list, **log_obj['draft_info'])

    if card_list:
        cards_by_name = {c.name: c for c in card_list}

    drafters = []

    for drafter_picks in log_obj['full_draft']:
        drafter = Drafter(picker=None, draft_info=draft_info)
        drafters.append(drafter)

        for pick in drafter_picks['picks']:
            drafter.cards_owned.append(pick['pick'])
            drafter.pack_history.append(pick['pack'])

        if card_list:
            drafter.cards_owned = [cards_by_name[n] for n in drafter.cards_owned]
            drafter.pack_history = [[cards_by_name[n] for n in p] for p in drafter.pack_history]

    return drafters


def log_to_html(log_file):
    """Outputs HTML visualization of a draft from the given log file."""

    drafters = load_drafters_from_log(log_file)

    html = default_style()

    i = 0
    for drafter in drafters:
        html += 'Drafter {}\n'.format(i)
        for pack, pick in zip(drafter.pack_history, drafter.cards_owned):
            html += '<div class="pack">\n{}</div>\n'.format(card_names_to_html(pack, highlighted=pick))

        html += 'Drafter {} final pool\n'.format(i)
        html += '<div class>\n{}</div>\n'.format(card_names_to_html(drafter.cards_owned))
        i += 1

    return html
