import logging
import time
import timeit
from rest_framework import viewsets, status
from rest_framework.filters import OrderingFilter, SearchFilter
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import JsonResponse
from django.db import transaction
from rest_framework.response import Response
import django_filters.rest_framework
from django.core.exceptions import FieldError
from django.db.models import Max, Count, F, Q
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from . import models
from . import serializers
import numpy as np
import json
from json.decoder import JSONDecodeError
import binascii
import os
from dateutil import parser
from .exceptions import MissingParametersException
import semver


class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Player.objects.all()
    serializer_class = serializers.PlayerSerializer
    search_fields = ['id', 'names__name']
    filter_backends = (SearchFilter, OrderingFilter,)
    ordering_fields = ['kills', 'deaths', 'ff_kills', 'playtime']

    @action(detail=False)
    def damage_type_kills(self, request):
        killer_id = request.query_params.get('killer_id', None)
        frags = models.Frag.objects.all()
        if killer_id is not None:
            frags = frags.filter(killer_id=killer_id)
        frags = frags.values('damage_type_id').annotate(kills=Count('damage_type_id')).order_by('-kills')
        paginator = LimitOffsetPagination()
        frags = paginator.paginate_queryset(frags, request)
        data = list(map(lambda x: {'damage_type_id': x['damage_type_id'], 'kills': x['kills']}, frags))
        return paginator.get_paginated_response(data)

    @action(detail=True)
    def stats(self, request, pk):
        player = models.Player.objects.get(id=pk)
        kd_ratio = player.kills / player.deaths if player.deaths != 0 else 0.0
        ff_kill_ratio = player.ff_kills / player.kills if player.kills != 0 else 0.0
        ff_death_ratio = player.ff_deaths / player.deaths if player.deaths != 0 else 0.0
        return JsonResponse({
            'kills': player.kills,
            'deaths': player.deaths,
            'kd_ratio': kd_ratio,
            'ff_kills': player.ff_kills,
            'ff_deaths': player.ff_deaths,
            'ff_kill_ratio': ff_kill_ratio,
            'ff_death_ratio': ff_death_ratio,
            'playtime': player.playtime
            # 'last_round_at': last_round_at
        })

    @action(detail=True)
    def sessions(self, request, pk):
        # TODO: different types of sessions (per day)
        player = models.Player.objects.get(id=pk)
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

    @action(detail=False)
    def most_kills(self, request):
        data = models.Frag.objects.values('killer').annotate(count=Count('id')).order_by('-count')
        paginator = LimitOffsetPagination()
        data = paginator.paginate_queryset(data, request)
        results = []
        for datum in data:
            player = models.Player.objects.get(pk=datum['killer'])
            result = {
                'count': datum['count'],
                'player': {
                    'id': player.id,
                    'name': player.name
                }
            }
            results.append(result)
        return paginator.get_paginated_response(results)


class DamageTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.DamageTypeClass.objects.all().order_by('id')
    serializer_class = serializers.DamageTypeClassSerializer
    search_fields = ['id']


class FragViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Frag.objects.all()
    serializer_class = serializers.FragSerializer

    def get_queryset(self):
        queryset = models.Frag.objects.all()
        map_id = self.request.query_params.get('map_id', None)
        killer_id = self.request.query_params.get('killer_id', None)
        # if map_id is not None:
            # queryset = queryset.filter(round__map_id=map_id)
        if killer_id is not None:
            queryset = queryset.filter(killer__id=killer_id)
        return queryset

    @action(detail=False)
    # TODO: this is massively inefficient, use aggregation/rounding to speed this up!
    def range_histogram(self, request):
        damage_type_ids = request.query_params.getlist('damage_type_ids[]', None)
        if damage_type_ids is None:
            raise MissingParametersException(['damage_type_id'])
        bin_size_in_meters = 5
        bin_size = bin_size_in_meters * 60.352
        data = {}
        for damage_type_id in damage_type_ids:
            bins = []
            frags = models.Frag.objects.filter(damage_type__id=damage_type_id)
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


class VehicleFragViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.VehicleFrag.objects.all()
    serializer_class = serializers.VehicleFragSerializer


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Event.objects.all()
    serializer_class = serializers.EventSerializer


class MapViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Map.objects.order_by('name')
    serializer_class = serializers.MapSerializer
    search_fields = ['name']

    @action(detail=True)
    def summary(self, request, pk):
        rounds = models.Round.objects.filter(log__map_id=pk)
        round_count = rounds.count()
        axis_wins = rounds.filter(winner=0).count()
        allied_wins = rounds.filter(winner=1).count()
        axis_deaths = models.Frag.objects.filter(round__log__map_id=pk, victim_team_index=0).count()
        allied_deaths = models.Frag.objects.filter(round__log__map_id=pk, victim_team_index=1).count()
        return JsonResponse({
            'round_count': round_count,
            'axis_wins': axis_wins,
            'allied_wins': allied_wins,
            'axis_deaths': axis_deaths,
            'allied_deaths': allied_deaths
        })

    @action(detail=True)
    def heatmap(self, request, pk):
        frags = models.Frag.objects.filter(round__log__map_id=pk)
        data = list(map(lambda x: x.victim_location, frags.all()))
        return JsonResponse({
            'data': data
        })


class TextMessageFilterSet(django_filters.rest_framework.FilterSet):
    message = django_filters.rest_framework.CharFilter(field_name='message', lookup_expr='icontains')
    map = django_filters.rest_framework.CharFilter(field_name='log__map', lookup_expr='exact')

    class Meta:
        model = models.TextMessage
        fields = ('log', 'sender', 'message', 'type', 'map', 'team_index')


class TextMessageViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.TextMessage.objects.all()
    serializer_class = serializers.TextMessageSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = TextMessageFilterSet

    @action(detail=False)
    def words(self, request):
        # TODO: reverse-lookup
        word_counts = dict()
        text_message_filter = TextMessageFilterSet(request.GET, queryset=self.queryset)
        for text_message in text_message_filter.qs:
            words = text_message.message.replace('.', ' ').replace(',', ' ').lower().split()
            # TODO: remove punctuation marks
            for word in words:
                if word not in word_counts:
                    word_counts[word] = 0
                word_counts[word] += 1
        # TODO: import this from a file, maybe
        excludes = ['', 'a', 'an', 'the', 'and', 'but', 'for', 'nor', 'or', 'so', 'yet', 'then', 'i', 'at', 'to', 'is', 'on', 'this', 'are', 'it', 'of', 'can', 'they', 'that', 'where', 'here', 'in', 'be', 'no', 'yes', 'our', 'has', 'it\'s', 'what', 'us', 'im', 'get', 'do', 'dont', 'with', 'have', 'from', 'was', 'by', 'just', 'there', 'your']
        for exclude in excludes:
            try:
                del word_counts[exclude]
            except KeyError:
                pass
        word_counts = [{'text': k, 'value': v} for (k, v) in word_counts.items()]
        word_counts.sort(key=lambda x: x['value'], reverse=True)
        return JsonResponse({'data': word_counts[:50]})

    @action(detail=False)
    def summary(self, request):
        text_message_filter = TextMessageFilterSet(request.GET, queryset=self.queryset)
        axis_messages = text_message_filter.qs.filter(team_index=0)
        allies_message = text_message_filter.qs.filter(team_index=1)
        axis_types = {x['type']: x['count'] for x in axis_messages.values('type').annotate(count=Count('type'))}
        allies_types = {x['type']: x['count'] for x in allies_message.values('type').annotate(count=Count('type'))}
        data = {'axis': {'total': axis_messages.count(), 'types': axis_types},
                'allies': {'total': allies_message.count(), 'types': allies_types}}
        return JsonResponse(data)



