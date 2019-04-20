from django.db import models


class Draft(models.Model):
    num_drafters = models.IntegerField()
    num_phases = models.IntegerField()
    cards_per_pack = models.IntegerField()

    def __str__(self):
        return str(self.__dict__)


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

    def __str__(self):
        return 'ID: {}, Draft: {}, Seat: {}, Is Bot: {}, Phase: {}, Pick: {}'.format(
            self.id, self.draft.id, self.seat, self.bot, self.current_phase, self.current_pick)


class Card(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    phase = models.IntegerField()
    start_seat = models.IntegerField()
    picked_by = models.ForeignKey(Drafter, on_delete=models.CASCADE, null=True, blank=True)
    picked_at = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return str(self.__dict__)
