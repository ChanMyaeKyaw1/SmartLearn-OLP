from django.db import models
from django.contrib.auth.models import User

# ==========================================
# 1. CLASSES MODEL (Phase 1)
# ==========================================
class Classes(models.Model):
    CLASS_TYPES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]
    class_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_classes')
    title = models.CharField(max_length=255)
    description = models.TextField()
    class_type = models.CharField(max_length=20, choices=CLASS_TYPES, default='public')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# ==========================================
# Classroom, Payment, Enrollment)
# ==========================================

class Classroom(models.Model):
    SUBJECT_CHOICES = [
        ('math', 'Mathematics'),
        ('science', 'Science'),
        ('coding', 'Coding/IT'),
        ('languages', 'Languages'),
        ('arts', 'Arts & Design'),
    ]
    CLASS_TYPES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]
    class_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_classrooms', null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES, default='math')
    class_type = models.CharField(max_length=20, choices=CLASS_TYPES, default='public', null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    created_from_site = models.BooleanField(default=False)
    member_limit = models.IntegerField(null=True, blank=True, help_text="Maximum number of students allowed (leave blank for unlimited)")

    # for live-videocall
    is_live = models.BooleanField(default=False)


    def __str__(self):
        return self.title if self.title else "Unnamed Classroom"

    def get_member_count(self):
        """Get current number of approved members (including owner)"""
        return Enrollment.objects.filter(classroom=self, status='approved').count() + 1

    def has_capacity(self):
        """Check if class has room for more members"""
        if self.member_limit is None:
            return True
        return self.get_member_count() < self.member_limit
# Updated Enrollment model to track payslips & payment details
class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved / Active'),
        ('rejected', 'Rejected'),
    ]
    enrollment_id = models.AutoField(primary_key=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='enrollments', null=True, blank=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    phone = models.CharField(max_length=20, null=True, blank=True)
    payment_type = models.CharField(max_length=50, null=True, blank=True)
    payslip = models.ImageField(upload_to='payslips/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    rejection_reason = models.TextField(blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('classroom', 'student')

    def __str__(self):
        return f"{self.student.username} -> {self.classroom.title if self.classroom else 'No Classroom'} ({self.status})"


# ==========================================
# Flashcards, MCQs & Quiz Attempts
# ==========================================

class Flashcard(models.Model):
    flashcard_id = models.AutoField(primary_key=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='flashcards')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcards')
    topic = models.CharField(max_length=120)
    front = models.TextField()
    back = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} - {self.front[:40]}"


class FlashcardTopicReaction(models.Model):
    REACTION_TYPES = [
        ('like', 'Like'),
        ('save', 'Save'),
    ]

    topic_reaction_id = models.AutoField(primary_key=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='flashcard_topic_reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcard_topic_reactions')
    topic = models.CharField(max_length=120)
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('classroom', 'user', 'topic', 'reaction_type')

    def __str__(self):
        return f"{self.user.username} {self.reaction_type}d {self.topic}"


class MCQQuestion(models.Model):
    OPTION_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]
    question_id = models.AutoField(primary_key=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='mcq_questions')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mcq_questions')
    topic = models.CharField(max_length=120)
    question = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES)
    explanation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} - {self.question[:40]}"

    def option_text(self, option):
        return {
            'A': self.option_a,
            'B': self.option_b,
            'C': self.option_c,
            'D': self.option_d,
        }.get(option, '')


class QuizAttempt(models.Model):
    attempt_id = models.AutoField(primary_key=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='quiz_attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    answers = models.JSONField(default=dict)
    taken_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.classroom.title} ({self.score}/{self.total_questions})"


# Teacher Payment Accounts model (KPay, WavePay, etc.)
class PaymentAccount(models.Model):
    account_id = models.AutoField(primary_key=True)
    # 🟢 Add owner field linking to User
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_accounts', null=True, blank=True)
    payment_type = models.CharField(max_length=50)  # e.g. KPay, Wave Money
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.owner.username if self.owner else 'Admin'} - {self.payment_type} ({self.account_number})"

# ==========================================
# Teacher Materials & Resources model
# ==========================================

import os
from django.db import models
from django.contrib.auth.models import User
from .models import Classroom  # Adjust import based on your models layout

class TeacherMaterial(models.Model):
    CATEGORY_CHOICES = [
        ('lecture', 'Lecture Slides'),
        ('syllabus', 'Syllabus & Info'),
        ('assignment', 'Assignment / Worksheet'),
        ('reference', 'Reference Material'),
        ('video', 'Video / Audio Link'),
        ('other', 'Other Resource'),
    ]

    material_id = models.AutoField(primary_key=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='materials')
    uploader = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='lecture')

    # Storage options: Direct File OR External Link
    file = models.FileField(upload_to='teacher_materials/', blank=True, null=True)
    external_url = models.URLField(max_length=500, blank=True, null=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} - {self.classroom.title}"

    @property
    def extension(self):
        if self.file:
            name, ext = os.path.splitext(self.file.name)
            return ext.lower().replace('.', '')
        return 'link'

    @property
    def size_mb(self):
        if self.file and hasattr(self.file, 'size'):
            return round(self.file.size / (1024 * 1024), 2)
        return 0

# ==========================================
# Community Notes model for Classroom Discussions
# ==========================================

from django.db import models
from django.contrib.auth.models import User
from .models import Classroom

class CommunityNote(models.Model):
    note_id = models.AutoField(primary_key=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='community_notes')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    attachment = models.FileField(upload_to='community_notes/', blank=True, null=True)

    is_pinned = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    upvotes = models.ManyToManyField(User, related_name='upvoted_notes', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.classroom.title}"

    @property
    def total_upvotes(self):
        return self.upvotes.count()

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_image = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    expertise = models.CharField(max_length=255, blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    website_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
