from django.db import models


class PlayerName(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Session(models.Model):
    ip = models.GenericIPAddressField()
    started_at = models.DateTimeField(null=False)
    ended_at = models.DateTimeField(null=False)


class Player(models.Model):
    id = models.CharField(max_length=17, primary_key=True)
    names = models.ManyToManyField(PlayerName)
    sessions = models.ManyToManyField(Session)


class DamageTypeClass(models.Model):
    id = models.CharField(primary_key=True, max_length=128)


class Map(models.Model):
    name = models.CharField(max_length=128, primary_key=True)
    bounds_ne_x = models.FloatField(null=True)
    bounds_ne_y = models.FloatField(null=True)
    bounds_sw_x = models.FloatField(null=True)
    bounds_sw_y = models.FloatField(null=True)
    offset = models.IntegerField(default=0)

    @property
    def bounds(self):
        return [
            [
               self.bounds_ne_x,
               self.bounds_ne_y
            ],
            [
                self.bounds_sw_x,
                self.bounds_sw_y
            ]
        ]


class Log(models.Model):
    crc = models.BigIntegerField(unique=True)
    version = models.CharField(max_length=16)
    map = models.ForeignKey(Map, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now=True)
    players = models.ManyToManyField(Player)


class Round(models.Model):
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True)
    winner = models.IntegerField(null=True)
    log = models.ForeignKey(Log, on_delete=models.CASCADE)

    @property
    def duration(self):
        return

    @property
    def version(self):
        return self.log.version

    @property
    def map(self):
        return self.log.map.name


class PawnClass(models.Model):
    classname = models.CharField(max_length=128, unique=True)


class ConstructionClass(models.Model):
    classname = models.CharField(max_length=128, unique=True)


class Construction(models.Model):
    team_index = models.IntegerField()
    round_time = models.IntegerField()
    classname = models.ForeignKey(ConstructionClass, on_delete=models.CASCADE)
    location_x = models.IntegerField()
    location_y = models.IntegerField()
    location_z = models.IntegerField()
    player = models.ForeignKey(Player, on_delete=models.DO_NOTHING)
    round = models.ForeignKey(Round, on_delete=models.CASCADE)

    @property
    def location(self):
        return (self.location_x, self.location_y)


class Frag(models.Model):
    damage_type = models.ForeignKey(DamageTypeClass, on_delete=models.DO_NOTHING)
    hit_index = models.SmallIntegerField()
    time = models.IntegerField()
    killer = models.ForeignKey(Player, on_delete=models.DO_NOTHING, related_name='+')
    killer_pawn_class = models.ForeignKey(PawnClass, on_delete=models.DO_NOTHING, related_name='+', null=True)
    killer_team_index = models.SmallIntegerField()
    killer_location_x = models.FloatField(default=0.0)
    killer_location_y = models.FloatField(default=0.0)
    killer_location_z = models.FloatField(default=0.0)
    victim = models.ForeignKey(Player, on_delete=models.DO_NOTHING, related_name='+')
    victim_pawn_class = models.ForeignKey(PawnClass, on_delete=models.DO_NOTHING, related_name='+', null=True)
    victim_team_index = models.SmallIntegerField()
    victim_location_x = models.FloatField(default=0.0)
    victim_location_y = models.FloatField(default=0.0)
    victim_location_z = models.FloatField(default=0.0)
    distance = models.FloatField(default=0.0)
    round = models.ForeignKey(Round, on_delete=models.CASCADE)

    @property
    def victim_location(self):
        return (self.victim_location_x, self.victim_location_y)

    @property
    def killer_location(self):
        return (self.killer_location_x, self.killer_location_y)

    @property
    def is_suicide(self):
        return self.killer == self.victim

    @property
    def is_friendly_fire(self):
        return not self.is_suicide and self.killer_team_index == self.victim_team_index


class RallyPoint(models.Model):
    DESTROYED_REASON_CHOICES = (
        ('overrun', 'Overrun'),
        ('exhausted', 'Exhausted'),
        ('damaged', 'Damaged'),
        ('deleted', 'Deleted'),
        ('replaced', 'Replaced'),
        ('spawn_kill', 'Spawn Kill'),
        ('abandoned', 'Abandoned'),
        ('encroached', 'Encroached Upon')
    )

    team_index = models.IntegerField()
    squad_index = models.IntegerField()
    player = models.ForeignKey(Player, on_delete=models.DO_NOTHING)
    location_x = models.FloatField()
    location_y = models.FloatField()
    location_z = models.FloatField()
    spawn_count = models.IntegerField()
    is_established = models.BooleanField()
    establisher_count = models.IntegerField()
    created_at = models.DateTimeField()
    destroyed_at = models.DateTimeField(null=True)
    destroyed_reason = models.CharField(max_length=32, null=True, choices=DESTROYED_REASON_CHOICES)
    round = models.ForeignKey(Round, on_delete=models.CASCADE)

    @property
    def location(self):
        return (self.location_x, self.location_y)
