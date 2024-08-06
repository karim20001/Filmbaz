from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import CreateUserApiView, LoginUserApiView


urlpatterns = [
    path('user/sign-up/', CreateUserApiView.as_view(), name='sign-up'),
    path('user/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
