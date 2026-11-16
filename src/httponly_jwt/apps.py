"""The app: named in ``INSTALLED_APPS`` as ``'httponly_jwt'``."""

from importlib.util import find_spec

from django.apps import AppConfig


class HttpOnlyJWTConfig(AppConfig):
    name = 'httponly_jwt'
    verbose_name = 'HttpOnly JWT'

    def ready(self) -> None:
        # The checks register themselves when their module is imported.
        from httponly_jwt import checks  # noqa: F401

        if find_spec('drf_spectacular') is not None:
            # The schema extensions register themselves when imported, too.
            from httponly_jwt import schema  # noqa: F401
