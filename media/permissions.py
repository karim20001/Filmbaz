from rest_framework import permissions
import datetime
from .models import UserEpisode

class MediaReleaseDate(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.release_date <= datetime.date.today()


class AuthenticateOwnerComment(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return obj.user == request.user
    

class WatchedEpisodeByUser(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return True
        # return UserEpisode.objects.filter(user=request.user, episode=obj).exists()