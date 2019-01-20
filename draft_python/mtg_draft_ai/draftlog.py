import toml
from mtg_draft_ai.display import card_names_to_html, default_style
from mtg_draft_ai.api import DraftInfo


def dumps_log(drafters, draft_info):
    full_draft = []
    i = 0
    for d in drafters:
        picks = [{'pack': [c.name for c in pack], 'pick': pick.name} for pack, pick in zip(d.pack_history, d.cards_owned)]
        full_draft.append({'drafter': i, 'picks': picks})
        i += 1

    draft_info_dict = draft_info.__dict__
    draft_info_dict.pop('card_list')

    return toml.dumps({'draft_info': draft_info_dict, 'full_draft': full_draft})


def log_to_html(log_filename):
    with open(log_filename, 'r') as f:
        log_obj = toml.load(f)

    draft_info = DraftInfo(card_list=None, **log_obj['draft_info'])

    html = default_style()

    for drafter in log_obj['full_draft']:
        html += 'Drafter {}\n'.format(drafter['drafter'])
        for pick in drafter['picks']:
            html += '<div class="pack">\n{}</div>\n'.format(card_names_to_html(pick['pack'], highlighted=pick['pick']))

    return html
