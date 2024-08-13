from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import (MovieWatchListView, SingleMovieView, CommentViewSet, ShowWatchListView,
                    SingleShowView, EpisodeView)

router = routers.DefaultRouter()
router.register('movies', MovieWatchListView, basename='user-movies')
router.register('movie', SingleMovieView, basename='movie')
router.register('shows', ShowWatchListView, basename='user-shows')
router.register('series', SingleShowView, basename='series')

movies_router = routers.NestedDefaultRouter(router, 'movie', lookup='movie')
movies_router.register('comment', CommentViewSet, basename='movie-comment')

series_router = routers.NestedDefaultRouter(router, 'series', lookup='series')
series_router.register('episodes', EpisodeView, basename='episodes')
series_router.register('comment', CommentViewSet, basename='series-comment')

episodes_router = routers.NestedDefaultRouter(series_router, 'episodes', lookup='episodes')
episodes_router.register('comment', CommentViewSet, basename='episode-comment')

urlpatterns = router.urls +\
              movies_router.urls +\
              series_router.urls +\
              episodes_router.urls
