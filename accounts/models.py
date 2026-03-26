import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from datetime import date, timedelta


class User(AbstractUser):
    phone_number             = models.CharField(max_length=15, null=True, blank=True)
    is_email_verified        = models.BooleanField(default=False)
    email_verification_token = models.UUIDField(default=uuid.uuid4, null=True, blank=True)
    is_blocked               = models.BooleanField(default=False)

    @property
    def is_gold(self):
        """Returns True if user has an active valid Gold subscription"""
        for sub in self.subscriptions.filter(status='active'):
            if sub.is_valid():
                return True
        return False

    def __str__(self):
        return self.email or self.username


class Profile(models.Model):

    # ── Choices ──────────────────────────────────────────────────────────────

    GENDER_CHOICES = [
        ('male',   'Male'),
        ('female', 'Female'),
    ]

    MARITAL_CHOICES = [
        ('never_married', 'Never Married'),
        ('divorced',      'Divorced'),
        ('widowed',       'Widowed'),
    ]

    PURPOSE_CHOICES = [
        ('marriage',         'Marriage'),
        ('serious_relation', 'Serious Relationship'),
        ('family_request',   'Family Request'),
    ]

    HEARD_CHOICES = [
        ('social_media', 'Social Media'),
        ('app_store',    'App Store'),
        ('friends',      'Friends'),
        ('ads',          'Ads'),
    ]

    EDUCATION_CHOICES = [
        ('high_school', 'High School'),
        ('bachelor',    'Bachelor'),
        ('master',      'Master'),
        ('phd',         'PhD'),
        ('other',       'Other'),
    ]

    FAITH_CHOICES = [
        ('very',     'Very Practicing'),
        ('moderate', 'Moderate'),
        ('somewhat', 'Somewhat Practicing'),
    ]

    HALAL_CHOICES = [
        ('always',     'Always'),
        ('sometimes',  'Sometimes'),
        ('not_strict', 'Not Strict'),
    ]

    DRESS_CHOICES = [
        ('modest',          'Modest'),
        ('somewhat_modest', 'Somewhat Modest'),
        ('modern',          'Modern'),
    ]

    YES_NO_CHOICES = [
        ('yes', 'Yes'),
        ('no',  'No'),
    ]

    BORN_MUSLIM_CHOICES = [
        ('yes',    'Yes'),
        ('revert', 'Revert'),
    ]

    # ── Relationship ─────────────────────────────────────────────────────────

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    # ── Section 1: Basic Information ─────────────────────────────────────────

    date_of_birth  = models.DateField(null=True, blank=True)
    gender         = models.CharField(max_length=10,  choices=GENDER_CHOICES,   blank=True)
    height         = models.CharField(max_length=10,  blank=True)
    nationality    = models.CharField(max_length=60,  blank=True)
    caste_sect     = models.CharField(max_length=60,  blank=True)
    marital_status = models.CharField(max_length=20,  choices=MARITAL_CHOICES,  blank=True)
    has_children   = models.CharField(max_length=5,   choices=YES_NO_CHOICES,   blank=True)

    # ── Section 2: Purpose & Discovery ───────────────────────────────────────

    purpose    = models.CharField(max_length=20, choices=PURPOSE_CHOICES, blank=True)
    heard_from = models.CharField(max_length=20, choices=HEARD_CHOICES,   blank=True)

    # ── Section 3: Education & Profession ────────────────────────────────────

    education  = models.CharField(max_length=20,  choices=EDUCATION_CHOICES, blank=True)
    profession = models.CharField(max_length=100, blank=True)

    # ── Section 4: Religious Information ─────────────────────────────────────

    faith_level = models.CharField(max_length=10, choices=FAITH_CHOICES,       blank=True)
    born_muslim = models.CharField(max_length=10, choices=BORN_MUSLIM_CHOICES, blank=True)
    halal_food  = models.CharField(max_length=15, choices=HALAL_CHOICES,       blank=True)

    # ── Section 5: Lifestyle ──────────────────────────────────────────────────

    dress_style = models.CharField(max_length=20, choices=DRESS_CHOICES,  blank=True)
    smoking     = models.CharField(max_length=5,  choices=YES_NO_CHOICES, blank=True)
    drinking    = models.CharField(max_length=5,  choices=YES_NO_CHOICES, blank=True)

    # ── Section 6: Location & Background ─────────────────────────────────────

    country        = models.CharField(max_length=60,  blank=True)
    city           = models.CharField(max_length=60,  blank=True)
    grew_up_in     = models.CharField(max_length=100, blank=True)
    open_to_abroad = models.CharField(max_length=5,   choices=YES_NO_CHOICES, blank=True)

    # ── Section 7: Bio & Media ────────────────────────────────────────────────

    about_me      = models.TextField(blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)

    # ── Section 8: Verification ───────────────────────────────────────────────

    VERIFICATION_STATUS = [
        ('unverified', 'Unverified'),
        ('pending',    'Pending Review'),
        ('verified',   'Verified'),
        ('rejected',   'Rejected'),
    ]

    phone_verified      = models.BooleanField(default=False)
    selfie_photo        = models.ImageField(upload_to='selfies/', null=True, blank=True)
    verification_status = models.CharField(
        max_length=15,
        choices=VERIFICATION_STATUS,
        default='unverified'
    )
    verified_badge = models.BooleanField(default=False)

    # ── Timestamps ────────────────────────────────────────────────────────────

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Methods ───────────────────────────────────────────────────────────────

    def completion_percentage(self):
        fields = [
            self.date_of_birth,
            self.gender,
            self.height,
            self.nationality,
            self.caste_sect,
            self.marital_status,
            self.has_children,
            self.purpose,
            self.heard_from,
            self.education,
            self.profession,
            self.faith_level,
            self.born_muslim,
            self.halal_food,
            self.dress_style,
            self.smoking,
            self.drinking,
            self.country,
            self.city,
            self.grew_up_in,
            self.open_to_abroad,
            self.about_me,
            self.profile_photo,
        ]
        filled = sum(1 for f in fields if f)
        return int((filled / len(fields)) * 100)

    def __str__(self):
        return f"{self.user.get_full_name()}'s Profile"


