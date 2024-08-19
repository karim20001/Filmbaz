from rest_framework import permissions
import datetime
from .models import UserEpisode, UserShow

class MediaReleaseDate(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.release_date <= datetime.date.today()


class AuthenticateOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return obj.user == request.user
       
    

class WatchedEpisodeByUser(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        user_episode = UserEpisode.objects.filter(user=request.user, episode=obj).exists()
        return user_episode
        
        # return UserEpisode.objects.filter(user=request.user, episode=obj).exists()

class WatchedShowByUser(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        user_show = UserShow.objects.filter(user=request.user, show=obj).first()
        return user_show and user_show.status
        