from rest_framework import viewsets
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import JsonResponse
from django.db import transaction
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.views import APIView
import django_filters.rest_framework
from django.core.exceptions import FieldError
from django.db.models import Max, Count, F, Q
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from .models import Player, PlayerName, DamageTypeClass, Round, Frag, Map, RallyPoint, Log, Session, Construction, ConstructionClass, Event, PawnClass, Patron, Announcement
from .serializers import PlayerSerializer, DamageTypeClassSerializer, RoundSerializer, FragSerializer, MapSerializer, LogSerializer, EventSerializer, PatronSerializer, AnnouncementSerializer
import numpy as np
import json
from json.decoder import JSONDecodeError
import binascii
import os
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
            'total_playtime': player.total_playtime
            # 'last_round_at': last_round_at
        })

    @action(detail=True)
    def sessions(self, request, pk):
        # TODO: different types of sessions (per day)
        player = Player.objects.get(id=pk)
        dates = dict()
        for session in player.sessions.all():
            date = str(session.started_at.date())
            if date not in dates:
                dates[date] = session.duration
            else:
                dates[date] += session.duration
        return JsonResponse({
            'results': dates
        })


class DamageTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DamageTypeClass.objects.all().order_by('id')
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


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


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
        secret = request.data['secret']
        if secret != os.environ['API_SECRET']:
            raise PermissionDenied('Invalid secret.')
        data = request.data['log'].file.read()
        data = data.replace(b'\r', b'')
        data = data.replace(b'\n', b'')
        crc = binascii.crc32(data)

        # The game mangles names with special characters which can cause decoding errors.
        # To mitigate this, let's just replace un-mappable characters with spaces as we
        # encounter them and hope for the best.
        attempts = 0
        while True:
            try:
                data = data.decode('cp1251')
            except UnicodeDecodeError as e:
                attempts += 1
                if attempts >= 100:
                    raise RuntimeError('Failed to resolve string decoding errors via brute force, giving up!')
                data = bytearray(data)
                data[e.start:e.end] = b' '
                continue
            break

        try:
            data = json.loads(data)
        except JSONDecodeError:
            # Versions <=v9.0.9 had a bug where backslashes and double-quotes were not being properly escaped
            # and therefore couldn't be parsed properly. If we run into a decoding error, attempt to escape the
            # backslashes and load it up again.
            data = data.replace('\\', '\\\\')
            data = json.loads(data)

        try:
            Log.objects.get(crc=crc)
            return Response(None, status=status.HTTP_409_CONFLICT, headers={})
        except ObjectDoesNotExist:
            pass

        if semver.compare(data['version'][1:], '8.3.0') < 0:
            data = {'success': False, 'error': 'Log file version {} is unsupported.'.format(data['version'][1:])}
            return JsonResponse(data, status=status.HTTP_406_NOT_ACCEPTABLE)

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
                if semver.compare(data['version'][1:], '9.0.9') <= 0:
                    if session_data['ended_at'] == '':
                        # There was a bug with <=v9.0.9 where player timeouts would not terminate sessions, resulting in
                        # ended_at being an empty string. This fix effectively terminates the session immediately.
                        session.ended_at = session_data['started_at']
                    else:
                        session.ended_at = session_data['ended_at']
                else:
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
                frag.killer_pawn_class = PawnClass.objects.get_or_create(classname=frag_data['killer']['pawn'])[0]
                frag.victim = Player.objects.get(id=frag_data['victim']['id'])
                frag.victim_team_index = frag_data['victim']['team']
                frag.victim_location_x = frag_data['victim']['location'][0]
                frag.victim_location_y = frag_data['victim']['location'][1]
                frag.victim_location_z = frag_data['victim']['location'][2]
                frag.victim_pawn_class = PawnClass.objects.get_or_create(classname=frag_data['victim']['pawn'])[0]
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

            if 'events' in round_data:
                events = round_data['events']

                for event_data in events:
                    event = Event()
                    event.type = event_data['type']
                    event.data = json.dumps(event_data['data'])
                    event.round = round
                    event.save()

        log.save()

        # TODO: store the log on disk, gzip'd probably
        log_path = os.path.join('storage', 'logs', str(crc) + '.log')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        json.dump(data, open(log_path, 'w'))

        return Response({}, status=status.HTTP_201_CREATED, headers={})


class RoundFilterSet(django_filters.rest_framework.FilterSet):
    map = django_filters.rest_framework.CharFilter(method='filter_map')

    class Meta:
        model = Round
        fields = ('map',)

    def filter_map(self, queryset, name, value):
        if value:
            queryset = queryset.annotate(mapf=F('log__map__name')).filter(mapf=value)
        return queryset


class PatronViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Patron.objects.all()
    serializer_class = PatronSerializer
    search_fields = ['player__id']


