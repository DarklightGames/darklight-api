from django.contrib import admin
from django.db import models
from .models import Patron, Player, Announcement, Report

# Register your models here.
class PatronAdmin(admin.ModelAdmin):
    raw_id_fields = ('player',)
    list_display = ('player', 'tier')
    # get name !!

class PlayerAdmin(admin.ModelAdmin):
    search_fields = ('id',)
    exclude = ('names', 'sessions')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'is_published')
    pass

class ReportAdmin(admin.ModelAdmin):
    raw_id_fields = ('offender',)
    list_display = ('author', 'offender', 'text',)
    exclude = ('author',)

    def save_model(self, request, obj, form, change):
        obj.author = request.user
        obj.save()

admin.site.register(Patron, PatronAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Announcement, AnnouncementAdmin)