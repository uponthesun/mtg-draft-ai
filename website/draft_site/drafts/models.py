from django.db import models
from mtg_draft_ai.api import DraftInfo


class Draft(models.Model):
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
    seat = models.IntegerField()
    # 0-indexed
    current_phase = models.IntegerField(default=0)
    # 0-indexed
    current_pick = models.IntegerField(default=0)
    bot = models.BooleanField()
    # TODO: may need to store this outside DB eventually
    bot_state = models.BinaryField(null=True, blank=True)
    name = models.CharField(max_length=40, default='')

    def __str__(self):
        return 'ID: {}, Name: {}, Draft: {}, Seat: {}, Is Bot: {}, Phase: {}, Pick: {}'.format(
            self.id, self.name, self.draft.id, self.seat, self.bot, self.current_phase, self.current_pick)

    def current_pack(self):
        # Alternate passing directions based on phase, starting with passing left.
        direction = 1 if self.current_phase % 2 == 0 else -1

        # Implement "passing" packs after each pick by shifting the index of the pack
        # assigned to each drafter by the pick index. We add when passing left,
        # and subtract when passing right (picture the packs staying in place,
        # and the drafters standing up and walking around the table).
        # Then we apply modulus (since the packs are passed in a circle).
        pack_index = (self.current_pick * direction + self.seat) % self.draft.num_drafters

        # The mod of a negative number will remain negative, e.g. -11 mod 8 = -3,
        # but we want to use the positive equivalent to find the index into the packs,
        # so we add num_drafters if it's a negative number. So in our example, -3
        # would become 5. This represents starting at seat 0 and finding the drafter
        # 3 seats to the left, which would be the drafter at seat 5.
        if pack_index < 0:
            pack_index += self.draft.num_drafters

        return self.draft.card_set.filter(phase=self.current_phase, start_seat=pack_index, picked_by__isnull=True)

    def owned_cards(self):
        return self.draft.card_set.filter(picked_by=self)

    def waiting_for_drafters(self):
        human_drafters = self.draft.drafter_set.filter(bot=False)
        return [d for d in human_drafters
                if d.current_phase < self.current_phase or
                d.current_phase == self.current_phase and d.current_pick < self.current_pick]


class Card(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    phase = models.IntegerField()
    start_seat = models.IntegerField()
    picked_by = models.ForeignKey(Drafter, on_delete=models.CASCADE, null=True, blank=True)
    picked_at = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return str(self.__dict__)
