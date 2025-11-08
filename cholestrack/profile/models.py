# profile/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """
    Extended user profile for institutional research access.
    Stores additional information about researchers and clinicians.
    """
    ROLE_CHOICES = [
        ('RESEARCHER', 'Researcher'),
        ('CLINICIAN', 'Clinician'),
        ('DATA_MANAGER', 'Data Manager'),
        ('ADMIN', 'Administrator'),
    ]
    
    DEPARTMENT_CHOICES = [
        ('GENETICS', 'Genetics Department'),
        ('PEDIATRICS', 'Pediatrics'),
        ('LAB_DADAMO', 'Lab D\'Adamo'),
        ('BIOINFORMATICS', 'Bioinformatics'),
        ('OTHER', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Full Name")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='RESEARCHER', verbose_name="Role")
    team = models.CharField(max_length=30, choices=DEPARTMENT_CHOICES, default='LAB_DADAMO', verbose_name="Team/Department")
    institutional_email = models.EmailField(blank=True, null=True, verbose_name="Institutional Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Phone")
    institution_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Institution ID")
    
    # Profile completion tracking
    profile_completed = models.BooleanField(default=False, verbose_name="Profile Completed")
    approved = models.BooleanField(default=False, verbose_name="Account Approved")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


# Signal to automatically create UserProfile when User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()