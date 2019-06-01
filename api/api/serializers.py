from .models import Player, DamageTypeClass, Round, PlayerName, Frag, Map, Log, Session, Event, Patron, Announcement, TextMessage
from rest_framework import serializers

class PlayerNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerName
        fields = ['name']

class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['ip', 'started_at', 'ended_at']

class PlayerSerializer(serializers.ModelSerializer):
    id = serializers.CharField()
    names = PlayerNameSerializer(read_only=True, many=True)

    class Meta:
        model = Player
        fields = ['id', 'names']

class DamageTypeClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = DamageTypeClass
        fields = ['id']

class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ['id', 'crc', 'version', 'created_at']

class RoundSerializer(serializers.ModelSerializer):
    log = LogSerializer(read_only=True)

    class Meta:
        model = Round
        fields = ['id', 'winner', 'started_at', 'ended_at', 'version', 'map', 'num_players', 'is_interesting', 'num_kills', 'log']

class FragSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frag
        fields = ['id', 'damage_type', 'distance', 'killer', 'victim', 'victim_location', 'killer_location']

class MapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Map
        fields = ['name', 'bounds', 'offset']

import json

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
        model = Event
        fields = ['type', 'data']

class PatronSerializer(serializers.ModelSerializer):

    class Meta:
        model = Patron
        exclude = []

class AnnouncementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Announcement
        exclude = []

class TextMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = TextMessage
        fields = ['id', 'type', 'message', 'sent_at', 'team_index', 'squad_index', 'sender_id', 'log_id']