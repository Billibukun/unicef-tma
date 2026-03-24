from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    """Thin wrapper so we can customise later if needed."""
    pass
