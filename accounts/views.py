import uuid
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q

from .models import (
    User, Profile, PartnerPreference,
    Interest, Conversation, Message, WaliInvite,
    Notification, Subscription,
)
from .forms import (
    RegisterForm, LoginForm,
    ProfileStep1Form, ProfileStep2Form, ProfileStep3Form,
    ProfileStep4Form, ProfileStep5Form, ProfileStep6Form,
    ProfileStep7Form, PartnerPreferenceForm,
)


# ──────────────────────────────────────────
# HOME
# ──────────────────────────────────────────

def home_view(request):
    return render(request, 'home.html')


# ──────────────────────────────────────────
# REGISTER
# ──────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_verification_email(request, user)
            messages.success(request,
                'Account created! Please check your email and click the verification link.')
            return redirect('login')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def send_verification_email(request, user):
    token = str(user.email_verification_token)
    uid   = urlsafe_base64_encode(force_bytes(user.pk))
    link  = request.build_absolute_uri(
        f'/verify-email/{uid}/{token}/'
    )
    send_mail(
        subject='Verify your email — Nikkah Connect',
        message=(
            f'Hi {user.first_name},\n\n'
            f'Click the link below to verify your email:\n\n{link}\n\n'
            f'If you did not register, ignore this email.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


# ──────────────────────────────────────────
# VERIFY EMAIL
# ──────────────────────────────────────────

def verify_email_view(request, uid, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user    = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError):
        messages.error(request, 'Invalid verification link.')
        return redirect('login')

    if str(user.email_verification_token) == token:
        user.is_email_verified        = True
        user.email_verification_token = None
        user.save()
        messages.success(request, '✅ Email verified! You can now log in.')
    else:
        messages.error(request, 'Verification link is invalid or already used.')

    return redirect('login')


# ──────────────────────────────────────────
# LOGIN
# ──────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_email_verified:
                messages.warning(request,
                    'Please verify your email first. Check your inbox.')
                return redirect('login')
            # Block check
            if user.is_blocked:
                messages.error(request,
                    '🚫 Your account has been blocked. Please contact support.')
                return redirect('login')
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name}!')
            profile = get_or_create_profile(user)
            if profile.completion_percentage() < 10:
                return redirect('profile_create_step', step=1)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


# ──────────────────────────────────────────
# LOGOUT
# ──────────────────────────────────────────

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ──────────────────────────────────────────
# FORGOT PASSWORD
# ──────────────────────────────────────────

def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        try:
            user  = User.objects.get(email=email)
            uid   = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link  = request.build_absolute_uri(
                f'/reset-password/{uid}/{token}/'
            )
            send_mail(
                subject='Reset your password — Nikkah Connect',
                message=(
                    f'Hi {user.first_name},\n\n'
                    f'Click the link below to reset your password:\n\n{link}\n\n'
                    f'This link expires in 24 hours.\n\n'
                    f'If you did not request this, ignore this email.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
        except User.DoesNotExist:
            pass

        messages.success(request,
            'If that email is registered, a reset link has been sent. Check your inbox.')
        return redirect('forgot_password')

    return render(request, 'accounts/forgot_password.html')


# ──────────────────────────────────────────
# RESET PASSWORD
# ──────────────────────────────────────────

def reset_password_view(request, uid, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user    = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError):
        messages.error(request, 'Invalid reset link.')
        return redirect('login')

    if not default_token_generator.check_token(user, token):
        messages.error(request,
            'This reset link has expired or already been used.')
        return redirect('forgot_password')

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,
                'Password reset successful! You can now log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = SetPasswordForm(user)

    return render(request, 'accounts/reset_password.html', {'form': form})


# ──────────────────────────────────────────
# PROFILE HELPER
# ──────────────────────────────────────────

def get_or_create_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


# ──────────────────────────────────────────
# PROFILE CREATION — Multi Step Wizard
# ──────────────────────────────────────────

STEP_FORMS = {
    1: ProfileStep1Form,
    2: ProfileStep2Form,
    3: ProfileStep3Form,
    4: ProfileStep4Form,
    5: ProfileStep5Form,
    6: ProfileStep6Form,
    7: ProfileStep7Form,
}

STEP_TITLES = {
    1: 'Basic Information',
    2: 'Purpose & Discovery',
    3: 'Education & Profession',
    4: 'Religious Information',
    5: 'Lifestyle',
    6: 'Location & Background',
    7: 'Bio & Photo',
}

TOTAL_STEPS = 7


def profile_create_view(request, step=1):
    if not request.user.is_authenticated:
        return redirect('login')

    step      = int(step)
    profile   = get_or_create_profile(request.user)
    FormClass = STEP_FORMS.get(step)

    if not FormClass:
        return redirect('dashboard')

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            if step < TOTAL_STEPS:
                return redirect('profile_create_step', step=step + 1)
            else:
                messages.success(request,
                    '🎉 Profile completed! Welcome to Nikkah Connect.')
                return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = FormClass(instance=profile)

    progress = int((step / TOTAL_STEPS) * 100)

    return render(request, 'accounts/profile_create.html', {
        'form':        form,
        'step':        step,
        'total_steps': TOTAL_STEPS,
        'step_title':  STEP_TITLES[step],
        'progress':    progress,
        'profile':     profile,
        'step_titles': STEP_TITLES,
    })


# ──────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────

def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    profile    = get_or_create_profile(request.user)
    preference = PartnerPreference.objects.filter(
        user=request.user).first()

    return render(request, 'accounts/dashboard.html', {
        'profile':    profile,
        'preference': preference,
    })


# ──────────────────────────────────────────
# PROFILE DETAIL
# ──────────────────────────────────────────

def profile_detail_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    profile = get_or_create_profile(request.user)
    return render(request, 'accounts/profile_detail.html', {
        'profile': profile,
    })


# ──────────────────────────────────────────
# PROFILE VERIFICATION
# ──────────────────────────────────────────

def verify_profile_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    profile = get_or_create_profile(request.user)

    if profile.verified_badge:
        messages.success(request, '✅ Your profile is already verified!')
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'confirm_phone':
            profile.phone_verified = True
            profile.save()
            messages.success(request,
                '✅ Phone number confirmed successfully!')
            return redirect('verify_profile')

        if action == 'upload_selfie':
            selfie = request.FILES.get('selfie_photo')
            if not selfie:
                messages.error(request,
                    'Please select a selfie photo to upload.')
                return redirect('verify_profile')

            profile.selfie_photo        = selfie
            profile.verification_status = 'verified'
            profile.verified_badge      = True
            profile.save()
            messages.success(request,
                '🎉 Congratulations! Your profile is now Verified!')
            return redirect('dashboard')

    return render(request, 'accounts/verify_profile.html', {
        'profile': profile,
    })


# ──────────────────────────────────────────
# PARTNER PREFERENCES
# ──────────────────────────────────────────

def partner_preference_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    preference, created = PartnerPreference.objects.get_or_create(
        user=request.user
    )

    if request.method == 'POST':
        form = PartnerPreferenceForm(request.POST, instance=preference)
        if form.is_valid():
            form.save()
            messages.success(request,
                '✅ Partner preferences saved successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = PartnerPreferenceForm(instance=preference)

    return render(request, 'accounts/partner_preferences.html', {
        'form':       form,
        'preference': preference,
        'created':    created,
    })


# ──────────────────────────────────────────
# BROWSE PROFILES
# ──────────────────────────────────────────

def browse_profiles_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    my_profile = get_or_create_profile(request.user)
    preference = PartnerPreference.objects.filter(
        user=request.user).first()

    if my_profile.gender == 'male':
        opposite_gender = 'female'
    elif my_profile.gender == 'female':
        opposite_gender = 'male'
    else:
        opposite_gender = None

    all_profiles = Profile.objects.exclude(
        user=request.user
    ).select_related('user')

    filtered_profiles = []

    for p in all_profiles:

        if p.completion_percentage() < 50:
            continue

        if opposite_gender and p.gender != opposite_gender:
            continue

        if preference:

            if p.date_of_birth:
                today = date.today()
                age = today.year - p.date_of_birth.year - (
                    (today.month, today.day) <
                    (p.date_of_birth.month, p.date_of_birth.day)
                )
                if age < preference.min_age or age > preference.max_age:
                    continue

            if preference.preferred_country:
                if p.country.lower() != preference.preferred_country.lower():
                    continue

            if preference.preferred_education != 'any':
                if p.education != preference.preferred_education:
                    continue

            if preference.preferred_marital_status != 'any':
                if p.marital_status != preference.preferred_marital_status:
                    continue

            if preference.preferred_faith_level != 'any':
                if p.faith_level != preference.preferred_faith_level:
                    continue

            if preference.preferred_smoking != 'any':
                if p.smoking != preference.preferred_smoking:
                    continue

            if preference.preferred_drinking != 'any':
                if p.drinking != preference.preferred_drinking:
                    continue

            if preference.preferred_caste_sect:
                if preference.preferred_caste_sect.lower() not in \
                        p.caste_sect.lower():
                    continue

            if preference.preferred_ethnicity:
                if preference.preferred_ethnicity.lower() not in \
                        p.nationality.lower():
                    continue

        filtered_profiles.append(p)

    sent_interests = Interest.objects.filter(
        sender=request.user
    ).values_list('receiver_id', flat=True)

    my_accepted_sent = Interest.objects.filter(
        sender=request.user, status='accepted'
    ).values_list('receiver_id', flat=True)

    my_accepted_received = Interest.objects.filter(
        receiver=request.user, status='accepted'
    ).values_list('sender_id', flat=True)

    matched_ids = list(
        set(my_accepted_sent) & set(my_accepted_received)
    )

    return render(request, 'accounts/browse_profiles.html', {
        'profiles':       filtered_profiles,
        'sent_interests': list(sent_interests),
        'matched_ids':    matched_ids,
        'preference':     preference,
    })


# ──────────────────────────────────────────
# NOTIFICATION HELPER
# ──────────────────────────────────────────

def create_notification(recipient, sender, notif_type, message, link=''):
    """Create a notification — skip if recipient is sender.
    For messages: update existing instead of creating duplicates."""
    if recipient == sender:
        return

    if notif_type == 'new_message':
        existing = Notification.objects.filter(
            recipient=recipient,
            sender=sender,
            notif_type='new_message',
        ).first()

        if existing:
            existing.message = message
            existing.is_read = False
            existing.save()
            return

    Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notif_type=notif_type,
        message=message,
        link=link,
    )


# ──────────────────────────────────────────
# SEND INTEREST
# ──────────────────────────────────────────

def send_interest_view(request, user_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        receiver = get_object_or_404(User, id=user_id)

        if receiver == request.user:
            messages.error(request,
                'You cannot send interest to yourself.')
            return redirect('browse_profiles')

        already_sent = Interest.objects.filter(
            sender=request.user,
            receiver=receiver
        ).exists()

        if already_sent:
            messages.warning(request,
                'You have already sent interest to this person.')
        else:
            Interest.objects.create(
                sender=request.user,
                receiver=receiver,
                status='pending'
            )
            messages.success(request,
                f'💌 Interest sent to {receiver.get_full_name()}!')

            create_notification(
                recipient=receiver,
                sender=request.user,
                notif_type='interest_received',
                message=f'💌 {request.user.get_full_name()} sent you an interest!',
                link='/my-interests/?tab=received',
            )

    return redirect('browse_profiles')


# ──────────────────────────────────────────
# RESPOND TO INTEREST (Accept / Reject)
# ──────────────────────────────────────────

def respond_interest_view(request, interest_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        interest = get_object_or_404(
            Interest,
            id=interest_id,
            receiver=request.user
        )
        action = request.POST.get('action')

        if action == 'accept':
            interest.status = 'accepted'
            interest.save()

            create_notification(
                recipient=interest.sender,
                sender=request.user,
                notif_type='interest_accepted',
                message=f'✅ {request.user.get_full_name()} accepted your interest!',
                link='/my-interests/?tab=sent',
            )

            reverse_interest = Interest.objects.filter(
                sender=request.user,
                receiver=interest.sender,
                status='accepted'
            ).exists()

            if reverse_interest:
                create_notification(
                    recipient=interest.sender,
                    sender=request.user,
                    notif_type='new_match',
                    message=f'💞 You and {request.user.get_full_name()} are now a match!',
                    link='/my-interests/?tab=matches',
                )
                create_notification(
                    recipient=request.user,
                    sender=interest.sender,
                    notif_type='new_match',
                    message=f'💞 You and {interest.sender.get_full_name()} are now a match!',
                    link='/my-interests/?tab=matches',
                )

            messages.success(request,
                f'🎉 You accepted {interest.sender.get_full_name()}\'s interest!')

        elif action == 'reject':
            interest.status = 'rejected'
            interest.save()
            messages.info(request,
                f'You declined {interest.sender.get_full_name()}\'s interest.')

    return redirect('my_interests')


# ──────────────────────────────────────────
# MY INTERESTS & MATCHES (tabbed page)
# ──────────────────────────────────────────

def my_interests_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    sent = Interest.objects.filter(
        sender=request.user
    ).select_related('receiver', 'receiver__profile').order_by('-created_at')

    received = Interest.objects.filter(
        receiver=request.user
    ).select_related('sender', 'sender__profile').order_by('-created_at')

    my_accepted_sent = Interest.objects.filter(
        sender=request.user, status='accepted'
    ).values_list('receiver_id', flat=True)

    my_accepted_received = Interest.objects.filter(
        receiver=request.user, status='accepted'
    ).values_list('sender_id', flat=True)

    mutual_ids = set(my_accepted_sent) & set(my_accepted_received)

    matched_users = User.objects.filter(
        id__in=mutual_ids
    ).select_related('profile')

    active_tab = request.GET.get('tab', 'received')

    return render(request, 'accounts/my_interests.html', {
        'sent':          sent,
        'received':      received,
        'matched_users': matched_users,
        'active_tab':    active_tab,
    })


# ──────────────────────────────────────────
# CHAT HELPER — Get or Create Conversation
# ──────────────────────────────────────────

def get_or_create_conversation(user1, user2):
    """Always store user with lower ID as user1 to avoid duplicates"""
    if user1.id > user2.id:
        user1, user2 = user2, user1
    conversation, _ = Conversation.objects.get_or_create(
        user1=user1, user2=user2)
    return conversation


# ──────────────────────────────────────────
# MY CONVERSATIONS LIST
# ──────────────────────────────────────────

def my_conversations_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    conversations = (
        Conversation.objects.filter(user1=request.user) |
        Conversation.objects.filter(user2=request.user)
    ).order_by('-updated_at')

    conv_list = []
    for conv in conversations:
        other_user   = conv.get_other_user(request.user)
        last_message = conv.messages.last()
        unread_count = conv.messages.filter(
            is_read=False
        ).exclude(sender=request.user).count()
        conv_list.append({
            'conversation': conv,
            'other_user':   other_user,
            'last_message': last_message,
            'unread_count': unread_count,
        })

    return render(request, 'accounts/conversations.html', {
        'conv_list': conv_list,
    })


# ──────────────────────────────────────────
# OPEN CHAT
# ──────────────────────────────────────────

def chat_view(request, user_id):
    if not request.user.is_authenticated:
        return redirect('login')

    other_user = get_object_or_404(User, id=user_id)

    # Security — only mutual matches can chat
    is_matched = (
        Interest.objects.filter(
            sender=request.user,
            receiver=other_user,
            status='accepted'
        ).exists()
        and
        Interest.objects.filter(
            sender=other_user,
            receiver=request.user,
            status='accepted'
        ).exists()
    )

    if not is_matched:
        messages.error(request,
            '💬 Chat is only available after a mutual match.')
        return redirect('my_interests')

    conversation = get_or_create_conversation(request.user, other_user)

    # Mark received messages as read
    conversation.messages.filter(
        is_read=False
    ).exclude(sender=request.user).update(is_read=True)

    # Handle sending a new message
    if request.method == 'POST':
        body  = request.POST.get('body', '').strip()
        image = request.FILES.get('chat_image')

        # Gold check for image uploads
        if image and not request.user.is_gold:
            messages.error(request,
                '📷 Photo sharing is only available for Gold members. '
                'Upgrade to Gold to send photos!')
            return redirect('chat', user_id=user_id)

        # Must have either text or image
        if body or image:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                body=body,
                image=image if image else None,
            )
            conversation.save()

            # 🔔 Notify the other user — one notification only
            create_notification(
                recipient=other_user,
                sender=request.user,
                notif_type='new_message',
                message=f'💬 {request.user.get_full_name()} sent you a message!',
                link=f'/chat/{request.user.id}/',
            )

        return redirect('chat', user_id=user_id)

    chat_messages = conversation.messages.all()

    wali_invites = WaliInvite.objects.filter(
        conversation=conversation,
        invited_by=request.user
    )

    return render(request, 'accounts/chat.html', {
        'conversation':  conversation,
        'other_user':    other_user,
        'chat_messages': chat_messages,
        'wali_invites':  wali_invites,
    })


# ──────────────────────────────────────────
# INVITE WALI / GUARDIAN
# ──────────────────────────────────────────

def invite_wali_view(request, conversation_id):
    if not request.user.is_authenticated:
        return redirect('login')

    conversation = get_object_or_404(Conversation, id=conversation_id)

    if request.user not in [conversation.user1, conversation.user2]:
        messages.error(request, 'You are not part of this conversation.')
        return redirect('dashboard')

    other_user = conversation.get_other_user(request.user)

    if request.method == 'POST':
        wali_name  = request.POST.get('wali_name', '').strip()
        wali_email = request.POST.get('wali_email', '').strip()

        if not wali_name or not wali_email:
            messages.error(request,
                'Please provide both name and email for the Wali.')
            return redirect('chat', user_id=other_user.id)

        invite = WaliInvite.objects.create(
            conversation=conversation,
            invited_by=request.user,
            wali_name=wali_name,
            wali_email=wali_email,
        )

        wali_link = request.build_absolute_uri(
            f'/wali-access/{invite.access_token}/'
        )

        try:
            send_mail(
                subject='You have been invited as a Guardian (Wali) — Nikkah Connect',
                message=(
                    f'As-salamu alaykum {wali_name},\n\n'
                    f'{request.user.get_full_name()} has invited you to join their '
                    f'conversation on Nikkah Connect as a Guardian (Wali).\n\n'
                    f'You can view the conversation by clicking the link below:\n'
                    f'{wali_link}\n\n'
                    f'This link is private. Please do not share it with others.\n\n'
                    f'JazakAllah Khair,\nNikkah Connect Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[wali_email],
                fail_silently=True,
            )
            messages.success(request,
                f'✅ Guardian invite sent to {wali_name} ({wali_email})!')
        except Exception:
            messages.warning(request,
                f'Invite saved but email could not be sent to {wali_email}.')

    return redirect('chat', user_id=other_user.id)


# ──────────────────────────────────────────
# WALI ACCESS — Read Only View
# ──────────────────────────────────────────

def wali_access_view(request, token):
    invite = get_object_or_404(WaliInvite, access_token=token)

    if invite.status == 'pending':
        invite.status = 'accepted'
        invite.save()

    conversation  = invite.conversation
    chat_messages = conversation.messages.all()

    return render(request, 'accounts/wali_view.html', {
        'invite':        invite,
        'conversation':  conversation,
        'chat_messages': chat_messages,
    })


# ──────────────────────────────────────────
# NOTIFICATIONS
# ──────────────────────────────────────────

def notifications_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')

    return render(request, 'accounts/notifications.html', {
        'notifications': notifications,
    })


def mark_notification_read_view(request, notif_id):
    if not request.user.is_authenticated:
        return redirect('login')

    notif = get_object_or_404(
        Notification, id=notif_id, recipient=request.user)

    link = notif.link
    notif.delete()

    if link:
        return redirect(link)
    return redirect('notifications')


# ──────────────────────────────────────────
# PRICING PAGE
# ──────────────────────────────────────────

def pricing_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    active_sub  = Subscription.objects.filter(
        user=request.user, status='active').first()
    pending_sub = Subscription.objects.filter(
        user=request.user, status='pending').first()

    return render(request, 'accounts/pricing.html', {
        'active_sub':  active_sub,
        'pending_sub': pending_sub,
        'is_gold':     request.user.is_gold,
    })


# ──────────────────────────────────────────
# UPGRADE — Submit Payment
# ──────────────────────────────────────────

PLAN_PRICES = {
    '1_month':  1000,
    '3_months': 2500,
    '6_months': 5000,
}

JAZZCASH_NUMBER  = '0310-7872939'
EASYPAISA_NUMBER = '0310-7872939'


def upgrade_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.user.is_gold:
        messages.info(request,
            '✅ You already have an active Gold subscription!')
        return redirect('pricing')

    already_pending = Subscription.objects.filter(
        user=request.user, status='pending').exists()

    if already_pending:
        messages.warning(request,
            '⏳ You already have a pending payment request. '
            'Please wait for admin approval.')
        return redirect('pricing')

    if request.method == 'POST':
        plan           = request.POST.get('plan')
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id', '').strip()

        if not plan or plan not in PLAN_PRICES:
            messages.error(request, 'Please select a valid plan.')
            return redirect('upgrade')

        if not payment_method or \
                payment_method not in ['jazzcash', 'easypaisa']:
            messages.error(request, 'Please select a payment method.')
            return redirect('upgrade')

        if not transaction_id:
            messages.error(request,
                'Please enter the Transaction ID from your payment.')
            return redirect('upgrade')

        if Subscription.objects.filter(
                transaction_id=transaction_id).exists():
            messages.error(request,
                'This Transaction ID has already been used. '
                'Please check and try again.')
            return redirect('upgrade')

        Subscription.objects.create(
            user=request.user,
            plan=plan,
            payment_method=payment_method,
            transaction_id=transaction_id,
            amount=PLAN_PRICES[plan],
            status='pending',
        )

        messages.success(request,
            '✅ Payment request submitted! Your Gold plan will be '
            'activated after admin verification. '
            'This usually takes a few hours.')
        return redirect('pricing')

    return render(request, 'accounts/upgrade.html', {
        'JAZZCASH_NUMBER':  JAZZCASH_NUMBER,
        'EASYPAISA_NUMBER': EASYPAISA_NUMBER,
        'PLAN_PRICES':      PLAN_PRICES,
    })


# ──────────────────────────────────────────
# MY SUBSCRIPTION
# ──────────────────────────────────────────

def my_subscription_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    subscriptions = Subscription.objects.filter(
        user=request.user).order_by('-created_at')
    active_sub = subscriptions.filter(status='active').first()

    return render(request, 'accounts/my_subscription.html', {
        'subscriptions': subscriptions,
        'active_sub':    active_sub,
        'is_gold':       request.user.is_gold,
    })


# ──────────────────────────────────────────
# ADMIN PANEL — Access Check Helper
# ──────────────────────────────────────────

def admin_required(view_func):
    """Decorator to restrict access to staff only"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        if not request.user.is_staff:
            messages.error(request,
                '🚫 You do not have permission to access this page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ──────────────────────────────────────────
# ADMIN LOGIN
# ──────────────────────────────────────────

def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    error = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        from django.contrib.auth import authenticate
        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_staff:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            error = '🚫 Invalid credentials or insufficient permissions.'

    return render(request, 'admin_panel/login.html', {'error': error})


def admin_logout_view(request):
    logout(request)
    return redirect('admin_login')


# ──────────────────────────────────────────
# ADMIN DASHBOARD
# ──────────────────────────────────────────

@admin_required
def admin_dashboard_view(request):
    total_users      = User.objects.filter(is_staff=False).count()
    total_gold       = Subscription.objects.filter(status='active').count()
    pending_payments = Subscription.objects.filter(status='pending').count()
    total_matches    = Interest.objects.filter(status='accepted').count()
    new_users_today  = User.objects.filter(
        date_joined__date=date.today(), is_staff=False).count()
    blocked_users    = User.objects.filter(is_blocked=True).count()

    recent_pending = Subscription.objects.filter(
        status='pending').order_by('-created_at')[:5]
    recent_users   = User.objects.filter(
        is_staff=False).order_by('-date_joined')[:5]

    return render(request, 'admin_panel/dashboard.html', {
        'total_users':      total_users,
        'total_gold':       total_gold,
        'pending_payments': pending_payments,
        'total_matches':    total_matches,
        'new_users_today':  new_users_today,
        'blocked_users':    blocked_users,
        'recent_pending':   recent_pending,
        'recent_users':     recent_users,
    })


# ──────────────────────────────────────────
# ADMIN — USERS
# ──────────────────────────────────────────

@admin_required
def admin_users_view(request):
    search    = request.GET.get('search', '').strip()
    filter_by = request.GET.get('filter', 'all')

    users = User.objects.filter(is_staff=False).order_by('-date_joined')

    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)  |
            Q(email__icontains=search)
        )

    if filter_by == 'gold':
        gold_ids = Subscription.objects.filter(
            status='active').values_list('user_id', flat=True)
        users = users.filter(id__in=gold_ids)
    elif filter_by == 'blocked':
        users = users.filter(is_blocked=True)
    elif filter_by == 'unverified':
        users = users.filter(profile__verified_badge=False)

    return render(request, 'admin_panel/users.html', {
        'users':     users,
        'search':    search,
        'filter_by': filter_by,
    })


@admin_required
def admin_user_detail_view(request, user_id):
    user    = get_object_or_404(User, id=user_id, is_staff=False)
    profile = get_or_create_profile(user)
    subscriptions      = Subscription.objects.filter(user=user)
    interests_sent     = Interest.objects.filter(sender=user).count()
    interests_received = Interest.objects.filter(receiver=user).count()

    return render(request, 'admin_panel/user_detail.html', {
        'target_user':        user,
        'profile':            profile,
        'subscriptions':      subscriptions,
        'interests_sent':     interests_sent,
        'interests_received': interests_received,
    })


@admin_required
def admin_block_user_view(request, user_id):
    user = get_object_or_404(User, id=user_id, is_staff=False)
    if request.method == 'POST':
        user.is_blocked = not user.is_blocked
        user.save()
        status = 'blocked' if user.is_blocked else 'unblocked'
        messages.success(request,
            f'✅ User {user.get_full_name()} has been {status}.')
    return redirect('admin_user_detail', user_id=user_id)


@admin_required
def admin_delete_user_view(request, user_id):
    user = get_object_or_404(User, id=user_id, is_staff=False)
    if request.method == 'POST':
        name = user.get_full_name()
        user.delete()
        messages.success(request,
            f'✅ User {name} has been permanently deleted.')
        return redirect('admin_users')
    return redirect('admin_user_detail', user_id=user_id)


# ──────────────────────────────────────────
# ADMIN — SUBSCRIPTIONS
# ──────────────────────────────────────────

@admin_required
def admin_subscriptions_view(request):
    filter_by = request.GET.get('filter', 'pending')

    subscriptions = Subscription.objects.all().order_by('-created_at')

    if filter_by != 'all':
        subscriptions = subscriptions.filter(status=filter_by)

    return render(request, 'admin_panel/subscriptions.html', {
        'subscriptions': subscriptions,
        'filter_by':     filter_by,
    })


@admin_required
def admin_approve_subscription_view(request, sub_id):
    from datetime import timedelta
    sub = get_object_or_404(Subscription, id=sub_id)
    if request.method == 'POST':
        if sub.status == 'pending':
            days = Subscription.PLAN_DAYS.get(sub.plan, 30)
            sub.status     = 'active'
            sub.start_date = date.today()
            sub.end_date   = date.today() + timedelta(days=days)
            sub.save()

            create_notification(
                recipient=sub.user,
                sender=request.user,
                notif_type='new_match',
                message='💛 Your Gold subscription has been activated!',
                link='/my-subscription/',
            )

            messages.success(request,
                f'✅ Subscription approved for {sub.user.get_full_name()}! '
                f'Gold active until {sub.end_date}.')
        else:
            messages.warning(request,
                'This subscription is not in pending state.')

    return redirect('admin_subscriptions')


@admin_required
def admin_reject_subscription_view(request, sub_id):
    sub = get_object_or_404(Subscription, id=sub_id)
    if request.method == 'POST':
        if sub.status == 'pending':
            sub.status = 'rejected'
            sub.save()

            create_notification(
                recipient=sub.user,
                sender=request.user,
                notif_type='new_match',
                message='❌ Your payment could not be verified. '
                        'Please contact support.',
                link='/my-subscription/',
            )

            messages.success(request,
                f'Subscription rejected for {sub.user.get_full_name()}.')
        else:
            messages.warning(request,
                'This subscription is not in pending state.')

    return redirect('admin_subscriptions')