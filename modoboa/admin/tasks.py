"""Async tasks done by RQ."""

from rq import Queue
from redis import Redis

from django.core.management import call_command
from django.db.models import signals
from django.dispatch import receiver

from .import models


@receiver(signals.post_save, sender=models.Domain)
def create_dkim_key(sender, instance, **kwargs):
    print("here!")
    if not instance.enable_dkim:
        return
    q = Queue("default", connection=Redis())
    print(instance.name)
    job = q.enqueue(call_command,
                    "modo",
                    "manage_dkim_keys",
                    "--domain=instance.name")
    print(job.id)
