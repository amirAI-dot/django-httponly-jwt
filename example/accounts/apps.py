"""The example's own app: signing in by a code, and what it records."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self) -> None:
        # Connects the receivers that keep the record of sessions.
        from accounts import receivers  # noqa: F401