# ──────────────────────────────────────────
# PARTNER PREFERENCE
# ──────────────────────────────────────────

class PartnerPreference(models.Model):

    # ── Choices ──────────────────────────────────────────────────────────────

    MARITAL_CHOICES = [
        ('any',           'Any'),
        ('never_married', 'Never Married'),
        ('divorced',      'Divorced'),
        ('widowed',       'Widowed'),
    ]

    EDUCATION_CHOICES = [
        ('any',         'Any'),
        ('high_school', 'High School'),
        ('bachelor',    'Bachelor'),
        ('master',      'Master'),
        ('phd',         'PhD'),
    ]

    FAITH_CHOICES = [
        ('any',      'Any'),
        ('very',     'Very Practicing'),
        ('moderate', 'Moderate'),
        ('somewhat', 'Somewhat Practicing'),
    ]

    SMOKING_CHOICES = [
        ('any', 'Any'),
        ('no',  'Non Smoker'),
        ('yes', 'Smoker'),
    ]

    DRINKING_CHOICES = [
        ('any', 'Any'),
        ('no',  'Non Drinker'),
        ('yes', 'Drinker'),
    ]

    # ── Relationship ─────────────────────────────────────────────────────────

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='partner_preference'
    )

    # ── Age Range ─────────────────────────────────────────────────────────────

    min_age = models.PositiveIntegerField(default=18)
    max_age = models.PositiveIntegerField(default=40)

    # ── Location ──────────────────────────────────────────────────────────────

    preferred_country = models.CharField(max_length=60, blank=True)

    # ── Background ────────────────────────────────────────────────────────────

    preferred_caste_sect = models.CharField(max_length=60, blank=True)
    preferred_ethnicity  = models.CharField(max_length=60, blank=True)

    # ── Filters ───────────────────────────────────────────────────────────────

    preferred_marital_status = models.CharField(
        max_length=20, choices=MARITAL_CHOICES, default='any')

    preferred_education = models.CharField(
        max_length=20, choices=EDUCATION_CHOICES, default='any')

    preferred_faith_level = models.CharField(
        max_length=10, choices=FAITH_CHOICES, default='any')

    preferred_smoking = models.CharField(
        max_length=5, choices=SMOKING_CHOICES, default='any')

    preferred_drinking = models.CharField(
        max_length=5, choices=DRINKING_CHOICES, default='any')

    # ── Timestamps ────────────────────────────────────────────────────────────

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()}'s Preferences"