class LogViewSet(viewsets.ModelViewSet):
    queryset = models.Log.objects.all()
    serializer_class = serializers.LogSerializer


    @transaction.atomic
    def create(self, request, *args, **kwargs):
        start = time.time()
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
            models.Log.objects.get(crc=crc)
            return Response(None, status=status.HTTP_409_CONFLICT, headers={})
        except ObjectDoesNotExist:
            pass

        if semver.compare(data['version'][1:], '8.3.0') < 0:
            data = {'success': False, 'error': 'Log file version {} is unsupported.'.format(data['version'][1:])}
            return JsonResponse(data, status=status.HTTP_406_NOT_ACCEPTABLE)

        log = models.Log()
        log.crc = crc
        log.version = data['version']

        map_data = data['map']
        log.map = models.Map(map_data['name'])
        log.map.bounds_ne_x = map_data['bounds']['ne'][0]
        log.map.bounds_ne_y = map_data['bounds']['ne'][1]
        log.map.bounds_sw_x = map_data['bounds']['sw'][0]
        log.map.bounds_sw_y = map_data['bounds']['sw'][1]
        log.map.offset = map_data['offset']
        log.map.save()

        log.save()

        for player_data in data['players']:
            try:
                player = models.Player.objects.get(id=player_data['id'])
            except ObjectDoesNotExist:
                player = models.Player(id=player_data['id'])
                player.save()
            for session_data in player_data['sessions']:
                session = models.Session()
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
                    player_name = models.PlayerName(name=name)
                    player_name.save()
                    player.save()
                    player.names.add(player_name)
            player.save()
            log.players.add(player)

        for text_message_data in data['text_messages']:
            if(isinstance(text_message_data['sender'], str)):
              # filter out special IDs (e.g. admins)
              continue
            text_message = models.TextMessage()
            text_message.log = log
            text_message.type = text_message_data['type']
            text_message.message = text_message_data['message']
            text_message.sender = models.Player(id=text_message_data['sender'])
            text_message.sent_at = parser.parse(text_message_data['sent_at'])
            text_message.team_index = text_message_data['team_index']
            text_message.squad_index = text_message_data['squad_index']
            text_message.save()

        for round_data in data['rounds']:
            round = models.Round()
            round.started_at = parser.parse(round_data['started_at'])
            round.ended_at = None if round_data['ended_at'] is None else parser.parse(round_data['ended_at'])
            round.winner = round_data['winner']
            round.log = log
            round.save()

            for frag_data in round_data['frags']:
                frag = models.Frag()
                frag.damage_type = models.DamageTypeClass.objects.get_or_create(id=frag_data['damage_type'])[0]
                frag.hit_index = frag_data['hit_index']
                frag.time = frag_data['time']
                frag.killer = models.Player.objects.get(id=frag_data['killer']['id'])
                frag.killer_team_index = frag_data['killer']['team']
                frag.killer_location_x = frag_data['killer']['location'][0]
                frag.killer_location_y = frag_data['killer']['location'][1]
                frag.killer_location_z = frag_data['killer']['location'][2]
                if frag_data['killer']['pawn'] is not None:
                    frag.killer_pawn_class = models.PawnClass.objects.get_or_create(classname=frag_data['killer']['pawn'])[0]
                if frag_data['killer']['vehicle'] is not None:
                    frag.killer_vehicle = models.PawnClass.objects.get_or_create(classname=frag_data['killer']['vehicle'])[0]
                frag.victim = models.Player.objects.get(id=frag_data['victim']['id'])
                frag.victim_team_index = frag_data['victim']['team']
                frag.victim_location_x = frag_data['victim']['location'][0]
                frag.victim_location_y = frag_data['victim']['location'][1]
                frag.victim_location_z = frag_data['victim']['location'][2]
                if frag_data['victim']['pawn'] is not None:
                    frag.victim_pawn_class = models.PawnClass.objects.get_or_create(classname=frag_data['victim']['pawn'])[0]
                if frag_data['victim']['vehicle'] is not None:
                    frag.killer_vehicle = models.PawnClass.objects.get_or_create(classname=frag_data['victim']['vehicle'])[0]
                frag.distance = np.linalg.norm(np.subtract(frag.victim_location, frag.killer_location))
                frag.round = round
                frag.save()

            for vehicle_frag_data in round_data['vehicle_frags']:
                vehicle_frag = models.VehicleFrag()
                vehicle_frag.round = round
                vehicle_frag.time = vehicle_frag_data['time']
                vehicle_frag.damage_type = models.DamageTypeClass.objects.get_or_create(id=vehicle_frag_data['damage_type'])[0]
                vehicle_frag.killer = models.Player.objects.get(id=vehicle_frag_data['killer']['id'])
                vehicle_frag.killer_team_index = vehicle_frag_data['killer']['team']
                vehicle_frag.killer_location_x = vehicle_frag_data['killer']['location'][0]
                vehicle_frag.killer_location_y = vehicle_frag_data['killer']['location'][1]
                vehicle_frag.killer_location_z = vehicle_frag_data['killer']['location'][2]
                if vehicle_frag_data['killer']['pawn'] is not None:
                    vehicle_frag.killer_pawn_class = models.PawnClass.objects.get_or_create(classname=vehicle_frag_data['killer']['pawn'])[0]
                if vehicle_frag_data['killer']['vehicle'] is not None:
                    vehicle_frag.killer_vehicle_class = models.PawnClass.objects.get_or_create(classname=vehicle_frag_data['killer']['vehicle'])[0]
                vehicle_frag.vehicle_class = models.PawnClass.objects.get_or_create(classname=vehicle_frag_data['destroyed_vehicle']['vehicle'])[0]
                vehicle_frag.vehicle_team_index = vehicle_frag_data['destroyed_vehicle']['team']
                vehicle_frag.vehicle_location_x = vehicle_frag_data['destroyed_vehicle']['location'][0]
                vehicle_frag.vehicle_location_x = vehicle_frag_data['destroyed_vehicle']['location'][1]
                vehicle_frag.vehicle_location_x = vehicle_frag_data['destroyed_vehicle']['location'][2]
                vehicle_frag.distance = np.linalg.norm(np.subtract(vehicle_frag.vehicle_location, vehicle_frag.killer_location))
                vehicle_frag.save()

            for rally_point_data in round_data['rally_points']:
                rally_point = models.RallyPoint()
                rally_point.team_index = rally_point_data['team_index']
                rally_point.squad_index = rally_point_data['squad_index']
                rally_point.player = models.Player.objects.get(id=rally_point_data['player_id'])
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
                construction = models.Construction()
                try:
                    construction_class = models.ConstructionClass.objects.get(classname=construction_data['class'])
                except ObjectDoesNotExist:
                    construction_class = models.ConstructionClass(classname=construction_data['class'])
                    construction_class.save()
                construction.classname = construction_class
                construction.player = models.Player.objects.get(id=construction_data['player_id'])
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
                    event = models.Event()
                    event.type = event_data['type']
                    event.data = json.dumps(event_data['data'])
                    event.round = round
                    event.save()

        log.save()

        # Recalculate all aggregate stats for players involved in the game.
        for player in log.players.all():
            player.calculate_stats()

        # TODO: store the log on disk, gzip'd probably
        log_path = os.path.join('storage', 'logs', str(crc) + '.log')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        json.dump(data, open(log_path, 'w'))
        end = time.time()
        logging.info("Benchmarking %s, time elapsed: %ds", request.data['log'].name, end - start)

        return Response({}, status=status.HTTP_201_CREATED, headers={})


