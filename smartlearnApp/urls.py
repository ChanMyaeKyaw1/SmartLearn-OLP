from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),              # Changed views.home to views.home_view
    path('login/', views.login_view, name='login'),      # Ensure this matches views.login_view
    path('register/', views.register_view, name='register'),  # Ensure this matches views.register_view
    path('dashboard/', views.dashboard_view, name='dashboard'), # Ensure this matches views.dashboard_view
    path('my-classes/', views.my_classes, name='my_classes'),
    path('logout/', views.logout_view, name='logout'),    # Ensure this matches views.logout_view
    # path('home/', views.home_view, name='home'),  # Ensure this matches views.logout_view

    path('browse/', views.browse_classes, name='browse_classes'),
    path('create/', views.create_class, name='create_class'),
    path('delete/<int:class_id>/', views.delete_class, name='delete_class'),
    path('join-request/<int:class_id>/', views.request_join_class, name='request_join_class'),
    # path('dashboard.html', views.serve_dashboard_page, name='dashboard_page'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),    # Teacher features
    path('manage/<int:class_id>/', views.manage_enrollments, name='manage_enrollments'),
    path('enrollment-decision/<int:enrollment_id>/<str:action>/', views.update_enrollment_status, name='update_enrollment_status'),
    path('classroom/<int:class_id>/',views.classroom_detail,name='classroom_detail'),
    path('classroom/<int:class_id>/flashcards/', views.flashcards_view, name='flashcards'),
    path('classroom/<int:class_id>/flashcards/react/', views.toggle_flashcard_topic_reaction, name='toggle_flashcard_topic_reaction'),
    path('classroom/<int:class_id>/mcqs/', views.mcqs_view, name='mcqs'),
    path('classroom/<int:class_id>/mcqs/take/', views.take_quiz_view, name='take_quiz'),
    path('classroom/<int:class_id>/mcqs/submit/', views.submit_quiz, name='submit_quiz'),
    path('quiz-result/<int:attempt_id>/', views.quiz_result, name='quiz_result'),
    path('my-results/', views.my_results_view, name='my_results'),
    path('flashcards/', views.all_flashcards_view, name='all_flashcards'),
    path('mcqs/', views.all_mcqs_view, name='all_mcqs'),
    path('classroom/<int:class_id>/student-results/', views.teacher_student_results, name='teacher_student_results'),

    path('classes/<int:class_id>/payment/', views.payment_upload_view, name='payment_upload'),

    path('payments/manage/', views.manage_payment_accounts, name='manage_payment_accounts'),
    path('payments/delete/<int:account_id>/', views.delete_payment_account, name='delete_payment_account'),
    path('create/<str:item_type>/', views.create_topic_global, name='create_topic_global'),
    path('classroom/<str:class_id>/manage/', views.manage_classroom_view, name='manage_classroom'),
    path('enrollment/<int:enrollment_id>/<str:action>/', views.handle_enrollment_request, name='handle_enrollment_request'),

]