# ──────────────────────────────────────────
# INTEREST
# ──────────────────────────────────────────

class Interest(models.Model):

    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    sender   = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_interests')
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_interests')
    status   = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('sender', 'receiver')

    def __str__(self):
        return f"{self.sender} → {self.receiver} ({self.status})"


# ──────────────────────────────────────────
# CHAT MODELS
# ──────────────────────────────────────────

class Conversation(models.Model):
    """A chat between two matched users"""

    user1      = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='conversations_as_user1')
    user2      = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='conversations_as_user2')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user1', 'user2')

    def get_other_user(self, current_user):
        """Returns the other participant in the conversation"""
        return self.user2 if self.user1 == current_user else self.user1

    def __str__(self):
        return f"Chat: {self.user1} & {self.user2}"


class Message(models.Model):
    """A single message inside a conversation"""

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages')
    sender    = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages')
    body      = models.TextField(blank=True)   # ← make blank=True
    image     = models.ImageField(             # ← Add this
        upload_to='chat_images/', null=True, blank=True)
    is_read   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender} — {self.body[:40]}"


class WaliInvite(models.Model):
    """Guardian / Wali mode — family member access to conversation"""

    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='wali_invites')
    invited_by   = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='wali_invites_sent')
    wali_email   = models.EmailField()
    wali_name    = models.CharField(max_length=100)
    access_token = models.UUIDField(default=uuid.uuid4, unique=True)
    status       = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wali: {self.wali_name} for {self.conversation}"


# ──────────────────────────────────────────
# NOTIFICATION MODEL
# ──────────────────────────────────────────

class Notification(models.Model):

    TYPE_CHOICES = [
        ('interest_received', '💌 Someone sent you an interest'),
        ('interest_accepted', '✅ Your interest was accepted'),
        ('new_match',         '💞 You have a new match!'),
        ('new_message',       '💬 You have a new message'),
    ]

    recipient  = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications')
    sender     = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='sent_notifications', null=True, blank=True)
    notif_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    message    = models.CharField(max_length=255)
    link       = models.CharField(max_length=255, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient} — {self.notif_type}"


# ──────────────────────────────────────────
# SUBSCRIPTION MODEL
# ──────────────────────────────────────────

class Subscription(models.Model):

    PLAN_CHOICES = [
        ('1_month',  '1 Month — Rs. 1,000'),
        ('3_months', '3 Months — Rs. 2,500'),
        ('6_months', '6 Months — Rs. 5,000'),
    ]

    PLAN_PRICES = {
        '1_month':  1000,
        '3_months': 2500,
        '6_months': 5000,
    }

    PLAN_DAYS = {
        '1_month':  30,
        '3_months': 90,
        '6_months': 180,
    }

    PAYMENT_CHOICES = [
        ('jazzcash',  'JazzCash'),
        ('easypaisa', 'Easypaisa'),
    ]

    STATUS_CHOICES = [
        ('pending',  'Pending Review'),
        ('active',   'Active'),
        ('expired',  'Expired'),
        ('rejected', 'Rejected'),
    ]

    user           = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='subscriptions')
    plan           = models.CharField(max_length=20, choices=PLAN_CHOICES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    transaction_id = models.CharField(max_length=100, unique=True)
    amount         = models.PositiveIntegerField()
    status         = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending')
    start_date     = models.DateField(null=True, blank=True)
    end_date       = models.DateField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def is_valid(self):
        """Check if subscription is currently active and not expired"""
        if self.status == 'active' and self.end_date:
            return self.end_date >= date.today()
        return False

    def __str__(self):
        return f"{self.user} — {self.plan} ({self.status})"