from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    FEMALE = 'زن'
    MALE = 'مرد'
    GENDER_CHOICES = [
        (FEMALE, 'زن'),
        (MALE, 'مرد')
    ]

    birth_year = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    profile_photo = models.ImageField(upload_to='users/photos/', null=True, blank=True)
    cover_photo = models.ImageField(upload_to='users/covers/', null=True, blank=True)
    is_pro = models.BooleanField(default=False)

    def __str__(self):
        return self.username
