from rest_framework import viewsets
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from .models import Player, PlayerName, DamageType, Round, PlayerIP, Frag, Map
from .serializers import PlayerSerializer, DamageTypeSerializer, RoundSerializer, FragSerializer
import numpy as np
import json
import binascii


class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

class DamageTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DamageType.objects.all()
    serializer_class = DamageTypeSerializer

class FragViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Frag.objects.all()
    serializer_class = FragSerializer

class RoundViewSet(viewsets.ModelViewSet):
    queryset = Round.objects.all()
    serializer_class = RoundSerializer

    def create(self, request):
        data = request.data['log'].file.read()
        data = data.replace(b'\r\n', b'')
        crc = binascii.crc32(data)
        data = json.loads(data.decode('cp1252'))

        try:
            Round.objects.get(crc=crc)
            return Response(None, status=status.HTTP_409_CONFLICT, headers={})
        except ObjectDoesNotExist:
            pass

        round_map = Map(name=data['map'])
        round_map.save()

        round = Round()
        round.crc = crc
        round.version = data['version']
        round.map = round_map
        round.save()

        for x in data['players']:
            try:
                player = Player.objects.get(id=x['id'])
            except ObjectDoesNotExist:
                player = Player(id=x['id'])
            for name in x['names']:
                if name not in map(lambda x: x.name, player.names.all()):
                    player_name = PlayerName(name=name)
                    player_name.save()
                    player.save()
                    player.names.add(player_name)
            if x['ip'] not in map(lambda x: x.ip, player.ips.all()):
                player_ip = PlayerIP(ip=x['ip'])
                player_ip.save()
                player.save()
                player.ips.add(player_ip)
            player.save()
        for x in data['frags']:
            damage_type = DamageType(id=x['damage_type'])
            damage_type.save()

            frag = Frag()
            frag.damage_type = damage_type
            frag.hit_index = x['hit_index']
            frag.time = x['time']
            frag.killer = Player.objects.get(id=x['killer']['id'])
            frag.killer_team_index = x['killer']['team']
            frag.killer_location_x = x['killer']['location'][0]
            frag.killer_location_y = x['killer']['location'][1]
            frag.killer_location_z = x['killer']['location'][2]
            frag.victim = Player.objects.get(id=x['victim']['id'])
            frag.victim_team_index = x['victim']['team']
            frag.victim_location_x = x['victim']['location'][0]
            frag.victim_location_y = x['victim']['location'][1]
            frag.victim_location_z = x['victim']['location'][2]
            frag.distance = np.linalg.norm(np.subtract(frag.victim_location, frag.killer_location))
            frag.round = round
            frag.save()

        return Response({}, status=status.HTTP_201_CREATED, headers={})
