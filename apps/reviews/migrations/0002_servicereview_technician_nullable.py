from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0001_initial'),
        ('services', '0002_alter_servicerequesthistory_new_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicereview',
            name='technician',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='reviews',
                to='services.technician',
                verbose_name='Мастер',
            ),
        ),
    ]