class RoundFilterSet(django_filters.rest_framework.FilterSet):
    map = django_filters.rest_framework.CharFilter(method='filter_map')

    class Meta:
        model = models.Round
        fields = ('map',)

    def filter_map(self, queryset, name, value):
        if value:
            queryset = queryset.annotate(mapf=F('log__map__name')).filter(mapf=value)
        return queryset


class PatronViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Patron.objects.all()
    serializer_class = serializers.PatronSerializer
    search_fields = ['player__id']


class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Announcement.objects.all()
    serializer_class = serializers.AnnouncementSerializer

    @action(detail=False)
    def latest(self, request):
        queryset = models.Announcement.objects.filter(is_published=True).order_by('-created_at')
        if queryset.count() == 0:
            return Response(status=204)
        announcement = queryset.first()
        data = serializers.AnnouncementSerializer(instance=announcement).data
        return JsonResponse(data)


class RoundViewSet(viewsets.ReadOnlyModelViewSet):
    model = models.Round
    queryset = models.Round.objects.all().order_by('-started_at')
    serializer_class = serializers.RoundSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = RoundFilterSet

    @action(detail=True)
    def summary(self, request, pk):
        round = models.Round.objects.get(pk=pk)
        deaths = models.Frag.objects.filter(round=round).count()
        axis_deaths = models.Frag.objects.filter(round=round, victim_team_index=0).count()
        allied_deaths = models.Frag.objects.filter(round=round, victim_team_index=1).count()
        data = {
            'kills': deaths,
            'axis_deaths': axis_deaths,
            'allied_deaths': allied_deaths
        }
        return JsonResponse(data)

    @action(detail=True)
    def scoreboard(self, request, pk):
        # add sorting
        round = models.Round.objects.get(pk=pk)
        paginator = LimitOffsetPagination()
        player_ids = list(map(lambda x: x.id, round.log.players.all()))
        players = models.Player.objects.filter(id__in=player_ids)
        players = paginator.paginate_queryset(players, request)
        data = []
        for player in players:
            kills = models.Frag.objects.filter(round=round, killer=player).count()
            deaths = models.Frag.objects.filter(round=round, victim=player).count()
            tks = models.Frag.objects.filter(round=round, killer=player, killer_team_index=F('victim_team_index')).count()
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
        round = models.Round.objects.get(pk=pk)
        player_id = request.GET['player_id']
        player = models.Player.objects.get(pk=player_id)
        frags = models.Frag.objects.filter(round=round, killer=player)
        kills = list(frags.values('damage_type').annotate(total=Count('damage_type')).order_by('total').annotate(longest=Max('distance')))
        return JsonResponse({
            'kills': kills
        })
        # longest range kill
        # aggregate kills by damage type
        # summary of frags for the player

    @action(detail=True)
    def frags(self, request, pk):
        round = models.Round.objects.get(pk=pk)
        frags = models.Frag.objects.filter(round=round)
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
        round = models.Round.objects.get(pk=pk)
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



