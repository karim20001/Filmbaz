from django.shortcuts import render, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, mixins, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from urllib.parse import urlparse
from collections import defaultdict
from operator import attrgetter
from django.db.models import Count, Q, OuterRef, Subquery, Max, Sum, F, ExpressionWrapper, IntegerField, Prefetch, Avg, Exists
from django.db.models.functions import Coalesce
import datetime
from django.contrib.auth import get_user_model
from .models import Actor, UserMovie, Movie, Cast, Comment, UserEpisode, Episode, Show, UserShow, Genre, Follow
from .serializers import (ActorMovieSerializer, ActorSerializer, ActorShowSerializer, FollowerSerializer, FollowingSerializer, LastWatchedUserSerializer, MovieWatchListSerializer, MovieWatchersSerializers, MovieWithLastWatchersSerializer, ProfileMovieSerializer, ProfileShowSerializer,
                          SingleMovieSerializer,
                          UserMovieSerialzier,
                          CommentSerializer,
                          ShowWatchListSerialzier,
                          ShowSerializer,
                          UserShowSerializer,
                          EpisodeSerializer,
                          SingleEpisodeSerializer,
                          UserEpisodeSerializer,
                          SimilarShowSerializer,
                          SimilarMovieSerializer,
                          ShowWithLastWatchersSerializer,
                          SearchMovieSerializer,
                          SearchShowSerializer,
                          SearchUserSerializer,
                          WatchersSerializers,
                          )
from core.serializers import SimpleUserSerializer, UserGetSerializer, UserUpdateSerializer
from .permissions import AuthenticateOwner, WatchedEpisodeByUser, WatchedShowByUser
from .paginations import CustomPagination
from .filters import ShowFilter, MovieFilter

