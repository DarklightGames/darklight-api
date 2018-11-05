from .models import Player, DamageType, Round, PlayerName, PlayerIP, Frag, Map
from rest_framework import serializers

class PlayerNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerName
        fields = ['name', 'date']

class PlayerIPSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerIP
        fields = ['ip', 'date']

class PlayerSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.CharField()
    names = PlayerNameSerializer(read_only=True, many=True)
    ips = PlayerIPSerializer(read_only=True, many=True)

    class Meta:
        model = Player
        fields = ['id', 'names', 'ips']

class DamageTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = DamageType
        fields = ['id']

class RoundSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Round
        fields = ['id']

class FragSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frag
        fields = ['id', 'damage_type', 'distance', 'killer', 'victim', 'victim_location', 'killer_location']

class MapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Map
        fields = ['name']