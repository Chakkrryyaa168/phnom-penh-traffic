from django.db import models


class Intersection(models.Model):
    name = models.CharField(max_length=255, unique=True, db_index=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_simulated = models.BooleanField(default=False, help_text="Indicates if loaded from demo dataset")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Intersection'
        verbose_name_plural = 'Intersections'

    def __str__(self):
        return self.name

    @property
    def record_count(self):
        return self.records.count()


class TrafficRecord(models.Model):
    intersection = models.ForeignKey(
        Intersection,
        on_delete=models.CASCADE,
        related_name='records'
    )
    timestamp = models.DateTimeField()
    volume = models.PositiveIntegerField()

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['intersection', 'timestamp']),
        ]
        verbose_name = 'Traffic Record'
        verbose_name_plural = 'Traffic Records'

    def __str__(self):
        return f"{self.intersection.name} @ {self.timestamp}: {self.volume}"
