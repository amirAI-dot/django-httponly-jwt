"""What the example records: every change to a session, from the library's signals."""

from django.conf import settings
from django.db import models


class SessionEvent(models.Model):
    """One change to one person's session - the audit trail a project keeps."""

    person = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+'
    )
    #: started, renewed, refreshed or ended.
    what = models.CharField(max_length=16)
    #: Why it ended, for an ended session.
    reason = models.CharField(max_length=32, blank=True)
    path = models.CharField(max_length=200, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('at', 'pk')

    def __str__(self) -> str:
        return f'{self.what} {self.reason}'.strip()
