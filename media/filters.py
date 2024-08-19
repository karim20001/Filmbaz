# your_app/filters.py

import django_filters
from django.db.models import Count, Q, Subquery, OuterRef, Exists
from django.utils import timezone
from datetime import timedelta

from .models import Show, Movie, UserEpisode, UserMovie

class ShowFilter(django_filters.FilterSet):
    genres = django_filters.CharFilter(method='filter_by_genres')
    exclude_user_shows = django_filters.BooleanFilter(method='filter_exclude_user_shows')

    class Meta:
        model = Show
        fields = ['genres', 'exclude_user_shows']

    def filter_by_genres(self, queryset, name, value):
        genres = value.split(',')
        return queryset.filter(genres__name__in=genres).distinct()

    def sort_by(self, queryset, name, value):
        user = self.request.user

        if value == 'top_matches':
            watched_genres = user.user_shows.values_list('show__genres', flat=True)
            return queryset.annotate(shared_genres_count=Count('genres', filter=Q(genres__in=watched_genres)))\
                           .order_by('-shared_genres_count')

        elif value == 'trending':
            four_months_ago = timezone.now() - timedelta(days=120)
            # Subquery to filter shows that had an episode watched in the last 4 months
            recent_activity = UserEpisode.objects.filter(
                episode__show=OuterRef('pk'),
                watch_date__gte=four_months_ago
            )
            return queryset.annotate(
                trending_count=Count('user_shows__user', distinct=True),
                has_recent_activity=Exists(recent_activity)
            ).filter(has_recent_activity=True).order_by('-trending_count')

        elif value == 'most_watched':
            # Filter shows by how many unique users have watched any episodes
            return queryset.annotate(
                watch_count=Count('episodes__user_episodes__user', distinct=True)
            ).order_by('-watch_count')

        elif value == 'watched_by_friends':
            # Get the list of user followings
            followings = self.request.user.following.values_list('follow_id', flat=True)
            # Subquery to filter shows watched by the user's followings
            friends_activity = UserEpisode.objects.filter(
                episode__show=OuterRef('pk'),
                user__in=followings
            )
            return queryset.annotate(
                friend_watch_count=Count('episodes__user_episodes__user', distinct=True),
                has_friend_activity=Exists(friends_activity)
            ).filter(has_friend_activity=True).order_by('-friend_watch_count')

        elif value == 'most_added':
            # Order shows by the number of users that have added them
            return queryset.annotate(
                added_count=Count('user_shows__user', distinct=True)
            ).order_by('-added_count')

        return queryset

    def filter_exclude_user_shows(self, queryset, name, value):
        if value:
            return queryset.exclude(user_shows__user=self.request.user)
        return queryset

class MovieFilter(django_filters.FilterSet):
    genres = django_filters.CharFilter(method='filter_by_genres')
    exclude_user_movies = django_filters.BooleanFilter(method='filter_exclude_user_movies')

    class Meta:
        model = Movie
        fields = ['genres', 'exclude_user_movies'] 

    def filter_by_genres(self, queryset, name, value):
        genres = value.split(',')
        return queryset.filter(genres__name__in=genres).distinct()

    def sort_by(self, queryset, name, value):
        user = self.request.user

        if value == 'top_matches':
            watched_genres = user.user_movies.values_list('movie__genres', flat=True)
            return queryset.annotate(shared_genres_count=Count('genres', filter=Q(genres__in=watched_genres)))\
                           .order_by('-shared_genres_count')

        elif value == 'trending':
            four_months_ago = timezone.now() - timedelta(days=120)
            # Subquery to filter movies that had an episode watched in the last 4 months
            recent_activity = UserMovie.objects.filter(
                movie=OuterRef('pk'),
                added_date__gte=four_months_ago
            )
            return queryset.annotate(
                trending_count=Count('user_movies__user', distinct=True),
                has_recent_activity=Exists(recent_activity)
            ).filter(has_recent_activity=True).order_by('-trending_count')

        elif value == 'most_watched':
            # Filter movies by how many unique users have watched movie
            return queryset.filter(user_movies__watched=True).annotate(
                watch_count=Count('user_movies__user', distinct=True)
            ).order_by('-watch_count')

        elif value == 'watched_by_friends':
            # Get the list of user followings
            followings = self.request.user.following.values_list('follow_id', flat=True)
            # Subquery to filter movies watched by the user's followings
            friends_activity = UserMovie.objects.filter(
                movie=OuterRef('pk'),
                user__in=followings,
                watched = True
            )
            return queryset.annotate(
                friend_watch_count=Count('user_movies__user', distinct=True),
                has_friend_activity=Exists(friends_activity)
            ).filter(has_friend_activity=True).order_by('-friend_watch_count')

        elif value == 'most_added':
            # Order movies by the number of users that have added them
            return queryset.annotate(
                added_count=Count('user_movies__user', distinct=True)
            ).order_by('-users_added_count')

        return queryset

    def filter_exclude_user_movies(self, queryset, name, value):
        if value:
            return queryset.exclude(user_movies__user=self.request.user)
        return queryset
