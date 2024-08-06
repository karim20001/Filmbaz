from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import MovieWatchListView, SingleMovieView, CommentViewSet

router = routers.DefaultRouter()
router.register('movies', MovieWatchListView, basename='user-movies')
router.register('movie', SingleMovieView, basename='movie')

movies_router = routers.NestedDefaultRouter(router, 'movie', lookup='movie')
movies_router.register('comment', CommentViewSet, basename='movie-comment')

urlpatterns = router.urls + movies_router.urls
