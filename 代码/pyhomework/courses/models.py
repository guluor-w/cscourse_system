from django.db import models

class Course(models.Model):
    title = models.CharField(max_length=255)
    platform = models.CharField(max_length=100)
    url = models.URLField()
    teacher = models.CharField(max_length=100, blank=True)
    rating = models.FloatField(null=True, blank=True)
    learners = models.IntegerField(default=0)
    tags = models.TextField(blank=True)
    description = models.TextField(blank=True)
    school = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.platform}] {self.title}"
