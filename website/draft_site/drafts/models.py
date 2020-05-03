from django.db import models
from mtg_draft_ai.api import DraftInfo

from .constants import CUBES_BY_ID


class StaleReadError(Exception):
    pass


class Draft(models.Model):
    cube_id = models.IntegerField()
    num_drafters = models.IntegerField()
    num_phases = models.IntegerField()
    cards_per_pack = models.IntegerField()

    def __str__(self):
        return str(self.__dict__)

    def to_draft_info(self, card_list):
        return DraftInfo(card_list=card_list, num_drafters=self.num_drafters, num_phases=self.num_phases,
                         cards_per_pack=self.cards_per_pack)

    def make_initial_bot_picks(self):
        bots = self.drafter_set.filter(bot=True).all()

        can_pick_bots = [b for b in bots if b.current_pack() is not None]
        while any(can_pick_bots):
            for b in can_pick_bots:
                b.make_bot_pick()
                b.refresh_from_db()
            can_pick_bots = [b for b in bots if b.current_pack() is not None]


class Drafter(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE)
    seat = models.IntegerField()  # 0-indexed
    current_phase = models.IntegerField(default=0)  # 0-indexed
    current_pick = models.IntegerField(default=0)  # 0-indexed
    bot = models.BooleanField()
    bot_state = models.BinaryField(null=True, blank=True)  # Not used as of 05/02/2020
    name = models.CharField(max_length=40, default='')

    def __str__(self):
        return 'ID: {}, Name: {}, Draft: {}, Seat: {}, Is Bot: {}, Phase: {}, Pick: {}'.format(
            self.id, self.name, self.draft.id, self.seat, self.bot, self.current_phase, self.current_pick)

    # TODO: move current phase to draft model
    def advance_phase(self):
        new_pick = 0
        new_phase = self.current_phase + 1

        updated_count = Drafter.objects \
            .filter(id=self.id, current_phase=self.current_phase, current_pick=self.current_pick) \
            .update(current_phase=new_phase, current_pick=new_pick)

        if updated_count != 1:
            raise StaleReadError('Drafter already updated: draft {}, seat {}'.format(self.draft.id, self.seat))

    def make_pick(self, card, phase, pick):
        updated_count = Card.objects \
            .filter(id=card.id, picked_by__isnull=True) \
            .update(picked_by=self, picked_at=pick)

        if updated_count != 1:
            raise StaleReadError('Card already picked: draft {}, seat {}, phase {}, pick {}'.format(
                self.draft.id, self.seat, phase, pick))

        # Don't advance phase here if we reach end of pack; that's done for all drafters at once in views.pick_card
        new_pick = pick + 1
        new_phase = phase

        updated_count = Drafter.objects \
            .filter(id=self.id, current_phase=phase, current_pick=pick) \
            .update(current_phase=new_phase, current_pick=new_pick)

        if updated_count != 1:
            raise StaleReadError('Drafter already updated: draft {}, seat {}, phase {}, pick {}'.format(
                self.draft.id, self.seat, phase, pick))

    def make_bot_pick(self, phase=None, pick=None):
        phase = phase or self.current_phase
        pick = pick or self.current_pick

        db_pack = self.current_pack()
        if db_pack is None:
            return

        cube_data = CUBES_BY_ID[self.draft.cube_id]
        mtg_draft_ai_pack = [cube_data.card_by_name(c.name) for c in db_pack]
        mtg_draft_ai_owned_cards = [cube_data.card_by_name(c.name) for c in self.owned_cards()]

        # TODO: for now picker state isn't saved to improve performance; we might need to in the future.
        picker = cube_data.picker_factory.create()
        picked_card = picker.pick(mtg_draft_ai_pack, cards_owned=mtg_draft_ai_owned_cards,
                                  draft_info=self.draft.to_draft_info(cube_data.cards))

        picked_db_card = next(c for c in db_pack if c.name == picked_card.name)
        # self.bot_state = pickle.dumps(mtg_ai_drafter)
        self.make_pick(picked_db_card, phase, pick)

    def current_pack(self):
        if self.current_pick >= self.draft.cards_per_pack or self.current_phase >= self.draft.num_phases:
            return None

        # If the next pack hasn't been passed yet, return None.
        receiving_from = self._receiving_from()
        receiving_from_drafter_progress = (receiving_from.current_phase, receiving_from.current_pick)
        if receiving_from_drafter_progress < (self.current_phase, self.current_pick):
            return None

        # Implement "passing" packs after each pick by shifting the index of the pack
        # assigned to each drafter by the pick index. We add when passing left,
        # and subtract when passing right (picture the packs staying in place,
        # and the drafters standing up and walking around the table).
        # Then we apply modulus (since the packs are passed in a circle).
        pack_index = (self.seat - self.current_pick * self.direction()) % self.draft.num_drafters

        return self.draft.card_set.filter(phase=self.current_phase, start_seat=pack_index, picked_by__isnull=True)

    def owned_cards(self):
        return self.draft.card_set.filter(picked_by=self)

    def direction(self):
        # Alternate passing directions based on phase, starting with passing left.
        return -1 if self.current_phase % 2 == 0 else 1

    def _receiving_from(self):
        return self._adjacent_drafter(-1 * self.direction())

    def _adjacent_drafter(self, direction):
        passing_to_seat = (self.seat + direction) % self.draft.num_drafters
        return self.draft.drafter_set.get(seat=passing_to_seat)


class Card(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    phase = models.IntegerField()
    start_seat = models.IntegerField()
    picked_by = models.ForeignKey(Drafter, on_delete=models.CASCADE, null=True, blank=True)
    picked_at = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return str(self.__dict__)
