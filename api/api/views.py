from rest_framework import viewsets
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Max, Count, F
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from .models import Player, PlayerName, DamageTypeClass, Round, Frag, Map, RallyPoint, Log, Session, Construction, ConstructionClass
from .serializers import PlayerSerializer, DamageTypeClassSerializer, RoundSerializer, FragSerializer, MapSerializer, LogSerializer
import numpy as np
import json
import binascii
from dateutil import parser
from datetime import datetime
from .exceptions import MissingParametersException
import semver


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
        # last_round_at = Round.objects.filter(players__contains=player).order_by('started_at')
        # self_kills = Frag.objects.filter()
        return JsonResponse({
            'kills': kills,
            'deaths': deaths,
            'kd_ratio': kd_ratio,
            'ff_kills': ff_kills,
            'ff_deaths': ff_deaths,
            'ff_kill_ratio': ff_kill_ratio,
            'ff_death_ratio': ff_death_ratio,
            # 'last_round_at': last_round_at
        })

    @action(detail=True)
    def sessions(self, request, pk):
        player = Player.objects.get(id=pk)
        dates = set()
        for session in player.sessions.all():
            dates.add(str(session.started_at.date()))
        dates = sorted(list(dates))
        return JsonResponse({
            'results': dates
        })


class DamageTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DamageTypeClass.objects.all()
    serializer_class = DamageTypeClassSerializer
    search_fields = ['id']

class FragViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Frag.objects.all()
    serializer_class = FragSerializer

    def get_queryset(self):
        queryset = Frag.objects.all()
        map_id = self.request.query_params.get('map_id', None)
        killer_id = self.request.query_params.get('killer_id', None)
        # if map_id is not None:
            # queryset = queryset.filter(round__map_id=map_id)
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
        rounds = Round.objects.filter(log__map_id=pk)
        round_count = rounds.count()
        axis_wins = rounds.filter(winner=0).count()
        allied_wins = rounds.filter(winner=1).count()
        axis_deaths = Frag.objects.filter(round__log__map_id=pk, victim_team_index=0).count()
        allied_deaths = Frag.objects.filter(round__log__map_id=pk, victim_team_index=1).count()
        return JsonResponse({
            'round_count': round_count,
            'axis_wins': axis_wins,
            'allied_wins': allied_wins,
            'axis_deaths': axis_deaths,
            'allied_deaths': allied_deaths
        })

    @action(detail=True)
    def heatmap(self, request, pk):
        frags = Frag.objects.filter(round__log__map_id=pk)
        data = list(map(lambda x: x.victim_location, frags.all()))
        return JsonResponse({
            'data': data
        })

class LogViewSet(viewsets.ModelViewSet):
    queryset = Log.objects.all()
    serializer_class = LogSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data['log'].file.read()
        data = data.replace(b'\r', b'')
        data = data.replace(b'\n', b'')
        crc = binascii.crc32(data)
        data = json.loads(data.decode('cp1251'))

        try:
            Log.objects.get(crc=crc)
            return Response(None, status=status.HTTP_409_CONFLICT, headers={})
        except ObjectDoesNotExist:
            pass

        if semver.compare(data['version'][1:], '8.3.0') < 0:
            raise Exception('Log file is for unsupported version ({})'.format(data['version']))

        log = Log()
        log.crc = crc
        log.version = data['version']

        map_data = data['map']
        log.map = Map(map_data['name'])
        log.map.bounds_ne_x = map_data['bounds']['ne'][0]
        log.map.bounds_ne_y = map_data['bounds']['ne'][1]
        log.map.bounds_sw_x = map_data['bounds']['sw'][0]
        log.map.bounds_sw_y = map_data['bounds']['sw'][1]
        log.map.offset = map_data['offset']
        log.map.save()

        log.save()

        for player_data in data['players']:
            try:
                player = Player.objects.get(id=player_data['id'])
            except ObjectDoesNotExist:
                player = Player(id=player_data['id'])
                player.save()
            for session_data in player_data['sessions']:
                session = Session()
                session.ip = session_data['ip']
                session.started_at = session_data['started_at']
                session.ended_at = session_data['ended_at']
                session.save()
                player.sessions.add(session)
            for name in player_data['names']:
                if name not in map(lambda x: x.name, player.names.all()):
                    player_name = PlayerName(name=name)
                    player_name.save()
                    player.save()
                    player.names.add(player_name)
            player.save()
            log.players.add(player)

        for round_data in data['rounds']:
            round = Round()
            round.map = log.map
            round.started_at = parser.parse(round_data['started_at'])
            round.ended_at = None if round_data['ended_at'] is None else parser.parse(round_data['ended_at'])
            round.winner = round_data['winner']
            round.log = log
            round.save()

            for frag_data in round_data['frags']:
                damage_type = DamageTypeClass(id=frag_data['damage_type'])
                damage_type.save()

                frag = Frag()
                frag.damage_type = damage_type
                frag.hit_index = frag_data['hit_index']
                frag.time = frag_data['time']
                frag.killer = Player.objects.get(id=frag_data['killer']['id'])
                frag.killer_team_index = frag_data['killer']['team']
                frag.killer_location_x = frag_data['killer']['location'][0]
                frag.killer_location_y = frag_data['killer']['location'][1]
                frag.killer_location_z = frag_data['killer']['location'][2]
                frag.victim = Player.objects.get(id=frag_data['victim']['id'])
                frag.victim_team_index = frag_data['victim']['team']
                frag.victim_location_x = frag_data['victim']['location'][0]
                frag.victim_location_y = frag_data['victim']['location'][1]
                frag.victim_location_z = frag_data['victim']['location'][2]
                frag.distance = np.linalg.norm(np.subtract(frag.victim_location, frag.killer_location))
                frag.round = round
                frag.save()

            for rally_point_data in round_data['rally_points']:
                rally_point = RallyPoint()
                rally_point.team_index = rally_point_data['team_index']
                rally_point.squad_index = rally_point_data['squad_index']
                rally_point.player = Player.objects.get(id=rally_point_data['player_id'])
                rally_point.is_established = rally_point_data['is_established']
                rally_point.establisher_count = rally_point_data['establisher_count']
                rally_point.location_x = rally_point_data['location'][0]
                rally_point.location_y = rally_point_data['location'][1]
                rally_point.location_z = rally_point_data['location'][2]
                rally_point.created_at = parser.parse(rally_point_data['created_at'])
                rally_point.destroyed_at = None if rally_point_data['destroyed_at'] is None else parser.parse(rally_point_data['destroyed_at'])
                rally_point.destroyed_reason = rally_point_data['destroyed_reason']
                rally_point.spawn_count = rally_point_data['spawn_count']
                rally_point.round = round
                rally_point.save()

            for construction_data in round_data['constructions']:
                construction = Construction()
                try:
                    construction_class = ConstructionClass.objects.get(classname=construction_data['class'])
                except ObjectDoesNotExist:
                    construction_class = ConstructionClass(classname=construction_data['class'])
                    construction_class.save()

                construction.classname = construction_class
                construction.player = Player.objects.get(id=construction_data['player_id'])
                construction.team_index = construction_data['team']
                construction.round_time = construction_data['round_time']
                construction.location_x = construction_data['location'][0]
                construction.location_y = construction_data['location'][1]
                construction.location_z = construction_data['location'][2]
                construction.round = round
                construction.save()

        log.save()

        return Response({}, status=status.HTTP_201_CREATED, headers={})


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
        player_ids = list(map(lambda x: x.id, round.log.players.all()))
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

