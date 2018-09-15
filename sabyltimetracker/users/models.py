from django.contrib.auth.models import AbstractUser
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class User(AbstractUser):

    # First Name and Last Name do not cover name patterns
    # around the globe.
    WORKER = 1
    OVERSEER = 2
    USER_TYPE_CHOICES = [(WORKER, _("Worker")), (OVERSEER, _("Overseer"))]

    user_type = models.PositiveSmallIntegerField(null=True, choices=USER_TYPE_CHOICES,
                                                 default=None)
    ci = models.CharField(null=False, blank=False, max_length=10)
    phone = models.CharField(blank=True, max_length=20)
    address = models.CharField(blank=True, max_length=255)

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse('users:detail', kwargs={'username': self.username})

    def full_name(self):
        return '%s, %s' % (self.last_name, self.first_name)


class Worker(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    dummy = models.CharField(blank=True, max_length=255)

    def __str__(self):
        return self.user.username


class Overseer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    dummy = models.CharField(blank=True, max_length=255)

    def __str__(self):
        return self.user.username
