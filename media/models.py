from django.db import models
from uuid import uuid4
from django.conf import settings
import os
from django.core.files.storage import default_storage
from django.core.validators import MaxValueValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q


class Genre(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


def show_cover_upload_to(instance, filename):
        """
        Dynamically generates the path for the show cover photo.
        """
        return f'shows/{instance.name}/{filename}'


class Show(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    imdb_url = models.URLField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    season_count = models.IntegerField(default=1, null=True, blank=True)
    imdb_rate = models.DecimalField(max_digits=2, decimal_places=1)
    users_rate = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    release_year = models.IntegerField(null=True, blank=True)
    end_year = models.IntegerField(null=True, blank=True, default=None)
    duration = models.IntegerField(null=True, blank=True)  # Duration in minutes
    release_time = models.TimeField(null=True, blank=True)
    release_day = models.CharField(max_length=50)  # Example: "Monday"
    is_released = models.BooleanField()
    network = models.CharField(max_length=255, null=True, blank=True)
    users_added_count = models.PositiveIntegerField(default=0)
    users_rate_count = models.PositiveIntegerField(default=0)
    genres = models.ManyToManyField(Genre)
    cover_photo = models.ImageField(upload_to=show_cover_upload_to, null=True, blank=True)

    def __str__(self):
        return f"{self.name} | Season {self.season_count}"
    
    def get_similar_shows(self):
        # Retrieve shows that share at least one genre with the current show, excluding the show itself
        similar_shows = Show.objects.filter(
            genres__in=self.genres.all()
        ).exclude(id=self.id) \
        .annotate(shared_genres=Count('genres', filter=Q(genres__in=self.genres.all()))) \
        .order_by('-shared_genres', '-users_added_count')[:10]

        return similar_shows

def episode_cover_upload_to(instance, filename):
        """
        Dynamically generates the path for the episode cover photo.
        """
        return f'shows/{instance.show.name}/season_{instance.season}/episodes/photos/{filename}'

class Episode(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    imdb_url = models.URLField(unique=True, null=True, blank=True)
    show = models.ForeignKey(Show, related_name='episodes', on_delete=models.CASCADE)
    season = models.IntegerField()
    duration = models.IntegerField(null=True, blank=True)
    imdb_rate = models.DecimalField(max_digits=2, decimal_places=1)
    users_rate = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    episode_number = models.IntegerField()
    release_date = models.DateField()
    is_released = models.BooleanField()
    name = models.CharField(max_length=255)
    description = models.TextField()
    cover_photo = models.ImageField(upload_to=episode_cover_upload_to, null=True, blank=True)

    def __str__(self):
        return f"{self.show.name} S{self.season}E{self.episode_number} - {self.name}"



class Movie(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    name = models.CharField(max_length=255)
    duration = models.IntegerField()  # Duration in minutes
    imdb_rate = models.DecimalField(max_digits=2, decimal_places=1)
    users_rate = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    description = models.TextField()
    release_date = models.DateField()
    is_released = models.BooleanField()
    genres = models.ManyToManyField(Genre)
    users_rate_count = models.PositiveIntegerField(default=0)
    users_added_count = models.PositiveIntegerField(default=0)
    cover_photo = models.ImageField(upload_to='movies/photos/', null=True, blank=True)

    def __str__(self):
        return self.name

    def get_similar_movies(self):
        similar_movies = Movie.objects.filter(
                            genres__in=self.genres.all()
                        ).exclude(id=self.id).distinct()\
                        .annotate(shared_genres=Count('genres', filter=Q(genres__in=self.genres.all())))\
                        .order_by('-shared_genres', '-users_added_count')[:10]                       
        return similar_movies

class Actor(models.Model):
    name = models.CharField(max_length=255)
    bio = models.TextField(null=True, blank=True)
    birth_date = models.DateField()
    birth_city = models.CharField(max_length=255)
    profile_photo = models.ImageField(upload_to='actors/photos/', null=True, blank=True)

    def __str__(self):
        return self.name


class Cast(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE) # should be Movie, Show, Episode
    object_id = models.UUIDField() # id of related object
    content_object = GenericForeignKey('content_type', 'object_id')
    actor = models.ForeignKey(Actor, related_name='cast', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    likes = models.PositiveIntegerField(default=0)
    photo = models.ImageField(upload_to='cast/photos/', null=True, blank=True)

    def __str__(self):
        return f"{self.actor.name} in {self.content_object.name}"


class UserShow(models.Model):
    NOT_STARTED = None
    WATCHING = 'در حال تماشا'
    STOPPED = 'متوقف شده'
    WATCH_LATER = 'برای بعد'
    STATUS_CHOICES = [
        (NOT_STARTED, None),
        (WATCHING, 'در حال تماشا'),
        (STOPPED, 'متوقف شده'),
        (WATCH_LATER, 'برای بعد'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='user_shows', on_delete=models.CASCADE)
    show = models.ForeignKey(Show, related_name='user_shows', on_delete=models.CASCADE)
    added_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=None, null=True)
    is_favorite = models.BooleanField(default=False)
    user_rate = models.PositiveIntegerField(null=True, blank=True, validators=[MaxValueValidator(5)])

    def __str__(self):
        return f"{self.user.username} - {self.show.name}"


class UserEpisode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='user_episodes', on_delete=models.CASCADE)
    episode = models.ForeignKey(Episode, related_name='user_episodes', on_delete=models.CASCADE)
    user_rate = models.PositiveIntegerField(null=True, blank=True, validators=[MaxValueValidator(5)])
    watch_date = models.DateTimeField(auto_now_add=True)
    emoji = models.CharField(max_length=50, null=True, blank=True)  # Example: "😀", "😢"
    favorite_cast = models.ForeignKey(Cast, related_name='favorite_episode_cast', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.episode.name} | {self.episode.show.name}"


class UserMovie(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='user_movies', on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, related_name='user_movies', on_delete=models.CASCADE)
    watched = models.BooleanField(default=False)
    watched_date = models.DateTimeField(default=None, blank=True, null=True)
    user_rate = models.PositiveIntegerField(null=True, blank=True, validators=[MaxValueValidator(5)])
    emoji = models.CharField(max_length=50, null=True, blank=True)  # Example: "😀", "😢"
    is_favorite = models.BooleanField(default=False)
    added_date = models.DateTimeField(auto_now_add=True)
    favorite_cast = models.ForeignKey(Cast, related_name='favorite_movie_cast', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.movie.name}"


class Follow(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='following', on_delete=models.CASCADE)
    follow = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='followers', on_delete=models.CASCADE)
    is_accepted = models.BooleanField(default=True)
    follow_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} follows {self.follow.username}"


class Comment(models.Model):
    # id = models.UUIDField(default=uuid4, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='comments', on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE) # should be Movie, Show, Episode
    object_id = models.UUIDField() # id of related object
    content_object = GenericForeignKey('content_type', 'object_id')
    detail = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    is_spoiler = models.BooleanField(default=False)
    is_proved = models.BooleanField(default=False)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_comments', blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.content_type} - {self.object_id}"
    
    @property
    def sub_comment_count(self):
        return self.replies.count()
    
    @property
    def like_count(self):
        return self.likes.count()


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"