from django.db import models


class Draft(models.Model):
    pass


class Card(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    phase = models.IntegerField()
    start_seat = models.IntegerField()
    picked_by = models.IntegerField(null=True, blank=True)
