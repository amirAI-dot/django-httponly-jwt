"""The app: named in ``INSTALLED_APPS`` as ``'httponly_jwt'``."""

from django.apps import AppConfig


class HttpOnlyJWTConfig(AppConfig):
    name = 'httponly_jwt'
    verbose_name = 'HttpOnly JWT'

    def ready(self) -> None:
        # The checks register themselves when their module is imported.
        from httponly_jwt import checks  # noqa: F401
