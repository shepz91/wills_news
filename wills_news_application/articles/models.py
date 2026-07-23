import requests
from django.db import models
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.mail import send_mail


class Publisher(models.Model):
    """Represents a news organisaation or network."""
    name = models.CharField(max_length=100, unique=True)
    journalists = models.ManyToManyField(User, related_name='publisher_journalists', blank=True)
    editors = models.ManyToManyField(User, related_name='publisher_editors', blank=True)

    def __str__(self):
        """Returns the publisher's name."""
        return self.name


class Article(models.Model):
    """Represents a written news story."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='articles',
        blank=True, null=True
    )
    publisher = models.ForeignKey(
        Publisher, on_delete=models.CASCADE, related_name='articles',
        blank=True, null=True
    )

    def clean(self):
        """Validates that an article belongs to either an author or a publisher."""
        super().clean()
        if self.author and self.publisher:
            raise ValidationError(
                "An article cannot have both an individual author "
                "(journalist) and a publisher."
            )
        if not self.author and not self.publisher:
            raise ValidationError(
                "An article must be associated with either an "
                "individual author (journalist) or a publisher."
            )

    def save(self, *args, **kwargs):
        """Runs full validation checks before committing to the database."""
        if not self.pk or kwargs.get('force_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Returns the article title."""
        return self.title


class Newsletter(models.Model):
    """Represents a collection of articles sent to subscribers."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='newsletters'
    )
    articles = models.ManyToManyField(
        Article,
        related_name='newsletters',
        blank=True
    )

    def __str__(self):
        """Returns the newsletter title."""
        return self.title


class UserProfile(models.Model):
    """Stores extended user information including account roles."""
    ROLE_CHOICES = [
        ('reader', 'Reader'),
        ('journalist', 'Journalist'),
        ('editor', 'Editor'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='reader')

    subscribed_publishers = models.ManyToManyField(Publisher, related_name='subscribed_readers', blank=True)
    subscribed_journalists = models.ManyToManyField(User, related_name='subscribed_readers', blank=True)

    def clean(self):
        """Performs initial user data checks."""
        super().clean()

    def save(self, *args, **kwargs):
        """Saves profile updates and clears subscriptions if a user becomes staff."""
        is_role_changing = False
        if self.pk:
            try:
                orig = UserProfile.objects.get(pk=self.pk)
                if orig.role == 'reader' and self.role in ['journalist', 'editor']:
                    is_role_changing = True
            except UserProfile.DoesNotExist:
                pass

        super().save(*args, **kwargs)
        if (self.role in ['journalist', 'editor']) or is_role_changing:
            self.subscribed_publishers.clear()
            self.subscribed_journalists.clear()

    def __str__(self):
        """Returns the username combined with their assigned role."""
        return f"{self.user.username} - {self.get_role_display()}"


@receiver(post_save, sender=UserProfile)
def assign_user_to_group(sender, instance, created, **kwargs):
    """Synchronizes auth groups when a profile is saved."""
    if getattr(instance, '_saving_group', False):
        return

    instance._saving_group = True
    try:
        role_groups = ['Reader', 'Journalist', 'Editor']
        for group_name in role_groups:
            group = Group.objects.filter(name=group_name).first()
            if group:
                instance.user.groups.remove(group)

        group_name = instance.role.capitalize()
        group, _ = Group.objects.get_or_create(name=group_name)
        instance.user.groups.add(group)
    finally:
        instance._saving_group = False


@receiver(post_save, sender=User)
def create_user_profile_on_signup(sender, instance, created, **kwargs):
    """Creates a basic reader profile automatically when a user joins."""
    if created:
        UserProfile.objects.get_or_create(user=instance, role='reader')


@receiver(pre_save, sender=Article)
def track_approval_change(sender, instance, **kwargs):
    """Caches an article's prior approval status before changes are saved."""
    if instance.pk:
        try:
            previous = Article.objects.get(pk=instance.pk)
            instance._was_approved = previous.approved
        except Article.DoesNotExist:
            instance._was_approved = False
    else:
        instance._was_approved = False


@receiver(post_save, sender=Article)
def handle_article_approval_actions(sender, instance, created, **kwargs):
    """Triggers email notification distribution and webhooks upon article approval."""
    was_approved = getattr(instance, '_was_approved', False)

    if instance.approved and not was_approved:
        recipient_emails = set()

        if instance.publisher:
            for profile in instance.publisher.subscribed_readers.all():
                recipient_emails.add(profile.user.email)
        elif instance.author:
            for profile in instance.author.subscribed_readers.all():
                recipient_emails.add(profile.user.email)

        recipient_list = [email for email in recipient_emails if email]

        if recipient_list:
            send_mail(
                subject=f"New Article Approved: {instance.title}",
                message=f"Read our latest story!\n\n{instance.content}",
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'news@example.com'),
                recipient_list=recipient_list,
                fail_silently=True,
            )

        try:
            payload = {
                'id': instance.id,
                'title': instance.title,
                'source': str(instance.publisher if instance.publisher else instance.author),
                'status': 'Approved for Distribution'
            }
            requests.post('http://127.0.0', json=payload, timeout=1)
        except requests.exceptions.RequestException:
            pass


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    subscribed_author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='author_subscribers'
    )
    subscribed_publisher_id = models.IntegerField(
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            'user',
            'subscribed_author',
            'subscribed_publisher_id'
        )

    def __str__(self):
        return f"{self.user.username} subscription node"
