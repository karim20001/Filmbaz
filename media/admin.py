from django.contrib import admin
from .models import Genre, Show, Episode, Movie, Actor, Cast, UserShow, UserEpisode, UserMovie, Follow, Comment, Notification

admin.site.register(Genre)
admin.site.register(Show)
admin.site.register(Episode)
admin.site.register(Movie)
admin.site.register(Actor)
admin.site.register(Cast)
admin.site.register(UserShow)
admin.site.register(UserEpisode)
admin.site.register(UserMovie)
admin.site.register(Follow)
admin.site.register(Comment)
admin.site.register(Notification)