class RallyPointFilterSet(django_filters.rest_framework.FilterSet):
    class Meta:
        model = models.RallyPoint
        fields = ('round', 'player')


class RallyPointViewSet(viewsets.ReadOnlyModelViewSet):
    model = models.RallyPoint
    queryset = models.RallyPoint.objects.all()
    serializer_class = serializers.RallyPointSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = RallyPointFilterSet


def damage_type_friendly_fire(request):
    damage_types = models.DamageTypeClass.objects.all()
    results = []
    for damage_type in damage_types:
        frags = models.Frag.objects.filter(damage_type=damage_type)
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

import datetime


def top_kills_this_week(request):
    # each round/log that started last week
    # now minus 7 days
    started_at = datetime.datetime.now() - datetime.timedelta(days=7)
    rounds = models.Round.objects.filter(started_at__gte=started_at)
    # all frags for all rounds
    frags = models.Frag.objects.filter(round__in=rounds)
    # TODO: now group by killer

def easter(request):
    player_counts = dict()
    for event in models.Event.objects.filter(type='egg_found'):
        data = json.loads(event.data)
        player_id = data['player_id']
        if player_id not in player_counts:
            player_counts[player_id] = 0
        player_counts[player_id] += 1
    player_counts = [x for x in player_counts.items()]
    player_counts = sorted(player_counts, key=lambda x: x[1])
    player_counts = {k:v for k,v in player_counts}
    return JsonResponse(player_counts)
