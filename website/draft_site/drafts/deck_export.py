import base64


def cockatrice(deck, leftovers):
    deck_lines = [_card_line(c) for c in deck]
    leftovers_lines = [_card_line(c) for c in leftovers]

    return '\n'.join(deck_lines + [''] + leftovers_lines)


def deckbuild_ui(deck, leftovers, cube_data, encoded=False):
    deck_lines = [_card_line(c, cube_data) for c in deck]
    leftovers_lines = [_card_line(c, cube_data) for c in leftovers]

    lines = '\n'.join(deck_lines + ['', '// Sideboard'] + leftovers_lines)
    return base64.urlsafe_b64encode(lines.encode('utf-8')).decode('utf-8') if encoded else lines


def _card_line(card, cube_data=None):
    line = '1 {}'.format(card.name)
    if cube_data:
        line += ' ({})'.format(cube_data.card_by_name(card.name).card_set.upper())
    return line
