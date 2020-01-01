from django.contrib import admin
from django.db import models
from .models import Patron, Player, Announcement, Report, TextMessage, Event, Log
from django_admin_listfilter_dropdown.filters import DropdownFilter
from admin_auto_filters.filters import AutocompleteFilter
from prettyjson import PrettyJSONWidget


class PatronAdmin(admin.ModelAdmin):
    raw_id_fields = ('player',)
    list_display = ('player', 'tier')


class PlayerAdmin(admin.ModelAdmin):
    search_fields = ('id', 'names__name')
    exclude = ('names', 'sessions')
    list_display = ['id', 'name', 'playtime', 'ips']
    list_filter = []

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'is_published')


class LogAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at')


class ReportAdmin(admin.ModelAdmin):
    raw_id_fields = ('offender',)
    list_display = ('author', 'offender', 'text',)
    exclude = ('author',)

    def save_model(self, request, obj, form, change):
        obj.author = request.user
        obj.save()


class SenderFilter(AutocompleteFilter):
    title = 'Sender'
    field_name = 'sender'


class TextMessageAdmin(admin.ModelAdmin):

    class Media:
        pass

    list_display = ('id', 'sender', 'type', 'message', 'sent_at', 'team_index', 'squad_index')
    list_filter = [SenderFilter, ('type', DropdownFilter), ('sent_at', admin.DateFieldListFilter)]
    search_fields = ('message',)
    autocomplete_fields = ('sender',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class EventAdmin(admin.ModelAdmin):
    list_display = ('type', 'data')
    list_filter = [('type', DropdownFilter)]

    formfield_overrides = {
        models.TextField: {'widget': PrettyJSONWidget}
    }

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(Patron, PatronAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(TextMessage, TextMessageAdmin)
admin.site.register(Announcement, AnnouncementAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Log, LogAdmin)
