import requests
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Article


@receiver(post_save, sender=Article)
def handle_article_approval(sender, instance, created, **kwargs):
    """Handles email alerts and webhook delivery when an article is approved."""
    if created or not instance.approved:
        return

    # Prevent infinite save loops
    if hasattr(instance, '_already_processed_approval'):
        return
    instance._already_processed_approval = True

    recipient_emails = list(User.objects.exclude(email='').values_list('email', flat=True)[:5])

    if recipient_emails:
        send_mail(
            subject=f"[SIMULATION] New Article Published: {instance.title}",
            message=f"Hello Reader!\n\nA new piece has been published by "
                    f"'{instance.publisher.name if instance.publisher else 'an Independent Author'}'.\n\n"
                    f"Content Snippet:\n{instance.content[:150]}...\n\n",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_emails,
            fail_silently=True,
        )

    api_path = reverse('api_approved')
    webhook_url = f"http://127.0.0.1:8000{api_path}"

    payload = {
        "id": instance.id,
        "title": instance.title,
        "publisher": instance.publisher.name if instance.publisher else "Independent",
        "author": instance.author.username if instance.author else "Corporate Staff",
    }

    try:
        headers = {'Content-Type': 'application/json', 'User-Agent': 'Django-Signal'}
        requests.post(webhook_url, json=payload, headers=headers, timeout=2)
    except requests.exceptions.RequestException as e:
        print(f"\n[SIGNAL WEBHOOK NOTICE] Webhook request skipped or timed out: {e}")
