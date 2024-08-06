from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


# class CustomUserAdmin(UserAdmin):
#     model = CustomUser
#     list_display = ('username', 'email', 'is_staff', 'is_active',)
#     list_filter = ('is_staff', 'is_active',)
#     fieldsets = (
#         (None, {'fields': ('username', 'email', 'password')}),
#         ('Personal Info', {'fields': ('birth_year', 'gender', 'profile_photo', 'cover_photo')}),
#         ('Permissions', {'fields': ('is_staff', 'is_pro', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
#     )
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('username', 'email', 'password1', 'password2', 'is_staff', 'is_active', 'is_pro')}
#         ),
#     )
#     search_fields = ('username', 'email',)
#     ordering = ('username',)

# admin.register(CustomUser, CustomUserAdmin)

from django.contrib import admin
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active', 'is_pro', 'gender', 'birth_year')
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_active')