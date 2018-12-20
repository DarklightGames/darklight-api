from .models import Player, DamageTypeClass, Round, PlayerName, Frag, Map, Log, Session
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

class RoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Round
        fields = ['id', 'winner', 'started_at', 'ended_at', 'version', 'map']

class FragSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frag
        fields = ['id', 'damage_type', 'distance', 'killer', 'victim', 'victim_location', 'killer_location']

class MapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Map
        fields = ['name', 'bounds', 'offset']

class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ['id']