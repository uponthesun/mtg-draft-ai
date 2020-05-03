import pickle

from django.db import models
from mtg_draft_ai.api import DraftInfo

from .views.constants import CUBES_BY_ID


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


class Drafter(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE)
    seat = models.IntegerField()  # 0-indexed
    current_phase = models.IntegerField(default=0)  # 0-indexed
    current_pick = models.IntegerField(default=0)  # 0-indexed
    bot = models.BooleanField()
    # TODO: may need to store this outside DB eventually
    bot_state = models.BinaryField(null=True, blank=True)
    name = models.CharField(max_length=40, default='')

    def __str__(self):
        return 'ID: {}, Name: {}, Draft: {}, Seat: {}, Is Bot: {}, Phase: {}, Pick: {}'.format(
            self.id, self.name, self.draft.id, self.seat, self.bot, self.current_phase, self.current_pick)

    def make_pick(self, card, phase, pick):
        updated_count = Card.objects \
            .filter(id=card.id, picked_by__isnull=True) \
            .update(picked_by=self, picked_at=pick)

        if updated_count != 1:
            raise StaleReadError('Card already picked: draft {}, seat {}, phase {}, pick {}'.format(
                self.draft.id, self.drafter.seat, phase, pick))

        new_pick = pick + 1
        new_phase = phase
        if new_pick >= self.draft.cards_per_pack:
            new_pick = 0
            new_phase = phase + 1

        updated_count = Drafter.objects \
            .filter(id=self.id, current_phase=phase, current_pick=pick) \
            .update(current_phase=new_phase, current_pick=new_pick, bot_state=self.bot_state)

        if updated_count != 1:
            raise StaleReadError('Drafter already updated: draft {}, seat {}, phase {}, pick {}'.format(
                self.draft.id, self.seat, phase, pick))

    def make_bot_pick(self, phase, pick):
        db_pack = self.current_pack()
        if db_pack is None:
            return

        cube_data = CUBES_BY_ID[self.draft.cube_id]
        mtg_draft_ai_pack = [cube_data.card_by_name(c.name) for c in db_pack]

        mtg_ai_drafter = pickle.loads(self.bot_state)
        # TODO: for now picker state isn't saved to improve performance; we might need to in the future.
        mtg_ai_drafter.picker = cube_data.picker_factory.create()

        picked_card = mtg_ai_drafter.pick(mtg_draft_ai_pack)

        picked_db_card = next(c for c in db_pack if c.name == picked_card.name)
        self.bot_state = pickle.dumps(mtg_ai_drafter)
        self.make_pick(picked_db_card, phase, pick)

    def current_pack(self):
        # If the next pack hasn't been passed yet, return None.
        receiving_from_drafter_progress = (self.receiving_from().current_phase, self.receiving_from().current_pick)
        if receiving_from_drafter_progress < (self.current_phase, self.current_pick):
            return None

        # Implement "passing" packs after each pick by shifting the index of the pack
        # assigned to each drafter by the pick index. We add when passing left,
        # and subtract when passing right (picture the packs staying in place,
        # and the drafters standing up and walking around the table).
        # Then we apply modulus (since the packs are passed in a circle).
        pack_index = (self.seat - self.current_pick * self._direction()) % self.draft.num_drafters

        return self.draft.card_set.filter(phase=self.current_phase, start_seat=pack_index, picked_by__isnull=True)

    def passing_to(self):
        return self._adjacent_drafter(self._direction())

    def receiving_from(self):
        return self._adjacent_drafter(-1 * self._direction())

    def owned_cards(self):
        return self.draft.card_set.filter(picked_by=self)

    def waiting_for_drafters(self):
        human_drafters = self.draft.drafter_set.filter(bot=False)
        return [d for d in human_drafters
                if d.current_phase < self.current_phase or
                d.current_phase == self.current_phase and d.current_pick < self.current_pick]

    def _direction(self):
        # Alternate passing directions based on phase, starting with passing left.
        return -1 if self.current_phase % 2 == 0 else 1

    def _adjacent_drafter(self, direction):
        passing_to_seat = (self.seat + direction) % self.draft.num_drafters
        return self.draft.drafter_set.filter(seat=passing_to_seat).first()


class Card(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    phase = models.IntegerField()
    start_seat = models.IntegerField()
    picked_by = models.ForeignKey(Drafter, on_delete=models.CASCADE, null=True, blank=True)
    picked_at = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return str(self.__dict__)
