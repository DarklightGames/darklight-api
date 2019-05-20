from django.contrib import admin
from django.db import models
from .models import Patron, Player, Announcement

# Register your models here.
class PatronAdmin(admin.ModelAdmin):
    raw_id_fields = ('player',)
    autocomplete_fields = ('player',)
    list_display = ('player', 'tier')
    # get name !!

class PlayerAdmin(admin.ModelAdmin):
    search_fields = ('id', 'names__name')


class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'is_published')
    pass

admin.site.register(Patron, PatronAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Announcement, AnnouncementAdmin)