class MovieWatchListView(viewsets.ReadOnlyModelViewSet):
    serializer_class = MovieWatchListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Movie.objects.none()  # Default queryset, not used for custom action

    def get_serializer_context(self):
        # Add request to the serializer context
        return {'request': self.request}

    @action(detail=False, methods=['get'])
    def watchlist(self, request):
        user_movies = UserMovie.objects.filter(user=request.user, watched=False)
        movie_ids = user_movies.values_list('movie_id', flat=True)
        movies = Movie.objects.filter(id__in=movie_ids, release_date__lte=datetime.date.today())
        serializer = self.get_serializer(movies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        user_movies = UserMovie.objects.filter(user=request.user, watched=False)
        movie_ids = user_movies.values_list('movie_id', flat=True)
        movies = Movie.objects.filter(id__in=movie_ids, release_date__gt=datetime.date.today())
        serializer = self.get_serializer(movies, many=True)
        return Response(serializer.data)


class SingleMovieView(viewsets.ReadOnlyModelViewSet,
                      viewsets.GenericViewSet):
    
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        return Movie.objects.all()

    def get_serializer_context(self):
        return {'request': self.request}

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserMovieSerialzier
        return SingleMovieSerializer
    
    # def get_redirect_url(self, request):
    #     referer = request.META.get('HTTP_REFERER')
    #     return referer if referer else '/'
    
    def retrieve(self, request, pk=None):
        movie = get_object_or_404(Movie, pk=pk)
        serializer = self.get_serializer(movie)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add(self, request, *args, **kwargs):
        movie = self.get_object()
        user = request.user
        if UserMovie.objects.filter(movie=movie, user=user).exists():
            return Response({"detail": "already exists"}, status.HTTP_400_BAD_REQUEST)
        
        UserMovie.objects.create(movie=movie, user=user)
        movie.users_added_count += 1
        movie.save()
        return Response(status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk)
        if not movie.is_released:
            return Response({"message": "movie not released"}, status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        user_movie = UserMovie.objects.filter(user=user, movie=movie).first()

        data = request.data
        watched_status = data.pop('watched', None)

        if watched_status and watched_status == True and not user_movie:
            UserMovie.objects.create(user=user, movie=movie, watched=True, watched_date=datetime.datetime.now())
            movie.users_added_count += 1
            movie.save()
            return Response({'detail': 'movie add and watched'}, status.HTTP_201_CREATED)
        
        elif not user_movie:
            return Response({'detail': 'movie not watched yet'}, status.HTTP_400_BAD_REQUEST)

        if watched_status is not None:
            if not watched_status and user_movie.watched:
                # Reset all other fields to None if watched status is changed to False
                user_movie.is_favorite = False
                user_movie.user_rate = None
                user_movie.emoji = None
                user_movie.favorite_cast = None
                user_movie.watched_date = None

                user_movie.watched = watched_status
                user_movie.save()
                return Response({'message': 'Watched status updated and user movie data reset!'}, status=status.HTTP_200_OK)
            else:
                user_movie.watched = watched_status
                user_movie.watched_date = datetime.datetime.now()
                user_movie.save()
                return Response({'message': 'Watched status updated!'}, status=status.HTTP_200_OK)

        if not user_movie.watched:
            return Response({"message": "You must watch the movie before updating its details."}, status=status.HTTP_400_BAD_REQUEST)

        old_favorite_cast = user_movie.favorite_cast
        new_favorite_cast_id = data.get('favorite_cast')
        content_type = ContentType.objects.get(model='movie').id

        if Cast.objects.filter(id=new_favorite_cast_id, object_id=movie.id, content_type=content_type):

            if new_favorite_cast_id and (not old_favorite_cast or new_favorite_cast_id != old_favorite_cast.id):
                new_favorite_cast = get_object_or_404(Cast, id=new_favorite_cast_id)
                user_movie.favorite_cast = new_favorite_cast

        else:
            return Response({"detail": "cast is not related"}, status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(user_movie, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'update success'}, status.HTTP_200_OK)

    def destroy(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk)
        user = request.user
        user_movie = get_object_or_404(UserMovie, user=user, movie=movie)
        movie.users_added_count -= 1
        movie.save()
        user_movie.delete()
        return Response({'detail': 'user movie deleted'}, status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def watchers(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk)

        # Get the list of users that the current user is following
        following_users = request.user.following.values_list('follow', flat=True)

        # Query to get the last watched episode for each following user in the specific series
        queryset = UserMovie.objects.filter(
            movie=movie,
            user__in=following_users,
            watched=True
        ).annotate(
            latest_watch_date=Max('watched_date')
        ).order_by('-latest_watch_date')

        if not queryset:
            return Response(status=status.HTTP_404_NOT_FOUND)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MovieWatchersSerializers(page, many=True)
            return self.get_paginated_response({
                'name': movie.name,
                'watchers': serializer.data
            })

        serializer = MovieWatchersSerializers(queryset, many=True)
        return Response({
                'name': movie.name,
                'watchers': serializer.data
            })

    # def update_likes_for_favorite_cast(self, old_cast, new_cast):
    #     if old_cast:
    #         old_cast.likes -= 1
    #         old_cast.save()
    #     new_cast.likes += 1
    #     new_cast.save()

    # def update_users_rate(self, movie, old_rate, new_rate):
    #     if old_rate is not None:
    #         movie.users_rate = ((movie.users_rate * movie.usermovie_set.count()) - old_rate + new_rate) / movie.usermovie_set.count()
    #     else:
    #         movie.users_rate = ((movie.users_rate * (movie.usermovie_set.count() - 1)) + new_rate) / movie.usermovie_set.count()
    #     movie.save()
    
    # def update_likes_and_rate(self, movie, user_movie, decrement=False):
    #     if user_movie.favorite_cast:
    #         if decrement:
    #             user_movie.favorite_cast.likes -= 1
    #         else:
    #             user_movie.favorite_cast.likes += 1
    #         user_movie.favorite_cast.save()
        
    #     if user_movie.user_rate is not None:
    #         all_ratings = list(UserMovie.objects.filter(movie=movie).exclude(user_rate=None).values_list('user_rate', flat=True))
    #         if decrement:
    #             all_ratings.remove(user_movie.user_rate)
    #         movie.users_rate = sum(all_ratings) / len(all_ratings) if all_ratings else 0
    #         movie.save()


class CommentViewSet(mixins.CreateModelMixin,
                     mixins.DestroyModelMixin,
                     mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):

    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, AuthenticateOwner]

    def get_content_type(self):
        url = self.request.build_absolute_uri()
        parsed_url = urlparse(url)
        content_type = parsed_url.path.strip('/').split('/')

        if "episodes" in content_type:
            return "episode"
        elif "series" in content_type:
            return "show"
        else:
            return "movie"
    
    def get_content_type_pk(self, content_type):
        if content_type == 'episode':
            return self.kwargs['episodes_pk']
        
        elif content_type == 'show':
            return self.kwargs['series_pk']
        
        elif content_type == 'movie':
            return self.kwargs['movie_pk']
    
    def get_queryset(self):
        content_type = self.get_content_type()
        media_id = self.get_content_type_pk(content_type)
        return Comment.objects.filter(content_type__model=content_type, object_id=media_id, parent=None)\
            .select_related('user')\
            .prefetch_related('likes', 'replies', 'replies__likes', 'replies__user')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Include replies only for the retrieve action
        if self.action == 'retrieve':
            context['include_replies'] = True
        return context
    
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        content_type = self.get_content_type()
        data['content_type'] = ContentType.objects.get(model=content_type).id
        data['object_id'] = self.get_content_type_pk(content_type)
        serializer = self.get_serializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status.HTTP_201_CREATED)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = CommentSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='reply', url_name='sub_comment')
    def create_sub_comment(self, request, *args, **kwargs):
        parent_comment = get_object_or_404(Comment, pk=self.kwargs['pk'])
        data = request.data.copy()
        data['parent'] = parent_comment.id
        data['content_type'] = parent_comment.content_type.id
        data['object_id'] = parent_comment.object_id
        serializer = self.get_serializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status.HTTP_201_CREATED)
    
    @create_sub_comment.mapping.delete
    def delete_sub_comment(self, request, *args, **kwargs):
        comment = get_object_or_404(Comment, pk=self.kwargs['pk'], parent__isnull=False)
        comment.delete()
        return Response({"message": "reply deleted"}, status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def like(self, request, *args, **kwargs):
        comment = get_object_or_404(Comment, pk=self.kwargs['pk'])
        user = request.user

        if comment.likes.filter(id=user.id).exists():
            return Response({'message': 'You have already liked this comment.'}, status.HTTP_400_BAD_REQUEST)
        
        comment.likes.add(user)
        return Response({'message': 'Comment liked!'}, status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def unlike(self, request, *args, **kwargs):
        comment = get_object_or_404(Comment, pk=self.kwargs['pk'])
        user = request.user

        if not comment.likes.filter(id=user.id).exists():
            return Response({'message': 'You have not liked this comment.'}, status.HTTP_400_BAD_REQUEST)
        
        comment.likes.remove(user)
        return Response({'message': 'Comment unliked!'}, status.HTTP_204_NO_CONTENT)
    

# show section
class ShowWatchListView(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ShowWatchListSerialzier

    def get_queryset(self):
        return Episode.objects.all()

    @action(detail=False, methods=['get'])
    def watchlist(self, request):
        user = request.user
        # Watched History
        watched_history = UserEpisode.objects.filter(user=user).order_by('-watch_date')
        watched_episodes = [wh.episode for wh in watched_history]
        watched_serialized = self.get_serializer(watched_episodes, many=True).data

        # Watch Next (Episodes of shows the user has started watching but not yet finished)
        # Dictionary to hold the last watched episode per show
        last_watched = {}
        for ue in watched_history:
            show = ue.episode.show
            if show not in last_watched or (ue.episode.season > last_watched[show].season or (ue.episode.season == last_watched[show].season and ue.episode.episode_number > last_watched[show].episode_number)):
                last_watched[show] = ue.episode

        # List to hold the next episodes to watch
        next_episodes = []
        old_episodes = []
        time_threshold = timezone.now() - datetime.timedelta(weeks=4) # assuming 4 weeks as the threshold

        for show, last_episode in last_watched.items():
            next_episode = Episode.objects.filter(show=show, season=last_episode.season, episode_number=last_episode.episode_number + 1).first()
            if not next_episode:
                next_episode = Episode.objects.filter(show=show, season=last_episode.season + 1, episode_number=1).first()

            if next_episode:
                # Haven't Watched for a While
                if UserEpisode.objects.get(user=user, episode=last_episode).watch_date <= time_threshold:
                    old_episodes.append(next_episode)

                else:
                    next_episodes.append(next_episode)

        watch_next_serialized = self.get_serializer(next_episodes, many=True).data
        old_serialized = self.get_serializer(old_episodes, many=True).data

        response_data = {
            'watched_history': watched_serialized,
            'watch_next': watch_next_serialized,
            'havent_watched_for_a_while': old_serialized
        }

        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        user = request.user
        compelet_watched_shows = Show.objects.annotate(
            count_show_episodes = Count('episodes', filter=Q(episodes__is_released=True), distinct=True),
            count_user_episodes = Count('episodes', filter=Q(episodes__is_released=True, episodes__user_episodes__user=user), distinct=True)
        ).filter(count_show_episodes=F('count_user_episodes'))

        episodes = Episode.objects.filter(show__in=compelet_watched_shows, is_released=False)

        serializer = self.get_serializer(episodes, many=True)
        return Response(serializer.data)


class SingleShowView(viewsets.GenericViewSet):
    
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.action == 'retrieve':
            return Show.objects.all()
        else:
            return UserShow.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ShowSerializer
        else:
            return UserShowSerializer
    
    def get_serializer_context(self):
        return {'request': self.request}
    
    def get_permissions(self):
        if self.action == 'partial_update':
            permission_classes = [IsAuthenticated, WatchedShowByUser]
        else:
            permission_classes = [IsAuthenticated]
            
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        # Automatically set the user to the current authenticated user
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add(self, request, *args, **kwargs):
        # Extract the show ID from the URL's pk
        show_pk = kwargs.get('pk')
        show = get_object_or_404(Show, id=show_pk)

        if UserShow.objects.filter(user=request.user, show=show).exists():
            return Response({"detail": "already exists"}, status.HTTP_400_BAD_REQUEST)

        UserShow.objects.create(user=request.user, show=show, status=None)
        show.users_added_count += 1
        show.save()
        return Response(status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, pk):
        show = get_object_or_404(Show, id=pk)
        serializer = self.get_serializer(show)
        return Response(serializer.data)

    def partial_update(self, request, pk):
        show = get_object_or_404(Show, pk=pk)
        user_show = get_object_or_404(UserShow, user=request.user, show=show)
        if not user_show.status and request.data['status']:
            return Response({"detail": "can't update while not start show"}, status.HTTP_400_BAD_REQUEST)

        serializer = UserShowSerializer(user_show, request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "update success"}, status.HTTP_202_ACCEPTED)
    
    def destroy(self, request, pk):
        show = get_object_or_404(Show, pk=pk)
        user_show = get_object_or_404(UserShow, user=request.user, show=show)
        user_show.delete()
        show.users_added_count -= 1
        show.save()
        return Response({"message": "deleted"},  status.HTTP_204_NO_CONTENT)
    
    
    @action(detail=True, methods=['get'])
    def watchers(self, request, pk):
        show = get_object_or_404(Show, pk=pk)

        # Get the list of users that the current user is following
        following_users = request.user.following.values_list('follow', flat=True)

        # Query to get the last watched episode for each following user in the specific series
        queryset = UserEpisode.objects.filter(
            episode__show=show,
            user__in=following_users
        ).annotate(
            latest_watch_date=Max('watch_date')
        ).order_by('-latest_watch_date')

        if not queryset:
            return Response(status=status.HTTP_404_NOT_FOUND)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = WatchersSerializers(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = WatchersSerializers(queryset, many=True)
        return Response(serializer.data)


class EpisodeView(mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    
    queryset = Episode.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.action in ['list', 'retrieve', 'create']:
            show_id = self.kwargs.get('series_pk')
            return Episode.objects.filter(show__id=show_id).order_by('season', 'episode_number')
        
        else:
            return get_object_or_404(UserEpisode, user=self.request.user, episode__id=self.kwargs.get('pk'))
            
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EpisodeSerializer
        
        elif self.action == 'retrieve':
            return SingleEpisodeSerializer
        
        else:
            return UserEpisodeSerializer
    

    def get_permissions(self):
        if self.action == 'destroy' or self.action == 'partial_update':
            permission_classes = [IsAuthenticated, WatchedEpisodeByUser]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]
    
    def list(self, request, series_pk=None):
        queryset = self.get_queryset()
        grouped_episodes = defaultdict(list)

        for episode in queryset:
            serializer = self.get_serializer(episode)
            grouped_episodes[episode.season].append(serializer.data)

        return Response(grouped_episodes)
    
    @action(detail=True, methods=['post'])
    def add(self, request, *args, **kwargs):
        episode_id = self.kwargs['pk']
        episode = get_object_or_404(Episode, pk=episode_id)
        user = request.user

        if UserEpisode.objects.filter(user=user, episode=episode).exists():
            return Response({"detail": "episode already watched"}, status.HTTP_400_BAD_REQUEST)

        if not UserShow.objects.filter(user=user, show=episode.show).exists():
            UserShow.objects.create(user=user, show=episode.show)
            episode.show.users_added_count += 1
            episode.show.save()
        
        UserEpisode.objects.get_or_create(user=user, episode=episode)
        user_show = get_object_or_404(UserShow, user=user, show=episode.show)
        if user_show.status == None:
            user_show.status = user_show.status.WATCHING
            user_show.save()

        return Response({"detail": "Episode watched"}, status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_queryset()
        data = request.data

        if instance.user != request.user:
            return Response({"detail": "You do not have permission to modify this episode."}, status=status.HTTP_403_FORBIDDEN)

        old_favorite_cast = instance.favorite_cast
        new_favorite_cast_id = data.get('favorite_cast')
        content_type = ContentType.objects.get(model='episode').id

        if Cast.objects.filter(id=new_favorite_cast_id, object_id=instance.episode.id, content_type=content_type):

            if new_favorite_cast_id and (not old_favorite_cast or new_favorite_cast_id != old_favorite_cast.id):
                new_favorite_cast = get_object_or_404(Cast, id=new_favorite_cast_id)
                self.update_likes_for_favorite_cast(old_favorite_cast, new_favorite_cast)
                instance.favorite_cast = new_favorite_cast

        elif new_favorite_cast_id:
            return Response({"detail": "cast is not related"}, status.HTTP_400_BAD_REQUEST)
        
        old_user_rate = instance.user_rate
        new_user_rate = data.get('user_rate')

        if new_user_rate is not None and new_user_rate != old_user_rate:
            instance.user_rate = new_user_rate

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "update success"}, status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_queryset()

        if instance.user != request.user:
            return Response({"detail": "You do not have permission to modify this episode."}, status=status.HTTP_403_FORBIDDEN)

        instance.delete()
        return Response({"detail": "episode unwatched"}, status.HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        return {'request': self.request}

    def update_likes_for_favorite_cast(self, old_cast, new_cast):
        if old_cast:
            old_cast.likes -= 1
            old_cast.save()
        new_cast.likes += 1
        new_cast.save()

#discover Section

class DiscoverView(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Show.objects.none()

    def list(self, request):
        user = request.user
        user_followings = list(Follow.objects.filter(user=user).values_list('follow_id', flat=True))

        # Precompute and annotate fields in one go
        annotated_shows = Show.objects.annotate(
            watching_or_finished_count=Count('user_shows__user', distinct=True),
            average_users_rate=Coalesce(
                ExpressionWrapper(
                    Avg('episodes__user_episodes__user_rate') * 20, output_field=IntegerField()
                ), 0
            ),
            season_counts=Count('episodes__season', distinct=True),
            is_added=Exists(UserShow.objects.filter(user=user, show=OuterRef('pk')))
        )

        annotated_movies = Movie.objects.annotate(
            watchers_count=Count('user_movies', filter=Q(user_movies__watched=True)),
            avg_users_rate=Coalesce(
                ExpressionWrapper(
                    Avg('user_movies__user_rate') * 20, output_field=IntegerField()
                ), 0
            ),
            is_added=Exists(UserMovie.objects.filter(user=user, movie=OuterRef('pk')))
        )

        # 1. Top Shows: Shows with the most common genres that the user is watching
        user_genres = Genre.objects.filter(show__user_shows__user=user).distinct()
        top_shows = annotated_shows.filter(genres__in=user_genres).annotate(
            watch_count=Count('user_shows', filter=Q(user_shows__status=UserShow.WATCHING))
        ).order_by('-watch_count')[:10]

        # 2. Trending Shows: Shows added by users in the last 3 months
        three_months_ago = timezone.now() - datetime.timedelta(days=90)
        trending_shows = annotated_shows.filter(
            user_shows__added_date__gte=three_months_ago
        ).order_by('-users_added_count')[:10]

        # 3. Trending Movies: Movies added by users in the last 3 months
        trending_movies = annotated_movies.filter(
            user_movies__added_date__gte=three_months_ago
        ).order_by('-users_added_count')[:10]

        # 4. Last watched shows by friends
        last_watched_shows_data = UserEpisode.objects.filter(
            user__in=user_followings
        ).values('episode__show_id').annotate(last_watch_date=Max('watch_date')).order_by('-last_watch_date')[:10]

        show_ids = [item['episode__show_id'] for item in last_watched_shows_data]

         # Subquery to get the last UserEpisode for each user and show
        last_user_episode_subquery = UserEpisode.objects.filter(
            user=OuterRef('user'),
            episode__show=OuterRef('episode__show')
        ).order_by('-watch_date').values('pk')[:1]

        # Filter the UserEpisodes to be unique per user per show
        user_episode_prefetch = Prefetch(
            'user_episodes',
            queryset=UserEpisode.objects.filter(
                user__in=user_followings,
                pk__in=Subquery(last_user_episode_subquery)
            ).select_related('user', 'episode').order_by('-watch_date'),
            to_attr='prefetched_user_episodes'
        )

        # Fetch the shows with the prefetch applied
        shows = annotated_shows.filter(id__in=show_ids).prefetch_related(
            Prefetch(
                'episodes',
                queryset=Episode.objects.all().prefetch_related(user_episode_prefetch),
                to_attr='prefetched_episodes'
            )
        )

        # Process the prefetched data
        community_activity_data = []
        for show in shows:
            last_watchers = []
            for episode in getattr(show, 'prefetched_episodes', []):
                for user_episode in getattr(episode, 'prefetched_user_episodes', [])[:6]:
                    last_watchers.append(user_episode)
            
            community_activity_data.append(
            ShowWithLastWatchersSerializer(
                show,
                context={
                    'last_watchers': LastWatchedUserSerializer(last_watchers, many=True).data
                }
            ).data
        )

        # 5. Last watched movies by friends
        last_watched_movies = UserMovie.objects.filter(
            user__in=user_followings,
            watched=True
        ).values('movie_id').annotate(last_watch_date=Max('watched_date')).order_by('-last_watch_date')[:10]

        movie_ids = [item['movie_id'] for item in last_watched_movies]
        # Annotate and Prefetch related data with custom attribute `prefetched_user_movies`
        movies = annotated_movies.filter(id__in=movie_ids).prefetch_related(
            Prefetch(
                'user_movies',
                queryset=UserMovie.objects.filter(user__in=user_followings, watched=True).select_related('user').order_by('-watched_date'),
                to_attr='prefetched_user_movies'
            )
        )
        # Serialize the data
        top_shows_data = SimilarShowSerializer(top_shows, many=True).data
        trending_shows_data = SimilarShowSerializer(trending_shows, many=True).data
        trending_movies_data = SimilarMovieSerializer(trending_movies, many=True).data

        community_activity_movies_data = [
            MovieWithLastWatchersSerializer(
                movie,
                context = {
                    'last_watchers': LastWatchedUserSerializer(getattr(movie, 'prefetched_user_movies'), many=True).data
                }
            ).data
            for movie in movies
        ]

        # Combine into a single response
        combined_response = {
            'top_shows': top_shows_data,
            'trending_shows': trending_shows_data,
            'trending_movies': trending_movies_data,
            'community_activity': community_activity_data,
            'community_activity_movies': community_activity_movies_data
        }

        return Response(combined_response)


class SearchView(viewsets.GenericViewSet):
    queryset = Movie.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def list(self, request):
        query = request.query_params.get('q', '')

        # Filter movies and shows by name
        movies = list(Movie.objects.filter(name__icontains=query))
        shows = list(Show.objects.filter(name__icontains=query))

        # Combine and sort by 'users_added_count'
        combined_results = sorted(movies + shows, key=attrgetter('users_added_count'), reverse=True)

        # Apply pagination
        paginator = self.pagination_class()
        paginated_results = paginator.paginate_queryset(combined_results, request)

        # Serialize the results (handling different types)
        serialized_data = []
        for item in paginated_results:
            if isinstance(item, Movie):
                serialized_data.append(SearchMovieSerializer(item, context={'request': request}).data)
            elif isinstance(item, Show):
                serialized_data.append(SearchShowSerializer(item, context={'request': request}).data)

        return paginator.get_paginated_response(serialized_data)

    @action(detail=False, methods=['get'], url_path='users')
    def search_users(self, request):
        query = request.query_params.get('q', '')

        # Filter users by username
        users = get_user_model().objects.filter(username__icontains=query)

        # Apply pagination
        paginator = self.pagination_class()

        users_page = paginator.paginate_queryset(users, request)
        user_serializer = SearchUserSerializer(users_page, many=True)

        return paginator.get_paginated_response(user_serializer.data)


class FilterShowView(mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    queryset = Show.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = SearchShowSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ShowFilter

    def get_queryset(self):
        queryset = super().get_queryset()

        # Handle sorting manually since it's not a model field
        sort_by = self.request.query_params.get('sort_by', 'top_matches')
        filter_class = ShowFilter(data=self.request.query_params, request=self.request)
        
        if filter_class.is_valid():
            queryset = filter_class.qs

        # Apply custom sorting based on the sort_by parameter
        if sort_by:
            queryset = filter_class.sort_by(queryset, 'sort_by', sort_by)

        return queryset


class FilterMovieView(mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    queryset = Movie.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = SearchMovieSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = MovieFilter

    def get_queryset(self):
        queryset = super().get_queryset()

        # Handle sorting manually since it's not a model field
        sort_by = self.request.query_params.get('sort_by', 'top_matches')
        filter_class = MovieFilter(data=self.request.query_params, request=self.request)
        
        if filter_class.is_valid():
            queryset = filter_class.qs

        # Apply custom sorting based on the sort_by parameter
        if sort_by:
            queryset = filter_class.sort_by(queryset, 'sort_by', sort_by)

        return queryset


class ProfileView(viewsets.GenericViewSet):
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        user = self.request.user
        if self.action == 'retrieve':
            user_model = get_user_model()
            user = get_object_or_404(user_model, username=self.kwargs['pk'])
            
        movies = Movie.objects.filter(user_movies__user=user, user_movies__watched=True)\
            .order_by('-user_movies__watched_date')[:10]
        favorite_movies = Movie.objects.filter(user_movies__user=user, user_movies__watched=True, user_movies__is_favorite=True)\
            .order_by('-user_movies__watched_date')[:10]
        # Annotate each show with the latest `UserEpisode.watch_date` for the user
        shows = Show.objects.filter(
            episodes__user_episodes__user=user
        ).annotate(
            last_watched=Max('episodes__user_episodes__watch_date')
        ).order_by('-last_watched')

        favorite_shows = Show.objects.filter(
            episodes__user_episodes__user=user,
            user_shows__is_favorite=True
        ).annotate(
            last_watched=Max('episodes__user_episodes__watch_date')
        ).order_by('-last_watched')

        # Calculate total duration and count for watched episodes
        user_episode_stats = UserEpisode.objects.filter(
            user=user
        ).aggregate(
            total_episode_duration=Sum(F('episode__show__duration')),  # Sum the duration of watched episodes
            episode_count=Count('episode')  # Count the total number of watched episodes
        )

        # Calculate total duration and count for watched movies
        user_movie_stats = UserMovie.objects.filter(
            user=user, watched=True  # Only include watched movies
        ).aggregate(
            total_movie_duration=Sum(F('movie__duration')),  # Sum the duration of watched movies
            movie_count=Count('movie')  # Count the total number of watched movies
        )

        # Total duration for shows and movies
        total_show_duration = user_episode_stats['total_episode_duration'] or 0
        total_movie_duration = user_movie_stats['total_movie_duration'] or 0

        # Function to convert minutes into months, days, hours
        def convert_time(minutes):
            total_hours = minutes // 60
            remaining_minutes = minutes % 60
            total_days = total_hours // 24
            remaining_hours = total_hours % 24
            total_months = total_days // 30
            remaining_days = total_days % 30

            return {
                'months': total_months,
                'days': remaining_days,
                'hours': remaining_hours,
                'minutes': remaining_minutes
            }

        # Convert the time for shows and movies separately
        show_time_spent = convert_time(total_show_duration)
        movie_time_spent = convert_time(total_movie_duration)

        comment_count = Comment.objects.filter(user=user).count()
        follower_count = Follow.objects.filter(follow=user).count()
        following_count = Follow.objects.filter(user=user).count()

        return {'movies': movies, 'favorite_movies': favorite_movies, 'user': user,
                'shows': shows, 'favorite_shows': favorite_shows,
                'movie_count': user_movie_stats['movie_count'], 'episode_count': user_episode_stats['episode_count'],
                'show_time_spent': show_time_spent, 'movie_time_spent': movie_time_spent,
                'follower_count': follower_count, 'following_count': following_count, 'comment_count': comment_count}

    def get_valid_data(self):
        queryset = self.get_queryset()

        serializer_user = SimpleUserSerializer(queryset.get('user')).data
        serializer_movie = ProfileMovieSerializer(queryset.get('movies'), many=True).data
        serializer_favorite_movie = ProfileMovieSerializer(queryset.get('favorite_movies'), many=True).data
        serializer_show = ProfileShowSerializer(queryset.get('shows'), many=True).data
        serializer_favorite_show = ProfileShowSerializer(queryset.get('favorite_shows'), many=True).data
        movie_time_spent = queryset.get('movie_time_spent')
        show_time_spent = queryset.get('show_time_spent')

        data = {
            'user': serializer_user,
            'movies': serializer_movie,
            'favorite_movies': serializer_favorite_movie,
            'movie_stats': {
                'time_spent': movie_time_spent,
                'total_movies_watched': queryset.get('movie_count'),
            },
            'shows': serializer_show,
            'favorite_shows': serializer_favorite_show,
            'show_stats': {
                'time_spent': show_time_spent,
                'total_episodes_watched': queryset.get('episode_count'),
            },
            'follower_count': queryset.get('follower_count'),
            'following_count': queryset.get('following_count'),
            'comment_count': queryset.get('comment_count')
        }

        return data

    def list(self, request):
        user = request.user
        data = self.get_valid_data()
        user_serialzier = SimpleUserSerializer(user).data
        data['user'] = user_serialzier
        return Response(data)

    def retrieve(self, request, pk=None):
        data = self.get_valid_data()
        is_follow = Follow.objects.filter(user__username=pk, follow=request.user).exists()
        is_following = Follow.objects.filter(user=request.user, follow__username=pk).exists()
        data['is_follow'] = is_follow
        data['is_following'] = is_following
        return Response(data)

    @action(detail=False, methods=['get'], url_path='detail')
    def get_profile(self, request):
        user = request.user
        serializer = UserGetSerializer(user).data
        return Response(serializer)
    
    @action(detail=False, methods=['patch'], url_path='detail/edit')
    def update_profile(self, request):
        user = request.user
        data = request.data

        # if not data['username']:
        #     data['username'] = user.username

        # if not (data['password1'] or data['password2'] or data['password']):
        #     data['password'] = user.password
        #     data['password1'] = user.password
        #     data['password2'] = user.password

        serializer = UserUpdateSerializer(user, data=data, context={'request': request}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_202_ACCEPTED)
    
#############################################################################
    # Profile Movie Section
    # For the authenticated user
    @action(detail=False, methods=['get'], url_path='movies')
    def movies(self, request):
        user = request.user
        data = self.get_movies(user)
        return Response(data)

    # For a specific user by username
    @action(detail=True, methods=['get'], url_path='movies')
    def user_movies(self, request, pk=None):
        user_model = get_user_model()
        user = get_object_or_404(user_model, username=pk)
        if user.private and (not Follow.objects.filter(user=request.user, follow=user, is_accepted=True).exists()):
            return Response({"message": "You should follow this user first"}, status=status.HTTP_200_OK)
        data = self.get_movies(user)
        return Response(data)
    
    def get_movies(self, user):
        watched_movies = Movie.objects.filter(user_movies__user=user, user_movies__watched=True)\
            .order_by('user_movies__watched_date')
        unwatched_movies = Movie.objects.filter(user_movies__user=user, user_movies__watched=False)\
            .order_by('user_movies__added_date')

        serialized_watched = ProfileMovieSerializer(watched_movies, many=True).data
        serialized_unwatched = ProfileMovieSerializer(unwatched_movies, many=True).data

        data = {
            'watched_movies': serialized_watched,
            'unwatched_movies': serialized_unwatched
        }

        return data
############################################################
    # Profile Show section
    @action(detail=False, methods=['get'], url_path='shows')
    def shows(self, request):
        user = request.user
        data = self.categorized_show(user)
        return Response(data)
    
    @action(detail=True, methods=['get'], url_path='shows')
    def user_shows(self, request, pk):
        user_model = get_user_model()
        user = get_object_or_404(user_model, username=pk)
        if user.private and (not Follow.objects.filter(user=request.user, follow=user, is_accepted=True).exists()):
            return Response({"message": "You should follow this user first"}, status=status.HTTP_200_OK)
    
        data = self.categorized_show(user)
        return Response(data)
    
    def categorized_show(self, user):
        # Get categorized shows
        watching_shows = self.get_user_shows_by_status(user, 'در حال تماشا')
        stopped_shows = self.get_user_shows_by_status(user, 'متوقف شده')
        watch_later_shows = self.get_user_shows_by_status(user, 'برای بعد')
        have_not_started_yet = self.get_user_shows_by_status(user, None)
        finished_shows = self.get_finished_or_up_to_date_shows(user, is_finished=True)
        up_to_date_shows = self.get_finished_or_up_to_date_shows(user, is_finished=False)

        # Combine all categories into a response
        data = {
            'watching': watching_shows,
            'stopped': stopped_shows,
            'watch_later': watch_later_shows,
            'have_not_started_yet': have_not_started_yet,
            'finished': finished_shows,
            'up_to_date': up_to_date_shows,
        }

        return data

    def get_user_shows_by_status(self, user, status):
        """ Get user shows based on their watch status and calculate watched percentage. """
        user_shows = Show.objects.filter(user_shows__user=user, user_shows__status=status) \
            .annotate(last_watched_episode_date=Max('episodes__user_episodes__watch_date')) \
            .order_by('-last_watched_episode_date')

        # Annotate with watched data
        user_shows = self.annotate_with_watched_data(user_shows, user)
        return self.serialize_shows(user_shows)
    
    def get_finished_or_up_to_date_shows(self, user, is_finished):
        """ Get shows where user has watched all episodes. Separate based on end_year (finished or up to date). """
        end_year_filter = Q(end_year__isnull=not is_finished)
        
        shows = Show.objects.filter(user_shows__user=user).filter(end_year_filter)\
            .annotate(last_watched_episode_date=Max('episodes__user_episodes__watch_date')) \
            .order_by('-last_watched_episode_date')

        # Annotate with watched data
        shows = self.annotate_with_watched_data(shows, user)

        # Filter shows where the user has watched all episodes
        completed_shows = [show for show in shows if show.watched_episodes == show.total_episodes]

        return self.serialize_shows(completed_shows)

    def annotate_with_watched_data(self, queryset, user):
        """ Annotate queryset with total episodes, watched episodes, last watched episode date, and watched percentage. """
        return queryset.annotate(
            total_episodes=Count('episodes'),
            watched_episodes=Count('episodes', filter=Q(episodes__user_episodes__user=user)),
            last_watched_episode_date=Max('episodes__user_episodes__watch_date'),
            watched_percentage=ExpressionWrapper(
                F('watched_episodes') * 100.0 / F('total_episodes'), output_field=IntegerField()
            )
        )

    def serialize_shows(self, queryset):
        """ Serialize the annotated queryset data into a dictionary with relevant fields. """
        return [
            {
                'show': ProfileShowSerializer(show).data,
                'watched_percentage': show.watched_percentage if show.total_episodes > 0 else 0,
                # 'last_watched_episode_date': show.last_watched_episode_date,
                # 'total_episodes': show.total_episodes,
                # 'watched_episodes': show.watched_episodes,
            }
            for show in queryset
        ]
#################################################################
    # Followers section
    @action(detail=False, methods=['get'], url_path='followers')
    def followers(self, request):
        user = request.user
        queryset = Follow.objects.filter(follow=user).order_by('-follow_date')
        paginator = self.pagination_class()
        users_page = paginator.paginate_queryset(queryset, request)
        serialize_followers = FollowerSerializer(users_page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serialize_followers.data)

    @action(detail=True, methods=['get'], url_path='followers')
    def user_follower(self, request, pk):
        user_model = get_user_model()
        user = get_object_or_404(user_model, username=pk)
        if user.private and (not Follow.objects.filter(user=request.user, follow=user, is_accepted=True).exists()):
            return Response({"message": "You should follow this user first"}, status=status.HTTP_200_OK)
        
        queryset = Follow.objects.filter(follow=user).order_by('-follow_date')
        paginator = self.pagination_class()
        users_page = paginator.paginate_queryset(queryset, request)
        serialize_followers = FollowerSerializer(users_page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serialize_followers.data)
######################################################
    #Following section
    @action(detail=False, methods=['get'], url_path='followings')
    def followings(self, request):
        user = request.user
        queryset = Follow.objects.filter(user=user).order_by('-follow_date')
        paginator = self.pagination_class()
        users_page = paginator.paginate_queryset(queryset, request)
        serialize_followers = FollowingSerializer(users_page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serialize_followers.data)

    @action(detail=True, methods=['get'], url_path='followings')
    def user_followings(self, request, pk):
        user_model = get_user_model()
        user = get_object_or_404(user_model, username=pk)
        if user.private and (not Follow.objects.filter(user=request.user, follow=user, is_accepted=True).exists()):
            return Response({"message": "You should follow this user first"}, status=status.HTTP_200_OK)
        
        queryset = Follow.objects.filter(user=user).order_by('-follow_date')
        paginator = self.pagination_class()
        users_page = paginator.paginate_queryset(queryset, request)
        serialize_followers = FollowingSerializer(users_page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serialize_followers.data)
##############################################
    # Follow
    @action(detail=True, methods=['post'])
    def follow(self, request, pk):
        user = request.user
        user_model = get_user_model()
        followed_user = get_object_or_404(user_model, username=pk)
        check_exist = Follow.objects.filter(user=user, follow=followed_user)
        if not check_exist:
            if followed_user.private:
                Follow.objects.create(user=user, follow=followed_user, is_accepted=False)
                return Response({"message": "requested"}, status.HTTP_201_CREATED)
            else:
                Follow.objects.create(user=user, follow=followed_user)
                return Response({"message": "followed"}, status.HTTP_201_CREATED)

        else:
            return Response({"message": "user already followed"}, status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='accept-follow-request')
    def accept_follow(self, request, pk):
        user = request.user
        user_model = get_user_model()
        following_user = get_object_or_404(user_model, username=pk)

        follow_request = get_object_or_404(Follow, user=following_user, follow=user, is_accepted=False)
        follow_request.is_accepted = True
        follow_request.save()
        return Response({"message": "follow request accepted"}, status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['delete'])
    def unfollow(self, request, pk):
        user = request.user
        user_model = get_user_model()
        followed_user = get_object_or_404(user_model, username=pk)
        instance = get_object_or_404(Follow, user=user, follow=followed_user)
        instance.delete()
        return Response({"detail": "deleted"}, status.HTTP_204_NO_CONTENT)
################################################
# Favorite section
    @action(detail=False, methods=['get'], url_path='movie-favorites')
    def movie_favorites(self, request):
        queryset = Movie.objects.filter(user_movies__user=request.user, user_movies__is_favorite=True).order_by('-user_movies__watched_date')
        paginator = self.pagination_class()
        users_page = paginator.paginate_queryset(queryset, request)
        serialize_followers = ProfileMovieSerializer(users_page, many=True)
        
        return paginator.get_paginated_response(serialize_followers.data)

    @action(detail=True, methods=['get'], url_path='movie-favorites')
    def user_movie_favorites(self, request, pk):
        user = get_object_or_404(get_user_model(), username=pk)
        if user.private and (not Follow.objects.filter(user=request.user, follow=user, is_accepted=True).exists()):
            return Response({"message": "You should follow this user first"}, status=status.HTTP_200_OK)
        
        queryset = Movie.objects.filter(user_movies__user=user, user_movies__is_favorite=True).order_by('-users_movies__watched_date')
        paginator = self.pagination_class()
        users_page = paginator.paginate_queryset(queryset, request)
        serialize_followers = ProfileMovieSerializer(users_page, many=True)
        
        return paginator.get_paginated_response(serialize_followers.data)
    
    # Show
    @action(detail=False, methods=['get'], url_path='show-favorites')
    def show_favorites(self, request):
        queryset = Show.objects.filter(user_shows__user=request.user, user_shows__is_favorite=True)\
            .annotate(last_watched_episode_date=Max('episodes__user_episodes__watch_date')) \
            .order_by('-last_watched_episode_date')
        paginator = self.pagination_class()
        users_page = paginator.paginate_queryset(queryset, request)
        serialize_followers = ProfileShowSerializer(users_page, many=True)
        
        return paginator.get_paginated_response(serialize_followers.data)

    @action(detail=True, methods=['get'], url_path='show-favorites')
    def show_movie_favorites(self, request, pk):
        user = get_object_or_404(get_user_model(), username=pk)
        if user.private and (not Follow.objects.filter(user=request.user, follow=user, is_accepted=True).exists()):
            return Response({"message": "You should follow this user first"}, status=status.HTTP_200_OK)
        
        queryset = Show.objects.filter(user_shows__user=user, user_shows__is_favorite=True)\
            .annotate(last_watched_episode_date=Max('episodes__user_episodes__watch_date')) \
            .order_by('-last_watched_episode_date')
        paginator = self.pagination_class()
        users_page = paginator.paginate_queryset(queryset, request)
        serialize_followers = ProfileShowSerializer(users_page, many=True)
        
        return paginator.get_paginated_response(serialize_followers.data)

####################################################
# Actor section
class ActorView(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = CustomPagination

    def retrieve(self, request, *args, **kwargs):
        actor = self.get_object()

        # Filter shows and movies based on query params
        filter_type = self.request.query_params.get('type', None)
        shows = []
        movies = []
        for cast_item in actor.cast.all():
            content_object = cast_item.content_object
            if filter_type == 'shows' and isinstance(content_object, Show):
                shows.append(content_object)
            elif filter_type == 'movies' and isinstance(content_object, Movie):
                movies.append(content_object)
            elif filter_type is None:
                if isinstance(content_object, Show):
                    shows.append(content_object)
                elif isinstance(content_object, Movie):
                    movies.append(content_object)

        # Apply pagination separately for shows and movies
        if filter_type == 'shows':
            page = self.paginate_queryset(shows)
            if page is not None:
                serializer = ActorShowSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
        elif filter_type == 'movies':
            page = self.paginate_queryset(movies)
            if page is not None:
                serializer = ActorMovieSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
        # If no filter_type is provided, return both shows and movies paginated together
        else:
            combined = shows + movies
            page = self.paginate_queryset(combined)
            if page is not None:
                serialized_shows = ActorShowSerializer([obj for obj in page if isinstance(obj, Show)], many=True)
                serialized_movies = ActorMovieSerializer([obj for obj in page if isinstance(obj, Movie)], many=True)
                return self.get_paginated_response({
                    'shows': serialized_shows.data,
                    'movies': serialized_movies.data,
                })

        # If no pagination is applied (e.g., pagination is turned off)
        data = {
            'actor': ActorSerializer(actor).data,
            'shows': ActorShowSerializer(shows, many=True).data,
            'movies': ActorMovieSerializer(movies, many=True).data
        }
        return Response(data)

    # def retrieve(self, request, pk):
    #     movie = get_object_or_404(Movie, id=pk)
    #     user_movie = get_object_or_404(UserMovie, user=request.user, movie=movie)
    #     if user_movie.watched:

    # def retrieve(self, request, *args, **kwargs):
    #     movie = self.get_object()
    #     user = request.user
    #     serializer = self.get_serializer(movie)
    #     data = serializer.data
        
    #     # Add user-specific statistics if the movie is watched by the user
    #     try:
    #         user_movie = UserMovie.objects.get(user=user, movie=movie, watched=True)
    #         if user_movie.user_rate is not None:
    #             data['users_rate_counts'] = self.get_users_rate_counts(movie)
    #         if user_movie.favorite_cast is not None:
    #             data['favorite_cast_stats'] = self.get_favorite_cast_stats(movie)
    #         if user_movie.emoji is not None:
    #             data['emoji_stats'] = self.get_emoji_stats(movie)
    #     except UserMovie.DoesNotExist:
    #         pass
        
    #     return Response(data)

    # def get_users_rate_counts(self, movie):
    #     rate_counts = UserMovie.objects.filter(movie=movie, user_rate__isnull=False).values('user_rate').annotate(count=Count('user_rate')).order_by('user_rate')
    #     return {rate_count['user_rate']: rate_count['count'] for rate_count in rate_counts}

    # def get_favorite_cast_stats(self, movie):
    #     favorite_cast_counts = UserMovie.objects.filter(movie=movie, favorite_cast__isnull=False).values('favorite_cast').annotate(count=Count('favorite_cast'))
    #     total_users = UserMovie.objects.filter(movie=movie).count()
    #     return {favorite_cast['favorite_cast']: (favorite_cast['count'] / total_users) * 100 for favorite_cast in favorite_cast_counts}

    # def get_emoji_stats(self, movie):
    #     emoji_counts = UserMovie.objects.filter(movie=movie, emoji__isnull=False).values('emoji').annotate(count=Count('emoji'))
    #     total_users = UserMovie.objects.filter(movie=movie).count()
    #     return {emoji['emoji']: (emoji['count'] / total_users) * 100 for emoji in emoji_counts}