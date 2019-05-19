from django.contrib import admin
from django.db import models
from .models import Patron, Player

# Register your models here.
class PatronAdmin(admin.ModelAdmin):
    raw_id_fields = ('player',)
    autocomplete_fields = ('player',)
    list_display = ('player', 'tier')
    # get name !!

class PlayerAdmin(admin.ModelAdmin):
    search_fields = ('id', 'names__name')

admin.site.register(Patron, PatronAdmin)
admin.site.register(Player, PlayerAdmin)