# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

# Custom user model with roles
class User(AbstractUser):
    ROLE_CHOICES = (
        ('superuser', 'Superuser'),
        ('agent', 'Agent'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='agent')
    subcounty = models.CharField(max_length=100, blank=True, null=True)
    # Add custom fields
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)

    # Optional: Override groups and user_permissions if needed
    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',  # Unique reverse access name
        blank=True,
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions_set',  # Unique reverse access name
        blank=True,
    )
class ElectionPosition(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Candidate(models.Model):
    name = models.CharField(max_length=255)
    position = models.ForeignKey(ElectionPosition, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='candidates_photos/')

    def __str__(self):
        return f"{self.name} ({self.position.name})"

class PollingStation(models.Model):
    name = models.CharField(max_length=255)
    subcounty = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} - {self.subcounty}"

class Result(models.Model):
    polling_station = models.ForeignKey(PollingStation, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    votes = models.IntegerField()
    agent = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.polling_station} - {self.candidate} - {self.votes} votes"
AUTH_USER_MODEL = 'tally.User'
