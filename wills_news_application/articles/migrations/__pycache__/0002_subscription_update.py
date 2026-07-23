from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('articles', '0001_initial'),  # Maps to your initial migration name
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='subscribed_author',
            field=models.ForeignKey(
                blank=True, 
                null=True, 
                on_delete=django.db.models.deletion.CASCADE, 
                related_name='author_subscribers', 
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='subscription',
            name='subscribed_publisher_id',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='subscription',
            unique_together={('user', 'subscribed_author', 'subscribed_publisher_id')},
        ),
    ]
