from django.db import models
import numpy


class PlayerName(models.Model):
    name = models.CharField(max_length=128)
    date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class PlayerIP(models.Model):
    ip = models.GenericIPAddressField()
    date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.ip

class Player(models.Model):
    id = models.CharField(max_length=17, primary_key=True)
    names = models.ManyToManyField(PlayerName)
    ips = models.ManyToManyField(PlayerIP)

class DamageType(models.Model):
    id = models.CharField(primary_key=True, max_length=128)

class Map(models.Model):
    name = models.CharField(max_length=128, primary_key=True)

class Round(models.Model):
    crc = models.IntegerField(unique=True)
    version = models.CharField(max_length=16)
    map = models.ForeignKey(Map, on_delete=models.DO_NOTHING)
    #frags = models.ManyToManyField(Frag)
    #players = models.ManyToManyField(Player)

class Frag(models.Model):
    damage_type = models.ForeignKey(DamageType, on_delete=models.DO_NOTHING)
    hit_index = models.SmallIntegerField()
    time = models.IntegerField()
    killer = models.ForeignKey(Player, on_delete=models.DO_NOTHING, related_name='+')
    killer_team_index = models.SmallIntegerField()
    victim = models.ForeignKey(Player, on_delete=models.DO_NOTHING, related_name='+')
    victim_team_index = models.SmallIntegerField()
    victim_location_x = models.FloatField(default=0.0)
    victim_location_y = models.FloatField(default=0.0)
    victim_location_z = models.FloatField(default=0.0)
    killer_location_x = models.FloatField(default=0.0)
    killer_location_y = models.FloatField(default=0.0)
    killer_location_z = models.FloatField(default=0.0)
    distance = models.FloatField(default=0.0)
    round = models.ForeignKey(Round, on_delete=models.CASCADE)

    @property
    def victim_location(self):
        return (self.victim_location_x, self.victim_location_y, self.victim_location_z)

    @property
    def killer_location(self):
        return (self.killer_location_x, self.killer_location_y, self.killer_location_z)

    @property
    def is_suicide(self):
        return self.killer == self.victim

    @property
    def is_friendly_fire(self):
        return not self.is_suicide and self.killer_team_index == self.victim_team_index
