from rest_framework import viewsets
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Max, Count, F
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from .models import Player, PlayerName, DamageType, Round, PlayerIP, Frag, Map
from .serializers import PlayerSerializer, DamageTypeSerializer, RoundSerializer, FragSerializer, MapSerializer
import numpy as np
import json
import binascii
from dateutil import parser
from datetime import datetime
from .exceptions import MissingParametersException


class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
    search_fields = ['id', 'names__name']

    @action(detail=False)
    def damage_type_kills(self, request):
        killer_id = request.query_params.get('killer_id', None)
        frags = Frag.objects.all()
        if killer_id is not None:
            frags = frags.filter(killer_id=killer_id)
        frags = frags.values('damage_type_id').annotate(kills=Count('damage_type_id')).order_by('-kills')
        paginator = LimitOffsetPagination()
        frags = paginator.paginate_queryset(frags, request)
        data = list(map(lambda x: {'damage_type_id': x['damage_type_id'], 'kills': x['kills']}, frags))
        return paginator.get_paginated_response(data)

    @action(detail=True)
    def summary(self, request, pk):
        player = Player.objects.get(id=pk)
        kills = Frag.objects.filter(killer=player).count()
        deaths = Frag.objects.filter(victim=player).count()
        kd_ratio = kills / deaths if deaths != 0 else 0.0
        ff_kills = Frag.objects.filter(killer=player, killer_team_index=F('victim_team_index')).exclude(victim=player).count()
        ff_deaths = Frag.objects.filter(victim=player, killer_team_index=F('victim_team_index')).exclude(killer=player).count()
        ff_kill_ratio = ff_kills / kills if kills != 0 else 0.0
        ff_death_ratio = ff_deaths / deaths if deaths != 0 else 0.0
        # self_kills = Frag.objects.filter()
        return JsonResponse({
            'kills': kills,
            'deaths': deaths,
            'kd_ratio': kd_ratio,
            'ff_kills': ff_kills,
            'ff_deaths': ff_deaths,
            'ff_kill_ratio': ff_kill_ratio,
            'ff_death_ratio': ff_death_ratio
        })


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
    def range_histogram(self, request):
        damage_type_ids = request.query_params.getlist('damage_type_ids[]', None)
        if damage_type_ids is None:
            raise MissingParametersException(['damage_type_id'])
        bin_size_in_meters = 5
        bin_size = bin_size_in_meters * 60.352
        data = {}
        for damage_type_id in damage_type_ids:
            bins = []
            frags = Frag.objects.filter(damage_type__id=damage_type_id)
            total = 0
            for i in range(25):
                min_distance = int(i * bin_size)
                max_distance = (i + 1) * bin_size
                count = frags.filter(damage_type__id=damage_type_id, distance__gte=min_distance, distance__lt=max_distance).count()
                total += count
                bins.append([i * bin_size_in_meters, count])
            data[damage_type_id] = {
                'total': total,
                'bins': bins
            }
        return JsonResponse(data)


class MapViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Map.objects.order_by('name')
    serializer_class = MapSerializer
    search_fields = ['name']

    @action(detail=True)
    def summary(self, request, pk):
        return JsonResponse({})

    @action(detail=True)
    def heatmap(self, request, pk):
        frags = Frag.objects.filter(round__map_id=pk)
        data = list(map(lambda x: x.victim_location, frags.all()))
        return JsonResponse({
            'data': data
        })

class RoundViewSet(viewsets.ModelViewSet):
    queryset = Round.objects.all().order_by('-started_at')
    serializer_class = RoundSerializer

    @action(detail=True)
    def summary(self, request, pk):
        round = Round.objects.get(pk=pk)
        deaths = Frag.objects.filter(round=round).count()
        axis_deaths = Frag.objects.filter(round=round, victim_team_index=0).count()
        allied_deaths = Frag.objects.filter(round=round, victim_team_index=1).count()
        duration = round.ended_at - round.started_at
        data = {
            'kills': deaths,
            'axis_deaths': axis_deaths,
            'allied_deaths': allied_deaths,
            'duration': duration
        }
        return JsonResponse(data)

    @action(detail=True)
    def scoreboard(self, request, pk):
        round = Round.objects.get(pk=pk)
        paginator = LimitOffsetPagination()
        player_ids = list(map(lambda x: x.id, round.players.all()))
        players = Player.objects.filter(id__in=player_ids)
        players = paginator.paginate_queryset(players, request)
        data = []
        for player in players:
            kills = Frag.objects.filter(round=round, killer=player).count()
            deaths = Frag.objects.filter(round=round, victim=player).count()
            tks = Frag.objects.filter(round=round, killer=player, killer_team_index=F('victim_team_index')).count()
            data.append({
                'player': {
                    'id': player.id,
                    'name': player.names.all()[0].name
                },
                'kills': kills,
                'deaths': deaths,
                'tks': tks
            })
        return paginator.get_paginated_response(data)

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
        round.started_at = parser.parse(data['round_start'])
        round.ended_at = parser.parse(data['round_end'])
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
            ip = x['ip'].split(':')[0]
            if ip not in map(lambda x: x.ip, player.ips.all()):
                player_ip = PlayerIP(ip=ip)
                player_ip.save()
                player.save()
                player.ips.add(player_ip)
            player.save()
            round.players.add(player)

        round.save()

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
