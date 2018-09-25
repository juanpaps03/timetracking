from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import User


class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class MyUserCreationForm(UserCreationForm):

    error_message = UserCreationForm.error_messages.update({
        'duplicate_username': 'This username has already been taken.'
    })

    class Meta(UserCreationForm.Meta):
        model = User

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])


@admin.register(User)
class MyUserAdmin(UserAdmin):
    form = MyUserChangeForm
    add_form = MyUserCreationForm
    fieldsets = (
            ('User Profile', {'fields': ('user_type',)}),
    ) + UserAdmin.fieldsets
    list_display = ('username', 'full_name', 'is_superuser')
    list_filter = ('is_active', 'user_type', 'is_staff', 'groups__name')

    search_fields = ['name']

    def get_readonly_fields(self, request, obj=None):
        rof = super(UserAdmin, self).get_readonly_fields(request, obj)
        if obj and not request.user.is_superuser:
            rof += ('is_superuser', 'groups', 'user_permissions', 'username', 'is_active', 'password')
        return rof

    def full_name(self, obj):
        if obj.last_name:
            return "%s, %s" % (obj.last_name, obj.first_name)
        return ''
    full_name.short_description = 'Full Name'

