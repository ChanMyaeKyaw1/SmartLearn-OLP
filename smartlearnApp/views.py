from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .models import Classroom, CommunityNote, Enrollment, Flashcard, FlashcardTopicReaction, MCQQuestion, QuizAttempt, TeacherMaterial

from .models import PaymentAccount

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model


# ==========================================
# HELPER FUNCTIONS & ACCESS CONTROL
# ==========================================

def get_mock_user(request=None):
    """
    Unified helper to get or simulate the logged-in user.
    """
    if request and request.user.is_authenticated:
        return request.user

    username = "TestUser"
    if request:
        username = request.POST.get('user') or request.GET.get('user') or 'TestUser'

    user, created = User.objects.get_or_create(username=username)
    return user


def user_can_enter_classroom(classroom, user):
    if classroom.owner == user or classroom.class_type == 'public':
        return True

    return Enrollment.objects.filter(
        classroom=classroom,
        student=user,
        status='approved'
    ).exists()


def user_can_create_learning_content(classroom, user):
    if classroom.owner == user:
        return True

    return classroom.class_type == 'public'


def require_classroom_access(request, classroom):
    current_user = get_mock_user(request)
    if user_can_enter_classroom(classroom, current_user):
        return current_user, None

    messages.error(
        request,
        "You need approval from the class owner before entering this private classroom."
    )
    return current_user, redirect('browse_classes')


def get_accessible_classrooms(user):
    classrooms = Classroom.objects.select_related('owner').all().order_by('title')
    accessible = []

    for classroom in classrooms:
        if user_can_enter_classroom(classroom, user):
            accessible.append(classroom)

    return accessible


# ==========================================
# AUTHENTICATION & LANDING
# ==========================================

def home_view(request):
    total_classes = Classroom.objects.count()
    total_flashcards = Flashcard.objects.count()
    total_mcqs = MCQQuestion.objects.count()

    context = {
        'total_classes': total_classes,
        'total_flashcards': total_flashcards,
        'total_mcqs': total_mcqs,
    }
    return render(request, 'home.html', context)


# def login_view(request):
#     if request.user.is_authenticated:
#         return redirect('dashboard')
#     if request.method == 'POST':
#         user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
#         if user:
#             login(request, user, backend='django.contrib.auth.backends.ModelBackend')
#             return redirect('dashboard')
#     return render(request, 'login.html')

