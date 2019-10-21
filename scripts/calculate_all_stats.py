from api.api.models import Player

for player in Player.objects.all():
    player.calculate_stats()
    