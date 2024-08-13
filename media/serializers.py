from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Avg
from django.forms.models import model_to_dict
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Movie, UserMovie, Cast, Actor, Genre, Comment, UserEpisode, UserShow, Episode, Show


class MovieWatchListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Movie
        fields = ['url', 'name', 'cover_photo']


class SimpleActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = ['name']


class UserMovieSerialzier(serializers.ModelSerializer):
    class Meta:
        model = UserMovie
        fields = ['watched', 'user_rate', 'emoji', 'is_favorite', 'favorite_cast']

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['name']

class SimpleCastSerializer(serializers.ModelSerializer):
    actor = SimpleActorSerializer()

    class Meta:
        model = Cast
        fields = ['id', 'name', 'actor', 'photo']

class SimilarMovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ['id', 'name', 'cover_photo']

class SingleMovieSerializer(serializers.ModelSerializer):
    genres = GenreSerializer()
    # watch_link = serializers.SerializerMethodField()
    # add_link = serializers.SerializerMethodField()
    # add_favorite = serializers.SerializerMethodField()
    casts = serializers.SerializerMethodField()
    # remove_link = serializers.SerializerMethodField()
    user_movie = serializers.SerializerMethodField()
    users_rate_counts = serializers.SerializerMethodField()
    favorite_cast_stats = serializers.SerializerMethodField()
    emoji_stats = serializers.SerializerMethodField()
    similar_movies = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        depth = 1
        fields = ['name', 'duration', 'imdb_rate', 'users_rate', 'description',
                  'release_date', 'genres', 'casts', 'rate_count', 'cover_photo',
                  'added_count', 'users_rate_counts', 'favorite_cast_stats',
                  'user_movie', 'emoji_stats', 'similar_movies']
    
    # depth = 1
    
    def get_casts(self, obj):
        casts = Cast.objects.filter(content_type__model='movie', object_id=obj.id)  # Filter casts related to the movie
        return SimpleCastSerializer(casts, many=True).data
    
    def get_user_movie(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if user:
            try:
                user_movie = UserMovie.objects.get(user=user, movie=obj)
                return UserMovieSerialzier(user_movie).data
            except:
                return None
        return None
    
    def get_users_rate_counts(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                user_movie = UserMovie.objects.get(user=request.user, movie=obj)
                if user_movie.user_rate is not None:
                    rate_counts = UserMovie.objects.filter(movie=obj, user_rate__isnull=False).values('user_rate').annotate(count=Count('user_rate')).order_by('user_rate')
                    total_users = UserMovie.objects.filter(movie=obj, user_rate__isnull=False).count()
                    return {rate_count['user_rate']: int((rate_count['count'] / total_users) * 100) for rate_count in rate_counts}
            except UserMovie.DoesNotExist:
                pass
        return None

    def get_favorite_cast_stats(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                user_movie = UserMovie.objects.get(user=request.user, movie=obj)
                if user_movie.favorite_cast is not None:
                    favorite_cast_counts = UserMovie.objects.filter(movie=obj, favorite_cast__isnull=False).values('favorite_cast').annotate(count=Count('favorite_cast'))
                    total_users = UserMovie.objects.filter(movie=obj, favorite_cast__isnull=False).count()
                    return {favorite_cast['favorite_cast']: int((favorite_cast['count'] / total_users) * 100) for favorite_cast in favorite_cast_counts}

            except UserMovie.DoesNotExist:
                pass
        return None

    def get_emoji_stats(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                user_movie = UserMovie.objects.get(user=request.user, movie=obj)
                if user_movie.emoji is not None:
                    emoji_counts = UserMovie.objects.filter(movie=obj, emoji__isnull=False).values('emoji').annotate(count=Count('emoji'))
                    total_users = UserMovie.objects.filter(movie=obj, emoji__isnull=False).count()
                    return {emoji['emoji']: int((emoji['count'] / total_users) * 100) for emoji in emoji_counts}

            except UserMovie.DoesNotExist:
                pass
        return None
    
    def get_similar_movies(self, obj):
        similar_movies = obj.get_similar_movies()
        return SimilarMovieSerializer(similar_movies, many=True).data

class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'first_name', 'profile_photo']
        read_only_fields = ['id', 'first_name', 'profile_photo']

class ReplySerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    likes_count = serializers.IntegerField(source='like_count', read_only=True)
    user_liked = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Comment
        fields = ['user', 'detail', 'created_date', 'is_spoiler', 'likes_count', 'user_liked']
        read_only_fields = ['created_at', 'is_spoiler']
    
    def get_user_liked(self, obj):
        request = self.context.get('request')
        if request:
            return obj.likes.filter(id=request.user.id).exists()
        return False
    

class CommentSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(source='like_count', read_only=True)
    replies_count = serializers.IntegerField(source='sub_comment_count', read_only=True)
    user_liked = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'user', 'detail', 'created_date', 'is_spoiler', 'content_type', 'object_id',
                   'parent', 'replies', 'replies_count', 'likes_count', 'user_liked']
        read_only_fields = ['created_at', 'is_spoiler', 'replies', 'likes']
    
    def get_replies(self, obj):
        # Check the context to see if replies should be included
        include_replies = self.context.get('include_replies', False)
        if include_replies:
            reply_comments = obj.replies.all()
            return ReplySerializer(reply_comments, many=True, context=self.context).data
        return None
    
    def get_user_liked(self, obj):
        request = self.context.get('request')
        if request:
            return obj.likes.filter(id=request.user.id).exists()
        return False
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


class EpisodeRateSerializer(serializers.ModelSerializer):
    average_user_rate = serializers.DecimalField(max_digits=2, decimal_places=1, read_only=True)
    class Meta:
        model = Episode
        fields = ['episode_number', 'average_user_rate']

class SeasonSerializer(serializers.Serializer):
    season = serializers.IntegerField()
    episodes = EpisodeRateSerializer(many=True)


class SimilarShowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Show
        fields = ['id', 'name', 'cover_photo']


class ShowSerializer(serializers.ModelSerializer):
    genres = GenreSerializer()
    seasons_rate = serializers.SerializerMethodField()
    similar_shows = serializers.SerializerMethodField()

    class Meta:
        model = Show
        fields = ['name', 'season_count', 'imdb_rate', 'users_rate', 'release_year',
                  'duration', 'release_time', 'release_day', 'users_added_count',
                  'users_rate_count', 'genres', 'cover_photo', 'seasons_rate',
                  'similar_shows']

    def get_seasons_rate(self, obj):
    # Get distinct seasons for the show
        seasons = obj.episodes.values_list('season', flat=True).distinct().order_by('season')

        # Prepare a list of seasons with their episodes
        season_data = []
        for season in seasons:
            episodes = obj.episodes.filter(season=season).annotate(average_user_rate=Avg('user_episodes__user_rate')).order_by('episode_number')
            season_data.append({
                'season': season,
                'episodes': EpisodeRateSerializer(episodes, many=True).data
            })
        
        return season_data
    
    def get_similar_shows(self, obj):
        similar_shows = obj.get_similar_shows()
        return SimilarShowSerializer(similar_shows, many=True).data
class SimpleShowNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Show
        fields = ['id', 'name']

class ShowWatchListSerialzier(serializers.ModelSerializer):
    show = SimpleShowNameSerializer()
    class Meta:
        model = Episode
        fields = ['id', 'name', 'season', 'episode_number', 'cover_photo', 'show']


class UserShowSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserShow
        fields = ['user', 'show', 'added_date', 'status',
                  'is_favorite', 'user_rate']

class EpisodeSerializer(serializers.ModelSerializer):
    user_watched = serializers.SerializerMethodField()

    class Meta:
        model = Episode
        fields = ['id', 'season', 'episode_number', 'name', 'cover_photo',
                  'user_watched']

    def get_user_watched(self, obj):
        user = self.context['request'].user
        return UserEpisode.objects.filter(user=user, episode=obj).exists()

class UserEpisodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEpisode
        fields = ['user_rate', 'emoji', 'favorite_cast']


class SingleEpisodeSerializer(serializers.ModelSerializer):
    casts = serializers.SerializerMethodField()
    users_rate = serializers.SerializerMethodField()
    favorite_cast_stats = serializers.SerializerMethodField()
    emoji_stats = serializers.SerializerMethodField()
    class Meta:
        model = Episode
        fields = ['id', 'season', 'episode_number', 'name', 'cover_photo',
                  'casts', 'users_rate', 'favorite_cast_stats', 'emoji_stats']

    def get_user_episode(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if user:
            try:
                user_episode = UserEpisode.objects.get(user=user, episode=obj)
                return UserEpisodeSerializer(user_episode).data
            except:
                return None
        return None

    def get_casts(self, obj):
        casts = Cast.objects.filter(content_type__model='episode', object_id=obj.id)  # Filter casts related to the movie
        return SimpleCastSerializer(casts, many=True).data
    
    def get_users_rate(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                user_movie = UserEpisode.objects.get(user=request.user, episode=obj)
                if user_movie.user_rate is not None:
                    rate_counts = UserEpisode.objects.filter(episode=obj, user_rate__isnull=False).values('user_rate').annotate(count=Count('user_rate')).order_by('user_rate')
                    total_users = UserEpisode.objects.filter(episode=obj, user_rate__isnull=False).count()
                    return {rate_count['user_rate']: int((rate_count['count'] / total_users) * 100) for rate_count in rate_counts}
            except UserEpisode.DoesNotExist:
                pass
        return None
    
    def get_favorite_cast_stats(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                user_movie = UserEpisode.objects.get(user=request.user, episode=obj)
                if user_movie.favorite_cast is not None:
                    favorite_cast_counts = UserEpisode.objects.filter(episode=obj, favorite_cast__isnull=False).values('favorite_cast').annotate(count=Count('favorite_cast'))
                    total_users = UserEpisode.objects.filter(episode=obj, favorite_cast__isnull=False).count()
                    return {favorite_cast['favorite_cast']: int((favorite_cast['count'] / total_users) * 100) for favorite_cast in favorite_cast_counts}

            except UserEpisode.DoesNotExist:
                pass
        return None
    
    def get_emoji_stats(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                user_movie = UserEpisode.objects.get(user=request.user, episode=obj)
                if user_movie.emoji is not None:
                    emoji_counts = UserEpisode.objects.filter(episode=obj, emoji__isnull=False).values('emoji').annotate(count=Count('emoji'))
                    total_users = UserEpisode.objects.filter(episode=obj, emoji__isnull=False).count()
                    return {emoji['emoji']: int((emoji['count'] / total_users) * 100) for emoji in emoji_counts}

            except UserEpisode.DoesNotExist:
                pass
        return None
    # def get_watch_link(self, obj):
    #     request = self.context.get('request')
    #     user = request.user if request else None
    #     if user and UserMovie.objects.filter(user=user, movie=obj, watched=True):
    #         return None
    #     return request.build_absolute_uri(f'/movie/{obj.id}/add_to_watchlist')
    
    # def get_add_link(self, obj):
    #     request = self.context.get('request')
    #     user = request.user if request else None
    #     if user and UserMovie.objects.filter(user=user, movie=obj).exists():
    #         return None
    #     return request.build_absolute_uri(f'/movie/{obj.id}/addMovie')
    
    # def get_remove_link(self, obj):
    #     request = self.context.get('request')
    #     user = request.user if request else None
    #     if user and UserMovie.objects.filter(user=user, movie=obj).exists():
    #         return request.build_absolute_uri(f'/movie/{obj.id}/removeMovie')
    #     return None
    
    # def get_add_favorite(self, obj):
    #     request = self.context.get('request')
    #     user = request.user if request else None
    #     if user and UserMovie.objects.filter(user=user, movie=obj, watched=True):
    #         return request.build_absolute_uri(f'/movie/{obj.id}/addFavorite')
    #     return None