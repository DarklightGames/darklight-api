from rest_framework import viewsets
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from rest_framework.response import Response
from django.db.models import Max
from rest_framework.decorators import action
from .models import Player, PlayerName, DamageType, Round, PlayerIP, Frag, Map
from .serializers import PlayerSerializer, DamageTypeSerializer, RoundSerializer, FragSerializer, MapSerializer
import numpy as np
import json
import binascii
from .exceptions import MissingParametersException


class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
    search_fields = ['names__name']

class DamageTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DamageType.objects.all()
    serializer_class = DamageTypeSerializer
    search_fields = ['id']

class FragViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Frag.objects.all()
    serializer_class = FragSerializer

    def get_queryset(self):
        queryset = Frag.objects.all()
        map_id = self.request.query_params.get('map_id', None)
        killer_id = self.request.query_params.get('killer_id', None)
        if map_id is not None:
            queryset = queryset.filter(round__map_id=map_id)
        if killer_id is not None:
            queryset = queryset.filter(killer__id=killer_id)
        return queryset

    @action(detail=False)
    # TODO: form validation
    def range_histogram(self, request):
        damage_type_ids = request.query_params.getlist('damage_type_ids[]', None)
        if damage_type_ids is None:
            raise MissingParametersException(['damage_type_id'])
        bin_size_in_meters = 10
        bin_size = bin_size_in_meters * 60.352
        histogram = []
        data = {}
        for damage_type_id in damage_type_ids:
            for i in range(25):
                min_distance = int(i * bin_size)
                max_distance = (i + 1) * bin_size
                count = Frag.objects.filter(damage_type__id=damage_type_id, distance__gte=min_distance, distance__lt=max_distance).count()
                histogram.append([i * bin_size_in_meters, count])
            data[damage_type_id] = histogram
        return JsonResponse(data)


class MapViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Map.objects.order_by('name')
    serializer_class = MapSerializer
    search_fields = ['name']

class RoundViewSet(viewsets.ModelViewSet):
    queryset = Round.objects.all()
    serializer_class = RoundSerializer

    def create(self, request):
        data = request.data['log'].file.read()
        data = data.replace(b'\r', b'')
        data = data.replace(b'\n', b'')
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