def login_view(request):
    # 1. Check if user specified a 'next' parameter in GET or POST
    next_url = request.GET.get('next') or request.POST.get('next')

    # 2. If already logged in, redirect to requested page or role dashboard
    if request.user.is_authenticated:
        if next_url:
            return redirect(next_url)
        if request.user.is_superuser or request.user.is_staff:
            return redirect('custom_admin_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            # 3. Superadmin/Staff override (takes priority or handles admin redirects)
            if user.is_superuser or user.is_staff:
                return redirect('custom_admin_dashboard')

            # 4. Regular users go to the 'next' URL if present, otherwise 'dashboard'
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'login.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "A user with that username already exists. Please choose a different one.")
            return render(request, 'register.html')

        # 1. Create the user
        user = User.objects.create_user(username=username, email=email, password=password)

        # 2. 🟢 Authenticate the user immediately
        # This automatically attaches user.backend = 'django.contrib.auth.backends.ModelBackend'
        authenticated_user = authenticate(request, username=username, password=password)

        if authenticated_user is not None:
            login(request, authenticated_user)

        messages.success(request, f"Welcome to SmartLearn, {user.username}!")
        return redirect('dashboard')

    return render(request, 'register.html')

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def view_profile(request):
    return render(request, 'view_profile.html')

# ==========================================
# DASHBOARD & CLASSROOM MANAGEMENT
# ==========================================

from django.db.models import Count, Q

@login_required(login_url='login')
def dashboard_view(request):
    # Annotate created classes with the pending requests count
    my_classes = Classroom.objects.filter(
        owner=request.user,
        created_from_site=True
    ).annotate(
        pending_count=Count('enrollments', filter=Q(enrollments__status='pending'))
    )

    total_teacher_pending = Enrollment.objects.filter(
        classroom__owner=request.user,
        status='pending'
    ).count()

    joined_classrooms = Classroom.objects.filter(
        enrollments__student=request.user,
        enrollments__status='approved'
    ).select_related('owner')

    pending_classrooms = Classroom.objects.filter(
        enrollments__student=request.user,
        enrollments__status='pending'
    ).select_related('owner')

    # 4. Classes available to explore:
    # Exclude: owned classes, approved joined classes, and pending classes
    available_classes = Classroom.objects.exclude(
        owner=request.user
    ).exclude(
        enrollments__student=request.user,
        enrollments__status__in=['approved', 'pending']
    ).select_related('owner').distinct()

    pending_class_ids = list(Enrollment.objects.filter(student=request.user, status='pending').values_list('classroom_id', flat=True))
    rejected_class_ids = list(Enrollment.objects.filter(student=request.user, status='rejected').values_list('classroom_id', flat=True))

    user_enrollments = {
        e.classroom_id: e for e in Enrollment.objects.filter(student=request.user)
    }

    for classroom in available_classes:
        classroom.user_enrollment = user_enrollments.get(classroom.class_id)

    # ==========================================
    # 2. CALCULATE QUIZ STATS FOR THE LOGGED-IN USER
    # ==========================================
    user_attempts = QuizAttempt.objects.filter(student=request.user)
    taken_quizzes_count = user_attempts.count()

    # Compute average score percentage across all attempts
    # Formula for percentage of an attempt: (score / total_questions) * 100
    if taken_quizzes_count > 0:
        total_percentage_sum = sum(
            (attempt.score / attempt.total_questions * 100)
            for attempt in user_attempts
            if attempt.total_questions > 0
        )
        avg_score = round(total_percentage_sum / taken_quizzes_count, 1)
    else:
        avg_score = 0
    return render(request, 'dashboard.html', {
        'my_classes': my_classes,
        'total_teacher_pending': total_teacher_pending,
        'joined_classrooms': joined_classrooms,
        'available_classes': available_classes,
        'pending_classrooms': pending_classrooms,
        'pending_class_ids': pending_class_ids,
        'rejected_class_ids': rejected_class_ids,
        'user_enrollments': user_enrollments,
        'taken_quizzes_count': taken_quizzes_count,
        'avg_score': avg_score,
    })


@login_required
def quiz_history(request):
    # Filter using 'student' and order using 'taken_at'
    attempts = QuizAttempt.objects.filter(student=request.user).order_by('-taken_at')
    
    context = {
        'attempts': attempts,
    }
    return render(request, 'quiz_history.html', context)


@login_required(login_url='login')
def edit_classroom(request, class_id):
    # Ensure only the class owner can edit
    classroom = get_object_or_404(Classroom, class_id=class_id, owner=request.user)

    if request.method == 'POST':
        title = request.POST.get('title')
        subject = request.POST.get('subject')
        description = request.POST.get('description')
        class_type = request.POST.get('class_type', 'public')
        price = request.POST.get('price', 0.00)

        if class_type == 'public':
            price = 0.00

        # Update model fields
        classroom.title = title
        classroom.subject = subject
        classroom.description = description if description else "No description provided."
        classroom.class_type = class_type
        classroom.price = price
        classroom.save()

        messages.success(request, "Classroom updated successfully!")
        return redirect('classroom_detail', class_id=classroom.class_id)

    return render(request, 'edit_classroom.html', {
        'classroom': classroom
    })

@login_required(login_url='login')
def my_classes(request):
    classes = Classroom.objects.filter(owner=request.user)

    return render(request, 'my_classes.html', {
        'classes': classes
    })


@login_required(login_url='login')  # Ensures current_user is authenticated
def browse_classes(request):
    current_user = request.user

    search_query = request.GET.get('search', '').strip()
    visibility = request.GET.get('visibility', '').strip()
    sorting = request.GET.get('sorting', '').strip()

    owned_classes = Classroom.objects.filter(owner=current_user).select_related('owner')

    # 1. Base Querysets
    joined_classes = Classroom.objects.filter(
        enrollments__student=current_user,
        enrollments__status='approved'
    ).select_related('owner').distinct()

    available_classes = Classroom.objects.exclude(
        owner=current_user
    ).exclude(
        enrollments__student=current_user,
        enrollments__status__in=['approved', 'pending']
    ).select_related('owner').distinct()

    # 2. Apply Search Filter (__icontains allows partial matching anywhere in the title)
    if search_query:
        joined_classes = joined_classes.filter(title__icontains=search_query)
        available_classes = available_classes.filter(title__icontains=search_query)

    # 3. Apply Visibility Filter
    if visibility == 'public':
        joined_classes = joined_classes.filter(class_type='public')
        available_classes = available_classes.filter(class_type='public')
    elif visibility == 'private':
        joined_classes = joined_classes.filter(class_type='private')
        available_classes = available_classes.filter(class_type='private')

    # 4. Apply Sorting
    if sorting == 'az':
        joined_classes = joined_classes.order_by('title')
        available_classes = available_classes.order_by('title')
    elif sorting == 'za':
        joined_classes = joined_classes.order_by('-title')
        available_classes = available_classes.order_by('-title')

    # 5. Query enrollment lists for IDs if needed
    user_enrollments = Enrollment.objects.filter(student=current_user)
    joined_class_ids = list(user_enrollments.filter(status='approved').values_list('classroom_id', flat=True))
    pending_class_ids = list(user_enrollments.filter(status='pending').values_list('classroom_id', flat=True))

    context = {
        'owned_classes': owned_classes,
        'joined_classes': joined_classes,
        'available_classes': available_classes,
        'search_query': search_query,
        'visibility': visibility,
        'sorting': sorting,
        'joined_class_ids': joined_class_ids,
        'pending_class_ids': pending_class_ids,
        'current_user_name': current_user.username,
    }
    return render(request, 'browserClass.html', context)

@login_required(login_url='login')
def create_class(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        subject = request.POST.get('subject')
        description = request.POST.get('description')
        class_type2 = request.POST.get('class_type', 'public')
        price = request.POST.get('price', 0.00)

        if class_type2 == 'public':
            price = 0.00

        Classroom.objects.create(
            title=title,
            subject=subject,
            description=description if description else "No description provided.",
            class_type=class_type2,
            price=price,
            owner=request.user,
            created_from_site=True
        )

        return redirect('dashboard')

    return render(request, 'createClass.html')


@login_required(login_url='login')
def delete_class(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)

    # Ensure only the actual owner can delete the classroom
    if classroom.owner == request.user:
        classroom.delete()
        messages.success(request, "Classroom deleted successfully.")
    else:
        messages.error(request, "You do not have permission to delete this class.")

    # Redirect safely back to dashboard or browse classes
    return redirect('dashboard')

def classroom_detail(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)
    current_user, blocked_response = require_classroom_access(request, classroom)
    if blocked_response:
        return blocked_response

    is_owner = (request.user.is_authenticated and classroom.owner == request.user)

    
    return render(
        request,
        "classroom_detail.html",
        {
            "classroom": classroom,
            "is_owner": is_owner,
            
        }
    )

def joined_students_list(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)
    
    # Ensure only the classroom owner/teacher can access
    if request.user != classroom.owner:
        return redirect('classroom_detail', class_id=class_id)

    joined_students = Enrollment.objects.filter(classroom=classroom, status='approved')

    return render(
        request,
        "joined_students.html",
        {
            "classroom": classroom,
            "joined_students": joined_students,
        }
    )

def serve_dashboard_page(request):
    user = get_mock_user(request)
    return render(request, 'dashboard.html', {
        'current_user_name': user.username
    })


# ==========================================
# ENROLLMENTS & PAYMENTS
# ==========================================

def request_join_class(request, class_id):
    current_user = get_mock_user(request)

    classroom = get_object_or_404(Classroom, class_id=class_id)

    # Prevent duplicate requests
    existing = Enrollment.objects.filter(
        student=current_user,
        classroom=classroom
    ).first()

    if not existing:
        Enrollment.objects.create(
            student=current_user,
            classroom=classroom,
            status='pending'
        )

    return redirect('browse_classes')


def manage_enrollments(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)
    current_user = get_mock_user(request)

    if classroom.owner != current_user:
        return redirect(f"/classes/browse/?user={current_user.username}")

    pending_requests = Enrollment.objects.filter(classroom=classroom, status='pending')
    active_students = Enrollment.objects.filter(classroom=classroom, status='approved')

    context = {
        'classroom': classroom,
        'pending_requests': pending_requests,
        'active_students': active_students,
        'current_user_name': current_user.username,
    }
    return render(request, 'manage_enrollments.html', context)


def update_enrollment_status(request, enrollment_id, action):
    enrollment = get_object_or_404(Enrollment, enrollment_id=enrollment_id)
    current_user = get_mock_user(request)

    if enrollment.classroom.owner == current_user:
        if action == 'approve':
            enrollment.status = 'approved'
            enrollment.save()
        elif action == 'reject':
            enrollment.status = 'rejected'
            enrollment.save()

    return redirect('manage_enrollments', class_id=enrollment.classroom.class_id)


@login_required(login_url='login')
def payment_upload_view(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)

    if request.method == 'POST':
        phone = request.POST.get('phone')
        payment_type = request.POST.get('payment_type')
        payslip = request.FILES.get('payslip')

        # Create pending enrollment request with payment details
        Enrollment.objects.create(
            student=request.user,
            classroom=classroom,
            phone=phone,
            payment_type=payment_type,
            payslip=payslip,
            status='pending'
        )

        messages.success(request, "Your payment slip has been uploaded successfully! Your enrollment status is now pending review.")
        return redirect('browse_classes')

    return render(request, 'payment_upload.html', {'classroom': classroom})


# ==========================================
# FLASHCARDS
# ==========================================

def flashcards_view(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)
    current_user, blocked_response = require_classroom_access(request, classroom)
    if blocked_response:
        return blocked_response

    can_create = user_can_create_learning_content(classroom, current_user)

    if request.method == 'POST':
        if not can_create:
            messages.error(request, "Only the private class owner can create flashcards for this classroom.")
            return redirect('flashcards', class_id=classroom.class_id)

        shared_topic = request.POST.get('topic', '').strip()
        fronts = request.POST.getlist('front') or [request.POST.get('front', '')]
        backs = request.POST.getlist('back') or [request.POST.get('back', '')]

        created_count = 0
        for front, back in zip(fronts, backs):
            front = front.strip()
            back = back.strip()

            if not shared_topic or not front or not back:
                continue

            Flashcard.objects.create(
                classroom=classroom,
                created_by=current_user,
                topic=shared_topic,
                front=front,
                back=back
            )
            created_count += 1

        if created_count:
            messages.success(request, f"Shared {created_count} flashcard{'s' if created_count != 1 else ''} with this classroom.")
            return redirect('flashcards', class_id=classroom.class_id)

        messages.error(request, "Please fill in the topic, front, and back for at least one flashcard.")

    flashcards = list(
        Flashcard.objects.filter(classroom=classroom)
        .select_related('created_by')
        .order_by('topic', '-created_at')
    )

    topic_groups = []
    topic_map = OrderedDict()

    for flashcard in flashcards:
        group = topic_map.get(flashcard.topic)
        if not group:
            group = {
                'topic': flashcard.topic,
                'topic_slug': slugify(flashcard.topic) or 'flashcard-topic',
                'cards': [],
                'contributors': [],
                'primary_creator': flashcard.created_by.username,
                'preview_front': flashcard.front,
                'preview_back': flashcard.back,
            }
            topic_map[flashcard.topic] = group
            topic_groups.append(group)

        group['cards'].append(flashcard)
        if flashcard.created_by.username not in group['contributors']:
            group['contributors'].append(flashcard.created_by.username)

    reaction_totals = FlashcardTopicReaction.objects.filter(classroom=classroom).values(
        'topic', 'reaction_type'
    ).annotate(total=Count('topic_reaction_id'))
    reaction_lookup = {
        (entry['topic'], entry['reaction_type']): entry['total']
        for entry in reaction_totals
    }
    current_reactions = set(
        FlashcardTopicReaction.objects.filter(classroom=classroom, user=current_user)
        .values_list('topic', 'reaction_type')
    )

    topic_groups_payload = []
    for group in topic_groups:
        contributor_count = len(group['contributors'])
        if contributor_count == 1:
            contributor_summary = group['contributors'][0]
        else:
            contributor_summary = f"{group['contributors'][0]} + {contributor_count - 1} more"

        group['total_cards'] = len(group['cards'])
        group['contributor_summary'] = contributor_summary
        group['like_count'] = reaction_lookup.get((group['topic'], 'like'), 0)
        group['save_count'] = reaction_lookup.get((group['topic'], 'save'), 0)
        group['user_liked'] = (group['topic'], 'like') in current_reactions
        group['user_saved'] = (group['topic'], 'save') in current_reactions

        topic_groups_payload.append({
            'topic': group['topic'],
            'topic_slug': group['topic_slug'],
            'total_cards': group['total_cards'],
            'primary_creator': group['primary_creator'],
            'contributor_summary': group['contributor_summary'],
            'like_count': group['like_count'],
            'save_count': group['save_count'],
            'user_liked': group['user_liked'],
            'user_saved': group['user_saved'],
            'cards': [
                {
                    'flashcard_id': card.flashcard_id,
                    'front': card.front,
                    'back': card.back,
                    'created_by': card.created_by.username,
                    'created_at': card.created_at.strftime('%b %d, %Y'),
                }
                for card in group['cards']
            ],
        })

    total_flashcards = len(flashcards)
    total_topics = len(topic_groups)

    return render(request, 'flashcards.html', {
        'classroom': classroom,
        'topic_groups': topic_groups,
        'topic_groups_payload': topic_groups_payload,
        'total_flashcards': total_flashcards,
        'total_topics': total_topics,
        'can_create': can_create,
        'current_user': current_user,
    })


def all_flashcards_view(request):
    current_user = request.user
    accessible_classrooms = Classroom.objects.filter(
        Q(class_type='public') | Q(owner=current_user) | Q(enrollments__student=current_user, enrollments__status='approved')
    ).distinct()
    flashcard_groups = []
    for classroom in accessible_classrooms:
        classroom_flashcards = list(
            Flashcard.objects.filter(classroom=classroom)
            .select_related('created_by')
            .order_by('topic', '-created_at')
        )

        classroom_topic_map = OrderedDict()
        for flashcard in classroom_flashcards:
            group_key = flashcard.topic
            group = classroom_topic_map.get(group_key)
            if not group:
                group = {
                    'classroom_id': classroom.class_id,
                    'classroom_title': classroom.title,
                    'class_type': classroom.class_type,
                    'topic': flashcard.topic,
                    'topic_slug': slugify(flashcard.topic) or 'flashcard-topic',
                    'modal_key': f'{classroom.class_id}-{slugify(flashcard.topic) or "flashcard-topic"}',
                    'cards': [],
                    'contributors': [],
                    'primary_creator': flashcard.created_by.username,
                    'preview_front': flashcard.front,
                }
                classroom_topic_map[group_key] = group

            group['cards'].append({
                'front': flashcard.front,
                'back': flashcard.back,
            })
            if flashcard.created_by.username not in group['contributors']:
                group['contributors'].append(flashcard.created_by.username)

        for group in classroom_topic_map.values():
            contributor_count = len(group['contributors'])
            if contributor_count == 1:
                contributor_summary = group['contributors'][0]
            else:
                contributor_summary = f"{group['contributors'][0]} + {contributor_count - 1} more"

            group['total_cards'] = len(group['cards'])
            group['contributor_summary'] = contributor_summary
            flashcard_groups.append(group)

    return render(request, 'all_flashcards.html', {
        'current_user': current_user,
        'flashcard_groups': flashcard_groups,
        'total_flashcards': sum(group['total_cards'] for group in flashcard_groups),
        'total_topics': len(flashcard_groups),
    })


def toggle_flashcard_topic_reaction(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)
    current_user, blocked_response = require_classroom_access(request, classroom)
    if blocked_response:
        return blocked_response

    if request.method != 'POST':
        return redirect('flashcards', class_id=classroom.class_id)

    topic = request.POST.get('topic', '').strip()
    reaction_type = request.POST.get('reaction_type', '').strip()

    if not topic or reaction_type not in {'like', 'save'}:
        messages.error(request, 'Please choose a valid topic reaction.')
        return redirect('flashcards', class_id=classroom.class_id)

    reaction = FlashcardTopicReaction.objects.filter(
        classroom=classroom,
        user=current_user,
        topic=topic,
        reaction_type=reaction_type,
    ).first()

    if reaction:
        reaction.delete()
        messages.info(request, f'Removed your {reaction_type} from {topic}.')
    else:
        FlashcardTopicReaction.objects.create(
            classroom=classroom,
            user=current_user,
            topic=topic,
            reaction_type=reaction_type,
        )
        messages.success(request, f'{reaction_type.title()}d {topic}.')

    return redirect('flashcards', class_id=classroom.class_id)


# ==========================================
# MCQS & QUIZZES
# ==========================================

def mcqs_view(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)
    current_user, blocked_response = require_classroom_access(request, classroom)
    if blocked_response:
        return blocked_response

    can_create = user_can_create_learning_content(classroom, current_user)

    if request.method == 'POST':
        if not can_create:
            messages.error(request, "Only the private class owner can create MCQs for this classroom.")
            return redirect('mcqs', class_id=classroom.class_id)

        shared_topic = request.POST.get('topic', '').strip()
        questions = request.POST.getlist('question') or [request.POST.get('question', '')]
        option_a_list = request.POST.getlist('option_a') or [request.POST.get('option_a', '')]
        option_b_list = request.POST.getlist('option_b') or [request.POST.get('option_b', '')]
        option_c_list = request.POST.getlist('option_c') or [request.POST.get('option_c', '')]
        option_d_list = request.POST.getlist('option_d') or [request.POST.get('option_d', '')]
        correct_options = request.POST.getlist('correct_option') or [request.POST.get('correct_option', '')]
        explanations = request.POST.getlist('explanation') or [request.POST.get('explanation', '')]

        created_count = 0
        for question, option_a, option_b, option_c, option_d, correct_option, explanation in zip(
            questions,
            option_a_list,
            option_b_list,
            option_c_list,
            option_d_list,
            correct_options,
            explanations,
        ):
            question = question.strip()
            option_a = option_a.strip()
            option_b = option_b.strip()
            option_c = option_c.strip()
            option_d = option_d.strip()
            correct_option = correct_option.strip()
            explanation = explanation.strip()

            if not shared_topic or not question or not option_a or not option_b or not option_c or not option_d or not correct_option:
                continue

            MCQQuestion.objects.create(
                classroom=classroom,
                created_by=current_user,
                topic=shared_topic,
                question=question,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                correct_option=correct_option,
                explanation=explanation
            )
            created_count += 1

        if created_count:
            messages.success(request, f"Shared {created_count} MCQ{'s' if created_count != 1 else ''} with this classroom.")
            return redirect('mcqs', class_id=classroom.class_id)

        messages.error(request, "Please complete the topic, question, options, and correct answer for at least one MCQ.")

    questions = list(
        MCQQuestion.objects.filter(classroom=classroom)
        .select_related('created_by')
        .order_by('topic', '-created_at')
    )

    topic_groups = []
    topic_map = OrderedDict()

    for question_item in questions:
        group = topic_map.get(question_item.topic)
        if not group:
            group = {
                'topic': question_item.topic,
                'topic_slug': slugify(question_item.topic) or 'mcq-topic',
                'questions': [],
                'contributors': [],
                'primary_creator': question_item.created_by.username,
                'preview_question': question_item.question,
            }
            topic_map[question_item.topic] = group
            topic_groups.append(group)

        group['questions'].append(question_item)
        if question_item.created_by.username not in group['contributors']:
            group['contributors'].append(question_item.created_by.username)

    topic_groups_payload = []
    for group in topic_groups:
        contributor_count = len(group['contributors'])
        if contributor_count == 1:
            contributor_summary = group['contributors'][0]
        else:
            contributor_summary = f"{group['contributors'][0]} + {contributor_count - 1} more"

        topic_groups_payload.append({
            'topic': group['topic'],
            'topic_slug': group['topic_slug'],
            'total_questions': len(group['questions']),
            'primary_creator': group['primary_creator'],
            'contributor_summary': contributor_summary,
            'preview_question': group['preview_question'],
        })

    total_questions = len(questions)
    total_topics = len(topic_groups)

    return render(request, 'mcqs.html', {
        'classroom': classroom,
        'topic_groups': topic_groups,
        'topic_groups_payload': topic_groups_payload,
        'total_questions': total_questions,
        'total_topics': total_topics,
        'can_create': can_create,
        'current_user': current_user,
    })


def all_mcqs_view(request):
    current_user = request.user
    accessible_classrooms = get_accessible_classrooms(current_user)
    can_create = request.user.is_authenticated

    mcq_groups = []
    for classroom in accessible_classrooms:
        classroom_questions = list(
            MCQQuestion.objects.filter(classroom=classroom)
            .select_related('created_by')
            .order_by('topic', '-created_at')
        )

        classroom_topic_map = OrderedDict()
        for question_item in classroom_questions:
            group_key = question_item.topic
            group = classroom_topic_map.get(group_key)
            if not group:
                group = {
                    'classroom_id': classroom.class_id,
                    'classroom_title': classroom.title,
                    'class_type': classroom.class_type,
                    'topic': question_item.topic,
                    'topic_slug': slugify(question_item.topic) or 'mcq-topic',
                    'preview_question': question_item.question,
                    'questions': [],
                    'contributors': [],
                    'primary_creator': question_item.created_by.username,
                }
                classroom_topic_map[group_key] = group

            group['questions'].append(question_item)
            if question_item.created_by.username not in group['contributors']:
                group['contributors'].append(question_item.created_by.username)

        for group in classroom_topic_map.values():
            contributor_count = len(group['contributors'])
            if contributor_count == 1:
                contributor_summary = group['contributors'][0]
            else:
                contributor_summary = f"{group['contributors'][0]} + {contributor_count - 1} more"

            group['total_questions'] = len(group['questions'])
            group['contributor_summary'] = contributor_summary
            mcq_groups.append(group)

    return render(request, 'all_mcqs.html', {
        'current_user': current_user,
        'mcq_groups': mcq_groups,
        'total_questions': sum(group['total_questions'] for group in mcq_groups),
        'total_topics': len(mcq_groups),
        'can_create': can_create,
    })


def take_quiz_view(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)
    current_user, blocked_response = require_classroom_access(request, classroom)
    if blocked_response:
        return blocked_response

    selected_topic = request.GET.get('topic', '').strip()
    questions = MCQQuestion.objects.filter(classroom=classroom).select_related('created_by').order_by('topic', 'question_id')

    if selected_topic:
        questions = questions.filter(topic=selected_topic)

    questions = list(questions)

    return render(request, 'take_mcq_quiz.html', {
        'classroom': classroom,
        'questions': questions,
        'selected_topic': selected_topic,
        'question_count': len(questions),
        'current_user': current_user,
    })


def submit_quiz(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)
    current_user, blocked_response = require_classroom_access(request, classroom)
    if blocked_response:
        return blocked_response

    if request.method != 'POST':
        return redirect('mcqs', class_id=classroom.class_id)

    selected_topic = request.POST.get('topic', '').strip()
    questions = MCQQuestion.objects.filter(classroom=classroom).order_by('topic', 'question_id')
    if selected_topic:
        questions = questions.filter(topic=selected_topic)

    answers = {}
    score = 0

    for question in questions:
        selected = request.POST.get(f'question_{question.question_id}', '')
        is_correct = selected == question.correct_option
        if is_correct:
            score += 1

        answers[str(question.question_id)] = {
            'selected': selected,
            'correct': question.correct_option,
            'is_correct': is_correct,
        }

    attempt = QuizAttempt.objects.create(
        classroom=classroom,
        student=current_user,
        score=score,
        total_questions=questions.count(),
        answers=answers
    )

    return redirect('quiz_result', attempt_id=attempt.attempt_id)


def my_results_view(request):
    current_user = get_mock_user(request)
    attempts = QuizAttempt.objects.filter(student=current_user).select_related('classroom').order_by('-taken_at')

    return render(request, 'my_results.html', {
        'attempts': attempts,
        'current_user': current_user,
    })


def quiz_result(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related('classroom', 'student'),
        attempt_id=attempt_id
    )
    current_user, blocked_response = require_classroom_access(request, attempt.classroom)
    if blocked_response:
        return blocked_response

    if attempt.student != current_user and attempt.classroom.owner != current_user:
        messages.error(request, "You can only view your own quiz result.")
        return redirect('mcqs', class_id=attempt.classroom.class_id)

    questions = MCQQuestion.objects.filter(classroom=attempt.classroom).order_by('topic', 'question_id')
    reviewed_questions = []

    for question in questions:
        answer = attempt.answers.get(str(question.question_id), {})
        selected = answer.get('selected', '')
        reviewed_questions.append({
            'question': question,
            'selected': selected,
            'selected_text': question.option_text(selected),
            'correct_text': question.option_text(question.correct_option),
            'is_correct': answer.get('is_correct', False),
        })

    percentage = round((attempt.score / attempt.total_questions) * 100) if attempt.total_questions else 0

    return render(request, 'quiz_result.html', {
        'attempt': attempt,
        'classroom': attempt.classroom,
        'reviewed_questions': reviewed_questions,
        'percentage': percentage,
    })


@login_required(login_url='login')
def teacher_student_results(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)

    if classroom.owner != request.user:
        messages.error(request, "Only the class instructor can access student quiz scores.")
        return redirect('classroom_detail', class_id=classroom.class_id)

    attempts = QuizAttempt.objects.filter(classroom=classroom).select_related('student').order_by('-taken_at')

    return render(request, 'teacher_student_results.html', {
        'classroom': classroom,
        'attempts': attempts
    })





@login_required(login_url='login')
def payment_upload_view(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)

    # 🟢 Fetch the payment accounts created by the owner (teacher) of this classroom
    payment_accounts = PaymentAccount.objects.filter(owner=classroom.owner)

    if request.method == 'POST':
        phone = request.POST.get('phone')
        payment_type = request.POST.get('payment_type')
        payslip = request.FILES.get('payslip')

        # Record pending enrollment
        Enrollment.objects.update_or_create(
            student=request.user,
            classroom=classroom,
            defaults={
                'phone': phone,
                'payment_type': payment_type,
                'payslip': payslip,
                'status': 'pending',
            }
        )

        messages.success(request, "Your payment slip has been uploaded successfully! Your request is pending review.")
        return redirect('browse_classes')

    return render(request, 'payment_upload.html', {
        'classroom': classroom,
        'payment_accounts': payment_accounts,  # 🟢 Pass to template
    })

@login_required(login_url='login')
def manage_payment_accounts(request):
    if request.method == 'POST':
        payment_type = request.POST.get('payment_type')
        account_name = request.POST.get('account_name')
        account_number = request.POST.get('account_number')

        if payment_type and account_name and account_number:
            PaymentAccount.objects.create(
                owner=request.user,
                payment_type=payment_type,
                account_name=account_name,
                account_number=account_number
            )
            messages.success(request, "Payment method added successfully!")
            return redirect('manage_payment_accounts')

    accounts = PaymentAccount.objects.filter(owner=request.user)
    return render(request, 'manage_payment_accounts.html', {'accounts': accounts})

@login_required(login_url='login')
def delete_payment_account(request, account_id):
    account = get_object_or_404(PaymentAccount, account_id=account_id, owner=request.user)
    account.delete()
    messages.success(request, "Payment method removed successfully.")
    return redirect('manage_payment_accounts')

from django.db.models import Q

# @login_required
# def create_topic_global(request, item_type):

#     if request.method == 'POST':
#         class_mode = request.POST.get('class_mode')
#         topic = request.POST.get('topic')

#     # Route to manage global creation of topics/items across classes
#     accessible_classrooms = get_accessible_classrooms(request.user)
#     return render(request, 'create_topic.html', {
#         'item_type': item_type,
#         'classrooms': accessible_classrooms
#     })


#         # 1. Resolve Classroom
#         if class_mode == 'new':
#             new_title = request.POST.get('new_class_title')
#             classroom = Classroom.objects.create(
#                 title=new_title,
#                 owner=request.user,
#                 class_type='public'
#             )
#         else:
#             classroom_id = request.POST.get('classroom_id')
#             classroom = get_object_or_404(Classroom, class_id=classroom_id)

#         # 2. Save Flashcards
#     if item_type == 'flashcards':
#             fronts = request.POST.getlist('front')
#             backs = request.POST.getlist('back')

#             for front, back in zip(fronts, backs):
#                 if front.strip() and back.strip():
#                     Flashcard.objects.create(
#                         classroom=classroom,
#                         topic=topic,
#                         front=front,
#                         back=back,
#                         created_by=request.user
#                     )
#             return redirect('all_flashcards')

#         # 3. Save MCQs
#     elif item_type == 'mcqs':
#             questions = request.POST.getlist('question')
#             opts_a = request.POST.getlist('option_a')
#             opts_b = request.POST.getlist('option_b')
#             opts_c = request.POST.getlist('option_c')
#             opts_d = request.POST.getlist('option_d')
#             corrects = request.POST.getlist('correct_option')
#             explanations = request.POST.getlist('explanation')

#             for i in range(len(questions)):
#                 if questions[i].strip():
#                     MCQQuestion.objects.create(
#                         classroom=classroom,
#                         topic=topic,
#                         question=questions[i],
#                         option_a=opts_a[i],
#                         option_b=opts_b[i],
#                         option_c=opts_c[i],
#                         option_d=opts_d[i],
#                         correct_option=corrects[i],
#                         explanation=explanations[i] if i < len(explanations) else '',
#                         created_by=request.user
#                     )
#             return redirect('all_mcqs')

#     # GET Request: Fetch owned vs public classes separately or mark them
#     all_classes = Classroom.objects.filter(
#         Q(class_type='public') | Q(owner=request.user)
#     ).distinct()

#     context = {
#         'item_type': item_type,
#         'classrooms': all_classes,
#     }
#     return render(request, 'create_topic.html', context)


@login_required
def create_topic_global(request, item_type):
    if request.method == 'POST':
        class_mode = request.POST.get('class_mode')
        topic = request.POST.get('topic')

        # 1. Resolve Classroom
        if class_mode == 'new':
            new_title = request.POST.get('new_class_title')
            classroom = Classroom.objects.create(
                title=new_title,
                owner=request.user,
                class_type='public'
            )
        else:
            classroom_id = request.POST.get('classroom_id')
            classroom = get_object_or_404(Classroom, class_id=classroom_id)

        # 2. Save Flashcards
        if item_type == 'flashcards':
            fronts = request.POST.getlist('front')
            backs = request.POST.getlist('back')

            for front, back in zip(fronts, backs):
                if front.strip() and back.strip():
                    Flashcard.objects.create(
                        classroom=classroom,
                        topic=topic,
                        front=front,
                        back=back,
                        created_by=request.user
                    )
            return redirect('all_flashcards')

        # 3. Save MCQs
        elif item_type == 'mcqs':
            questions = request.POST.getlist('question')
            opts_a = request.POST.getlist('option_a')
            opts_b = request.POST.getlist('option_b')
            opts_c = request.POST.getlist('option_c')
            opts_d = request.POST.getlist('option_d')
            corrects = request.POST.getlist('correct_option')
            explanations = request.POST.getlist('explanation')

            for i in range(len(questions)):
                if questions[i].strip():
                    MCQQuestion.objects.create(
                        classroom=classroom,
                        topic=topic,
                        question=questions[i],
                        option_a=opts_a[i],
                        option_b=opts_b[i],
                        option_c=opts_c[i],
                        option_d=opts_d[i],
                        correct_option=corrects[i],
                        explanation=explanations[i] if i < len(explanations) else '',
                        created_by=request.user
                    )
            return redirect('all_mcqs')

    # GET Request
    all_classes = Classroom.objects.filter(
        Q(class_type='public') | Q(owner=request.user)
    ).distinct()

    return render(request, 'create_topic.html', {
        'item_type': item_type,
        'classrooms': all_classes,
    })


@login_required(login_url='login')
def manage_classroom_view(request, class_id):
    # Ensure only the owner can manage this class
    classroom = get_object_or_404(Classroom, class_id=class_id, owner=request.user)

    # Get all pending enrollment requests for this classroom
    pending_enrollments = Enrollment.objects.filter(
        classroom=classroom,
        status='pending'
    ).select_related('student')

    # Get approved students list (roster)
    approved_enrollments = Enrollment.objects.filter(
        classroom=classroom,
        status='approved'
    ).select_related('student')

    return render(request, 'manage_classroom.html', {
        'classroom': classroom,
        'pending_enrollments': pending_enrollments,
        'approved_enrollments': approved_enrollments,
    })


@login_required(login_url='login')
def handle_enrollment_request(request, enrollment_id, action):
    # Fix: Use 'enrollment_id' instead of 'id'
    enrollment = get_object_or_404(Enrollment, enrollment_id=enrollment_id, classroom__owner=request.user)

    if action == 'approve':
        enrollment.status = 'approved'
        enrollment.rejection_reason = None  # Clear reason on approval
        enrollment.save()
        messages.success(request, f"Approved {enrollment.student.username}'s request.")

    elif action == 'reject':
        # Grab the reason sent from JavaScript query parameter
        reason = request.GET.get('rejection_reason', '').strip()

        enrollment.status = 'rejected'
        enrollment.rejection_reason = reason if reason else "No reason provided."
        enrollment.save()
        messages.warning(request, f"Rejected {enrollment.student.username}'s request.")

    return redirect('manage_enrollments', class_id=enrollment.classroom.class_id)



# (Note: If you want to redirect them to Django's built-in default admin page instead of a custom-built one, simply replace return redirect('custom_admin_dashboard') with return redirect('/admin/')).

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required(login_url='login')
def custom_admin_dashboard(request):
    # Fetch data you want to display on the admin page
    total_users = User.objects.count()
    total_classrooms = Classroom.objects.count()

    context = {
        'total_users': total_users,
        'total_classrooms': total_classrooms,
    }
    return render(request, 'custom_admin/dashboard.html', context)




User = get_user_model()

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def custom_admin_dashboard(request):
    section = request.GET.get('section', 'all')

    context = {
        'section': section,
        'total_users': User.objects.count(),
        'total_classrooms': Classroom.objects.count(),
        'total_flashcards': Flashcard.objects.count(),
        'total_mcqs': MCQQuestion.objects.count(),
        'users': User.objects.all(),
        'classrooms': Classroom.objects.all(),
        'flashcards': Flashcard.objects.all(),
        'mcqs': MCQQuestion.objects.all(),
    }
    return render(request, 'custom_admin/dashboard.html', context)

@staff_member_required(login_url='login')
def admin_edit_user(request, user_id):
    target_user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        target_user.username = request.POST.get('username', '').strip()
        target_user.email = request.POST.get('email', '').strip()
        target_user.is_staff = 'is_staff' in request.POST
        target_user.is_active = 'is_active' in request.POST
        target_user.save()
        messages.success(request, f"User {target_user.username} updated successfully!")
        return redirect('custom_admin_dashboard')

    return render(request, 'custom_admin/edit_user.html', {'target_user': target_user})


@staff_member_required(login_url='login')
def admin_delete_user(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot delete your own admin account!")
    else:
        target_user.delete()
        messages.success(request, "User deleted successfully.")
    return redirect('custom_admin_dashboard')

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def admin_view_profile(request):
    return render(request, 'custom_admin/view_profile.html')

@staff_member_required(login_url='login')
def admin_update_profile(request):
    if request.method == 'POST':
        request.user.username = request.POST.get('username', '').strip()
        request.user.email = request.POST.get('email', '').strip()
        request.user.save()
        messages.success(request, "Admin profile updated successfully!")
        return redirect('admin_update_profile')

    return render(request, 'custom_admin/edit_profile.html')

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def admin_change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        # 1. Verify old password using Django's check_password method
        if not request.user.check_password(old_password):
            messages.error(request, "Incorrect old password.")
            return render(request, 'custom_admin/change_password.html')

        # 2. Check if new passwords match
        if new_password1 != new_password2:
            messages.error(request, "New passwords do not match.")
            return render(request, 'custom_admin/change_password.html')

        # 3. Save new password and update session so admin stays logged in
        request.user.set_password(new_password1)
        request.user.save()
        update_session_auth_hash(request, request.user)  # Prevents logging out

        messages.success(request, "Your password has been changed successfully!")
        return redirect('admin_view_profile')

    return render(request, 'custom_admin/change_password.html')





@login_required
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)

        if 'image' in request.FILES:
            user.profile_image = request.FILES['image']

        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('edit_profile')

    return render(request, 'edit_profile.html')


@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        if not request.user.check_password(old_password):
            messages.error(request, "Incorrect old password.")
            return render(request, 'change_password.html')

        if new_password1 != new_password2:
            messages.error(request, "New passwords do not match.")
            return render(request, 'change_password.html')

        request.user.set_password(new_password1)
        request.user.save()
        update_session_auth_hash(request, request.user)

        messages.success(request, "Your password has been changed successfully!")
        return redirect('edit_profile')

    return render(request, 'change_password.html')

@login_required
def teacher_materials_view(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)

    # Verify access permission
    current_user, blocked_response = require_classroom_access(request, classroom)
    if blocked_response:
        return blocked_response

    is_owner = (classroom.owner == request.user)

    # Filter search and category
    search_query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()

    materials = TeacherMaterial.objects.filter(classroom=classroom)

    # Non-owners only see published materials
    if not is_owner:
        materials = materials.filter(is_visible=True)

    if search_query:
        materials = materials.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    if selected_category:
        materials = materials.filter(category=selected_category)

    context = {
        'classroom': classroom,
        'materials': materials,
        'is_owner': is_owner,
        'search_query': search_query,
        'selected_category': selected_category,
        'categories': TeacherMaterial.CATEGORY_CHOICES,
    }
    return render(request, 'teacher_materials.html', context)


@login_required
def upload_material(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)

    if classroom.owner != request.user:
        messages.error(request, "Only the course teacher can upload materials.")
        return redirect('teacher_materials', class_id=classroom.class_id)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', 'lecture')
        external_url = request.POST.get('external_url', '').strip()
        file_obj = request.FILES.get('file')

        if not title:
            messages.error(request, "Material title is required.")
            return redirect('teacher_materials', class_id=classroom.class_id)

        if not file_obj and not external_url:
            messages.error(request, "Please attach a file or provide an external URL.")
            return redirect('teacher_materials', class_id=classroom.class_id)

        TeacherMaterial.objects.create(
            classroom=classroom,
            uploader=request.user,
            title=title,
            description=description,
            category=category,
            file=file_obj if file_obj else None,
            external_url=external_url if external_url else None
        )
        messages.success(request, f"'{title}' uploaded successfully!")

    return redirect('teacher_materials', class_id=classroom.class_id)


@login_required
def delete_material(request, material_id):
    material = get_object_or_404(TeacherMaterial, material_id=material_id)
    class_id = material.classroom.class_id

    if material.classroom.owner != request.user:
        messages.error(request, "Permission denied.")
        return redirect('teacher_materials', class_id=class_id)

    if request.method == 'POST':
        material.delete()
        messages.success(request, "Material deleted successfully.")

    return redirect('teacher_materials', class_id=class_id)

@login_required
def edit_material(request, material_id):
    material = get_object_or_404(TeacherMaterial, material_id=material_id)
    class_id = material.classroom.class_id

    # Ensure only the classroom owner can edit
    if material.classroom.owner != request.user:
        messages.error(request, "Permission denied.")
        return redirect('teacher_materials', class_id=class_id)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', material.category)
        external_url = request.POST.get('external_url', '').strip()
        file_obj = request.FILES.get('file')

        if not title:
            messages.error(request, "Material title is required.")
            return redirect('teacher_materials', class_id=class_id)

        material.title = title
        material.description = description
        material.category = category
        material.external_url = external_url if external_url else None

        # Replace existing file if a new file is uploaded
        if file_obj:
            material.file = file_obj

        material.save()
        messages.success(request, f"'{title}' updated successfully!")

    return redirect('teacher_materials', class_id=class_id)


@login_required
def community_notes_view(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)
    is_owner = (classroom.owner == request.user)

    search_query = request.GET.get('q', '').strip()
    filter_type = request.GET.get('filter', '')

    notes = CommunityNote.objects.filter(classroom=classroom)

    if search_query:
        notes = notes.filter(title__icontains=search_query) | notes.filter(content__icontains=search_query)

    if filter_type == 'verified':
        notes = notes.filter(is_verified=True)
    elif filter_type == 'pinned':
        notes = notes.filter(is_pinned=True)

    context = {
        'classroom': classroom,
        'notes': notes,
        'is_owner': is_owner,
        'search_query': search_query,
        'filter_type': filter_type,
    }
    return render(request, 'community_notes.html', context)


@login_required
def create_community_note(request, class_id):
    classroom = get_object_or_404(Classroom, class_id=class_id)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        attachment = request.FILES.get('attachment')

        if title and content:
            CommunityNote.objects.create(
                classroom=classroom,
                author=request.user,
                title=title,
                content=content,
                attachment=attachment
            )
            messages.success(request, "Note shared with the community!")
        else:
            messages.error(request, "Title and content are required.")

    return redirect('community_notes', class_id=classroom.class_id)


@login_required
def toggle_upvote_note(request, note_id):
    note = get_object_or_404(CommunityNote, note_id=note_id)
    if request.user in note.upvotes.all():
        note.upvotes.remove(request.user)
    else:
        note.upvotes.add(request.user)
    return redirect('community_notes', class_id=note.classroom.class_id)


@login_required
def toggle_verify_note(request, note_id):
    note = get_object_or_404(CommunityNote, note_id=note_id)
    if note.classroom.owner == request.user:
        note.is_verified = not note.is_verified
        note.save()
        messages.success(request, "Verification status updated.")
    return redirect('community_notes', class_id=note.classroom.class_id)


@login_required
def toggle_pin_note(request, note_id):
    note = get_object_or_404(CommunityNote, note_id=note_id)
    if note.classroom.owner == request.user:
        note.is_pinned = not note.is_pinned
        note.save()
        messages.success(request, "Pin status updated.")
    return redirect('community_notes', class_id=note.classroom.class_id)


import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def chatbot_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            msg = data.get("message", "").strip().lower()

            # 1. Greetings
            if any(k in msg for k in ["hi", "hello", "hey", "start", "greetings", "bot", "ai"]):
                reply = (
                    "Hello! Welcome to SmartLearn Assistant. "
                    "I can help you with Classes, Flashcards, MCQs, Theme settings, Profile details, or Teacher Mode. "
                    "What would you like to explore?"
                )

            # 2. Account & Authentication
            elif any(k in msg for k in ["account", "signup", "sign up", "login", "log in", "password", "register"]):
                reply = (
                    "Account Help: You can log in or register using the buttons at the top right of the navigation bar. "
                    "If you forgot your password, click Forgot Password on the sign-in screen to reset it."
                )

            # 3. Classes & Courses
            elif any(k in msg for k in ["class", "classes", "course", "courses", "lecture", "study"]):
                reply = (
                    "Classes: Access your video lectures, study materials, and track your learning progress directly from your Dashboard or the Classes tab."
                )

            # 4. Flashcards
            elif any(k in msg for k in ["flashcard", "flashcards", "card", "deck", "memorize"]):
                reply = (
                    "Flashcards: Practice active recall with our flashcard decks. You can study existing subject decks or build your own custom sets from your dashboard."
                )

            # 5. MCQs & Quizzes
            elif any(k in msg for k in ["mcq", "mcqs", "quiz", "quizzes", "test", "practice"]):
                reply = (
                    "MCQs & Quizzes: Test your knowledge with multiple-choice quizzes. Visit the MCQs section to take practice tests and get instant feedback."
                )

            # 6. Theme Settings (Dark/Light Mode)
            elif any(k in msg for k in ["theme", "dark mode", "light mode", "color", "appearance"]):
                reply = (
                    "Theme Settings: Click the sun/moon icon in the top navigation bar to toggle between Light Mode and Dark Mode whenever you like."
                )

            # 7. User Profile
            elif any(k in msg for k in ["profile", "avatar", "username", "bio", "details", "settings"]):
                reply = (
                    "Profile Settings: Click your profile icon at the top right to update your personal details, avatar, and password preferences."
                )

            # 8. Teacher Mode (Updated)
            elif any(k in msg for k in ["teacher", "teacher mode", "educator", "instructor", "create course", "payment"]):
                reply = (
                    "Teacher Mode: Toggle Teacher Mode using the switch in the top bar. "
                    "When enabled, it reveals the Payment Methods option in your profile dropdown, allowing you to manage educator payment accounts."
                )

            # 9. Support & Contact
            elif any(k in msg for k in ["help", "support", "contact", "email", "issue", "bug"]):
                reply = (
                    "Support: Need extra assistance? Contact our support team anytime at support@smartlearn.com."
                )

            # Default Fallback
            else:
                reply = (
                    "I am here to help! You can ask me about Accounts, Classes, Flashcards, MCQs, Theme settings, Profile, or Teacher Mode."
                )

            return JsonResponse({"reply": reply})

        except Exception as e:
            return JsonResponse({"reply": f"Error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)