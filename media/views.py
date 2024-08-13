from django.shortcuts import render, redirect
from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from urllib.parse import urlparse
from collections import defaultdict
from django.db.models import Count
import datetime
from .models import UserMovie, Movie, Cast, Comment, UserEpisode, Episode, Show, UserShow
from .serializers import (MovieWatchListSerializer,
                          SingleMovieSerializer,
                          UserMovieSerialzier,
                          CommentSerializer,
                          ShowWatchListSerialzier,
                          ShowSerializer,
                          UserShowSerializer,
                          EpisodeSerializer,
                          SingleEpisodeSerializer,
                          UserEpisodeSerializer,
                          )
from .permissions import AuthenticateOwnerComment, WatchedEpisodeByUser

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
        serializer = MovieWatchListSerializer(movies, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        user_movies = UserMovie.objects.filter(user=request.user, watched=False)
        movie_ids = user_movies.values_list('movie_id', flat=True)
        movies = Movie.objects.filter(id__in=movie_ids, release_date__gte=datetime.date.today())
        serializer = MovieWatchListSerializer(movies, many=True, context={'request': request})
        return Response(serializer.data)


class SingleMovieView(viewsets.ReadOnlyModelViewSet,
                      viewsets.GenericViewSet):
    
    queryset = Movie.objects.all()
    permission_classes = [IsAuthenticated]

   

    def get_serializer_context(self):
        return {'request': self.request}

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserMovieSerialzier
        return SingleMovieSerializer
    
    def get_redirect_url(self, request):
        referer = request.META.get('HTTP_REFERER')
        return referer if referer else '/'
    

    
    def create(self, request, *args, **kwargs):
        movie = self.get_object()
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user, movie=movie)
        movie.added_count += 1
        movie.save()
        return redirect(self.get_redirect_url(request))

    def partial_update(self, request, *args, **kwargs):
        movie = self.get_object()
        if movie.release_date > datetime.date.today():
            return Response({"message": "movie not released"}, status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        user_movie = get_object_or_404(UserMovie, user=user, movie=movie)

        data = request.data
        watched_status = data.pop('watched', None)

        if watched_status is not None:
            if not watched_status and user_movie.watched:
                # Update likes for favorite_cast and users_rate for movie
                self.update_likes_and_rate(movie, user_movie, decrement=True)
                
                # Reset all other fields to None if watched status is changed to False
                user_movie.is_favorite = None
                user_movie.user_rate = None
                user_movie.emoji = None
                user_movie.favorite_cast = None

                user_movie.watched = watched_status
                user_movie.save()
                return Response({'message': 'Watched status updated and user movie data reset!'}, status=status.HTTP_200_OK)
            else:
                user_movie.watched = watched_status
                user_movie.save()
                return Response({'message': 'Watched status updated!'}, status=status.HTTP_200_OK)

        if not user_movie.watched:
            return Response({"message": "You must watch the movie before updating its details."}, status=status.HTTP_400_BAD_REQUEST)

        old_favorite_cast = user_movie.favorite_cast
        new_favorite_cast_id = data.get('favorite_cast')
        content_type = ContentType.objects.get(model='episode').id

        if Cast.objects.filter(id=new_favorite_cast_id, object_id=old_favorite_cast.id, content_type=content_type):

            if new_favorite_cast_id and (not old_favorite_cast or new_favorite_cast_id != old_favorite_cast.id):
                new_favorite_cast = get_object_or_404(Cast, id=new_favorite_cast_id)
                self.update_likes_for_favorite_cast(old_favorite_cast, new_favorite_cast)

                user_movie.favorite_cast = new_favorite_cast
        else:
            return Response({"detail": "cast is not related"}, status.HTTP_400_BAD_REQUEST)
        
        old_user_rate = user_movie.user_rate
        new_user_rate = data.get('user_rate')

        if new_user_rate is not None and new_user_rate != old_user_rate:
            user_movie.user_rate = new_user_rate
            self.update_users_rate(movie, old_user_rate, new_user_rate)

        serializer = self.get_serializer(user_movie, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return redirect(self.get_redirect_url(request))

    def destroy(self, request, *args, **kwargs):
        movie = self.get_object()
        user = request.user

        try:
            user_movie = UserMovie.objects.get(user=user, movie=movie)
            if user_movie.watched:
                self.update_likes_and_rate(movie, user_movie, decrement=True)
            user_movie.delete()
            movie.added_count -= 1
            movie.save()
            return redirect(self.get_redirect_url(request))
        except UserMovie.DoesNotExist:
            return Response({'message': 'Movie not added yet!'}, status=status.HTTP_400_BAD_REQUEST)

    def update_likes_for_favorite_cast(self, old_cast, new_cast):
        if old_cast:
            old_cast.likes -= 1
            old_cast.save()
        new_cast.likes += 1
        new_cast.save()

    def update_users_rate(self, movie, old_rate, new_rate):
        if old_rate is not None:
            movie.users_rate = ((movie.users_rate * movie.usermovie_set.count()) - old_rate + new_rate) / movie.usermovie_set.count()
        else:
            movie.users_rate = ((movie.users_rate * (movie.usermovie_set.count() - 1)) + new_rate) / movie.usermovie_set.count()
        movie.save()


class CommentViewSet(mixins.CreateModelMixin,
                     mixins.DestroyModelMixin,
                     mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):

    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, AuthenticateOwnerComment]

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
        print(data['object_id'])
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
        time_threshold = timezone.now() - datetime.timedelta(minutes=8) # assuming 4 weeks as the threshold

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


class SingleShowView(mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    
    permission_classes = [IsAuthenticated]

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

    def create(self, request, *args, **kwargs):
        # Extract the show ID from the URL's pk
        show_pk = kwargs.get('pk')
        
        # Ensure the user is set to the current authenticated user
        data = request.data.copy()
        data['user'] = request.user.pk
        data['show'] = show_pk  # Set the show from the URL's pk

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


    def perform_create(self, serializer):
        # Automatically set the user to the current authenticated user
        serializer.save(user=self.request.user)
    
    def destroy(self, request, pk):
        show = get_object_or_404(Show, pk=pk)
        user_show = get_object_or_404(UserShow, user=request.user, show=show)
        user_show.delete()
        return Response({"message": "deleted"},  status.HTTP_204_NO_CONTENT)


class EpisodeView(
                  mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    
    serializer_class = Episode
    queryset = Episode.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.action in ['list', 'retrieve']:
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
    
    def create(self, request, *args, **kwargs):
        episode_id = self.kwargs['pk']
        episode = get_object_or_404(Episode, pk=episode_id)
        user = request.user

        if not UserShow.objects.filter(user=user, show=episode.show).exists():
            UserShow.create(user=user, show=episode.show)
        
        UserEpisode.create(user=user, episode=episode)

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

        else:
            return Response({"detail": "cast is not related"}, status.HTTP_400_BAD_REQUEST)
        
        old_user_rate = instance.user_rate
        new_user_rate = data.get('user_rate')

        if new_user_rate is not None and new_user_rate != old_user_rate:
            instance.user_rate = new_user_rate
            self.update_users_rate(instance, old_user_rate, new_user_rate)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status.HTTP_200_OK)

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

    def update_users_rate(self, episode, old_rate, new_rate):
        if old_rate is not None:
            episode.users_rate = ((episode.users_rate * episode.usermovie_set.count()) - old_rate + new_rate) / episode.usermovie_set.count()
        else:
            episode.users_rate = ((episode.users_rate * (episode.usermovie_set.count() - 1)) + new_rate) / episode.usermovie_set.count()
        episode.save()


















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