class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer

    @action(detail=False)
    def latest(self, request):
        queryset = Announcement.objects.filter(is_published=True).order_by('-created_at')
        if queryset.count() == 1:
            return Response(status=204)
        announcement = queryset.first()
        data = AnnouncementSerializer(instance=announcement).data
        return JsonResponse(data)


class RoundViewSet(viewsets.ReadOnlyModelViewSet):
    model=Round
    queryset = Round.objects.all().order_by('-started_at')
    serializer_class = RoundSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = RoundFilterSet

    @action(detail=True)
    def summary(self, request, pk):
        round = Round.objects.get(pk=pk)
        deaths = Frag.objects.filter(round=round).count()
        axis_deaths = Frag.objects.filter(round=round, victim_team_index=0).count()
        allied_deaths = Frag.objects.filter(round=round, victim_team_index=1).count()
        data = {
            'kills': deaths,
            'axis_deaths': axis_deaths,
            'allied_deaths': allied_deaths
        }
        return JsonResponse(data)

    @action(detail=True)
    def scoreboard(self, request, pk):
        # add sorting
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
                'kd': kills / deaths if deaths > 0 else None,
                'tks': tks
            })
        return paginator.get_paginated_response(data)

    @action(detail=True)
    def player_summary(self, request, pk):
        round = Round.objects.get(pk=pk)
        player_id = request.GET['player_id']
        player = Player.objects.get(pk=player_id)
        frags = Frag.objects.filter(round=round, killer=player)
        kills = list(frags.values('damage_type').annotate(total=Count('damage_type')).order_by('total').annotate(longest=Max('distance')))
        return JsonResponse({
            'kills': kills
        })
        # longest range kill
        # aggregate kills by damage type
        # summary of frags for the player

    @action(detail=True)
    def frags(self, request, pk):
        round = Round.objects.get(pk=pk)
        frags = Frag.objects.filter(round=round)
        paginator = LimitOffsetPagination()
        order_by = self.request.query_params.get('order_by', None)
        if order_by is not None:
            try:
                frags = frags.order_by(order_by)
            except FieldError:
                pass
        damage_type_id = self.request.query_params.get('damage_type_id', None)
        if damage_type_id is not None:
            frags = frags.filter(damage_type__id=damage_type_id)
        killer_id = self.request.query_params.get('killer', None)
        if killer_id is not None:
            frags = frags.filter(killer__id=killer_id)
        victim_id = self.request.query_params.get('victim', None)
        if victim_id is not None:
            frags = frags.filter(victim__id=victim_id)
        frags = paginator.paginate_queryset(frags, request)
        data = list(map(lambda x: {
            'damage_type_id': x.damage_type.id,
            'victim': {
                'id': x.victim.id,
                'name': x.victim.names.all()[0].name,
                'pawn': x.victim_pawn_class.classname if x.victim_pawn_class else None,
                'team': x.victim_team_index
            },
            'killer': {
                'id': x.killer.id,
                'name': x.killer.names.all()[0].name,
                'pawn': x.killer_pawn_class.classname if x.killer_pawn_class else None,
                'team': x.killer_team_index
            },
            'distance': x.distance,
            'time': x.time
        }, frags))
        return paginator.get_paginated_response(data)

    @action(detail=True)
    def players(self, request, pk):
        round = Round.objects.get(pk=pk)
        search = self.request.query_params.get('search', None)
        print(search)
        data = []
        for player in round.log.players.all():
            if search is None or search.lower() in player.name.lower():
                data.append({
                    'id': player.id,
                    'names': list(map(lambda x: {'name': x.name}, player.names.all()))
                })
        return JsonResponse({
            'results': data
        })



def damage_type_friendly_fire(request):
    damage_types = DamageTypeClass.objects.all()
    results = []
    for damage_type in damage_types:
        frags = Frag.objects.filter(damage_type=damage_type)
        kills = frags.count()
        suicides = frags.filter(killer=F('victim')).count()
        team_kills = frags.filter(~Q(killer=F('victim'))).filter(killer_team_index=F('victim_team_index')).count()
        results.append({
            'id': damage_type.id,
            'kills': kills,
            'team_kills': team_kills,
            'suicides': suicides,
            'team_kill_ratio': team_kills / kills
        })
    return JsonResponse({
        'results': results
    })

def easter(request):
    player_counts = dict()
    for event in Event.objects.filter(type='egg_found'):
        data = json.loads(event.data)
        player_id = data['player_id']
        if player_id not in player_counts:
            player_counts[player_id] = 0
        player_counts[player_id] += 1
    player_counts = [x for x in player_counts.items()]
    player_counts = sorted(player_counts, key=lambda x: x[1])
    player_counts = {k:v for k,v in player_counts}
    return JsonResponse(player_counts)
