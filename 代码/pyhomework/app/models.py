# apps/users/models.py
from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.jpg')
    bio = models.TextField(max_length=500, blank=True, help_text="个人简介")
    learning_goal = models.CharField(max_length=100, blank=True, help_text="学习目标")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # 保存时压缩头像
        super().save(*args, **kwargs)
        try:
            img = Image.open(self.avatar.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 3)
                img.thumbnail(output_size)
                img.save(self.avatar.path)
        except Exception as e:
            print(f"头像处理错误: {e}")
    
    def __str__(self):
        return f"{self.user.username}的资料"

# 用户创建信号处理
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance,** kwargs):
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)  # 修复已有用户无profile的情况