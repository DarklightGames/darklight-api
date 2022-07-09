from . import models
from rest_framework import serializers
import json
import isodate


class PlayerNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PlayerName
        fields = ['name']


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Session
        fields = ['ip', 'started_at', 'ended_at']


class PlayerSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    names = PlayerNameSerializer(read_only=True, many=True)
    kills = serializers.IntegerField()
    deaths = serializers.IntegerField()
    playtime = serializers.SerializerMethodField()

    def get_playtime(self, obj):
        return isodate.duration_isoformat(obj.playtime)

    class Meta:
        model = models.Player
        fields = ['id', 'names', 'kills', 'deaths', 'ff_kills', 'ff_deaths', 'playtime']


class DamageTypeClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DamageTypeClass
        fields = ['id', 'classname']


class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Log
        fields = ['id', 'crc', 'version', 'created_at']


class RoundSerializer(serializers.ModelSerializer):
    log = LogSerializer(read_only=True)

    class Meta:
        model = models.Round
        fields = ['id', 'winner', 'started_at', 'ended_at', 'version', 'map', 'num_players', 'is_interesting', 'num_kills', 'log']


class FragSerializer(serializers.ModelSerializer):

    killer = serializers.SerializerMethodField()
    victim = serializers.SerializerMethodField()

    def get_killer(self, obj):
        return {
            'id': obj.killer.id,
            'location': obj.killer_location
        }

    def get_victim(self, obj):
        return {
            'id': obj.victim.id,
            'location': obj.victim_location
        }

    # TODO: use proper serializermethodfields
    class Meta:
        model = models.Frag
        fields = ['id', 'damage_type', 'distance', 'killer', 'victim']


class VehicleFragSerializer(serializers.ModelSerializer):

    killer = serializers.SerializerMethodField()
    vehicle = serializers.SerializerMethodField()

    def get_killer(self, obj):
        return {
            'id': obj.killer.id,
            'team': obj.killer_team_index,
            'pawn': obj.killer_pawn_class.classname if obj.killer_pawn_class else None,
            'vehicle': obj.killer_vehicle_class.classname if obj.killer_vehicle_class else None,
            'location': [
                int(obj.killer_location_x),
                int(obj.killer_location_y)
            ]
        }

    def get_vehicle(self, obj):
        return {
            'class': obj.vehicle_class.classname if obj.vehicle_class else None,
            'location': [
                int(obj.vehicle_location_x),
                int(obj.vehicle_location_y)
            ]
        }

    class Meta:
        model = models.VehicleFrag
        fields = ['id', 'damage_type', 'time', 'killer', 'vehicle', 'distance']

class MapSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Map
        fields = ['id', 'name', 'bounds', 'offset']


class JSONSerializerField(serializers.Field):
    """Serializer for JSONField -- required to make field writable"""

    def to_representation(self, value):
        json_data = {}
        try:
            json_data = json.loads(value)
        except ValueError as e:
            raise e
        finally:
            return json_data

    def to_internal_value(self, data):
        return json.dumps(data)


class EventSerializer(serializers.ModelSerializer):
    data = JSONSerializerField()

    class Meta:
        model = models.Event
        fields = ['type', 'data']


class PatronSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Patron
        exclude = []


class AnnouncementSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Announcement
        exclude = []


class TextMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.TextMessage
        fields = ['id', 'type', 'message', 'sent_at', 'team_index', 'squad_index', 'sender', 'log']


class RallyPointSerializer(serializers.ModelSerializer):

    player = serializers.SerializerMethodField()

    def get_player(self, obj):
        return {'id': obj.player.id, 'name': obj.player.name}

    class Meta:
        model = models.RallyPoint
        exclude = []
        fields = ['id', 'team_index', 'squad_index', 'player', 'spawn_count', 'is_established',
                  'establisher_count', 'destroyed_reason', 'round', 'location', 'created_at', 'lifespan']
