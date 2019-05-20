from django.db import models
import datetime
import isodate


class PlayerName(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Session(models.Model):
    ip = models.GenericIPAddressField()
    started_at = models.DateTimeField(null=False)
    ended_at = models.DateTimeField(null=False)

    @property
    def duration(self):
        return (self.ended_at - self.started_at)


class Player(models.Model):
    id = models.CharField(max_length=17, primary_key=True)
    names = models.ManyToManyField(PlayerName)
    sessions = models.ManyToManyField(Session)

    def __str__(self):
        return '{} ({})'.format(self.id, self.name)

    @property
    def name(self):
        return self.names.all()[0].name

    @property
    def total_playtime(self):
        return isodate.duration_isoformat(sum(map(lambda x: x.duration, self.sessions.all()), datetime.timedelta()))

    @property
    def total_kills(self):
        return Frag.objects.filter(killer=self).count()

    @property
    def total_deaths(self):
        return Frag.objects.filter(victim=self).count()


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

    @property
    def num_players(self):
        return self.log.players.count()

    @property
    def num_kills(self):
        return Frag.objects.filter(round=self).count()

    @property
    def is_interesting(self):
        return self.num_players > 1 and self.num_kills > 0


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


class Objective(models.Model):
    map = models.ForeignKey(Map, on_delete=models.CASCADE)


class Capture(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    objective = models.ForeignKey(Objective, on_delete=models.CASCADE)
    round_time = models.IntegerField()
    team_index = models.IntegerField()


class Patron(models.Model):
    TIER_CHOICES = (
        ('lead', 'Lead'),
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold')
    )
    player = models.OneToOneField(Player, on_delete=models.DO_NOTHING)
    tier = models.CharField(max_length=32, choices=TIER_CHOICES)

    def __str__(self):
        return str(self.player)


class Event(models.Model):
    type = models.CharField(max_length=32)
    data = models.TextField()
    round = models.ForeignKey(Round, on_delete=models.CASCADE)

class Announcement(models.Model):
    created_at = models.DateTimeField()
    title = models.CharField(max_length=64)
    url = models.URLField()
    content = models.TextField()
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title
