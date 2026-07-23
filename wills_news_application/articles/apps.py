from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_project_groups(sender, **kwargs):
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType

    roles_permissions = {
        'Reader': {
            'article': ['view_article'],
            'newsletter': ['view_newsletter']
        },
        'Editor': {
            'article': ['view_article', 'change_article', 'delete_article'],
            'newsletter': ['view_newsletter', 'change_newsletter', 'delete_newsletter']
        },
        'Journalist': {
            'article': ['add_article', 'view_article', 'change_article', 'delete_article'],
            'newsletter': ['add_newsletter', 'view_newsletter', 'change_newsletter', 'delete_newsletter']
        }
    }

    for group_name, models_perms in roles_permissions.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        permission_objects = []

        for model_name, actions in models_perms.items():
            try:
                content_type = ContentType.objects.get(app_label='articles', model=model_name)
                for action in actions:
                    perm = Permission.objects.filter(content_type=content_type, codename=action).first()
                    if perm:
                        permission_objects.append(perm)
            except ContentType.DoesNotExist:
                continue

        group.permissions.set(permission_objects)


class ArticlesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'articles'

    def ready(self):
        import articles.signals

        post_migrate.connect(create_project_groups, sender=self)
