from django.core.exceptions import PermissionDenied


def user_permissions(user_types_allowed):
    """
    Decorator for permissions checking
    :param user_types_allowed: list of user types allowed
    """
    def wrapper(function):
        def wrap(request, *args, **kwargs):
            if request.user:
                user = request.user
                self_type = user.user_type
                if self_type in user_types_allowed:
                    return function(request, *args, **kwargs)
            raise PermissionDenied
            # TODO: change this raise to render or something and use 403_csrf.html of cookiecutter
        wrap.__doc__ = function.__doc__
        wrap.__name__ = function.__name__
        return wrap
    return wrapper
