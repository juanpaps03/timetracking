from django.contrib.auth.models import AbstractUser
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class User(AbstractUser):
    ci = models.CharField(null=False, blank=False, max_length=10)
    phone = models.CharField(blank=True, max_length=20)
    address = models.CharField(blank=True, max_length=255)

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse('users:detail', kwargs={'username': self.username})

    def full_name(self):
        return '%s, %s' % (self.last_name, self.first_name)
