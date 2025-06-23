from django.urls import path

from management import views

urlpatterns = [
    # User authentication routes
    path("dashboard/", views.home, name="dashboard"),  # Changed from 'home/' to 'dashboard/' and name to 'dashboard'
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("add-user/", views.add_user, name="add_user"),
    path("my-profile/", views.my_profile, name="my_profile"),
    path("users/", views.user_list, name="user_list"),
    path("users/edit/<int:user_id>/", views.edit_user, name="edit_user"),
    path("users/delete/<int:user_id>/", views.delete_user, name="delete_user"),
    path("change-password/", views.change_password, name="change_password"),

    # Company Management URLs
    path("companies/", views.company_list_view, name="company_list"),
    path("companies/create/", views.company_create_view, name="company_create"),
    path("companies/<int:pk>/", views.company_detail_view, name="company_detail"),
    path("companies/<int:pk>/edit/", views.company_edit_view, name="company_edit"),
    path("companies/<int:pk>/delete/", views.company_delete_view, name="company_delete"),

    # Public landing page
    path("", views.public_landing_page, name="public_home"),
    # Session management routes
    path("sessions/", views.all_sessions_view, name="session_list"),
    path(
        "sessions/<int:session_id>/edit/", views.edit_session_view, name="edit_session"
    ),
    path(
        "sessions/<int:session_id>/delete/",
        views.delete_session_view,
        name="delete_session",
    ),
    # Topic management routes
    path("create-topic/", views.create_topic, name="create-topic"),
    path(
        "create-learning-topic/",
        views.create_external_topic,
        name="create-learning-topic",
    ),
    path("learning-view/", views.learning_view, name="learning-view"),
    path(
        "learning-view/<int:learning_id>/edit/",
        views.edit_learning,
        name="edit-learning",
    ),
    path(
        "learning-view/<int:learning_id>/delete/",
        views.delete_learning,
        name="delete-learning",
    ),
    path("recent-activities/", views.recent_activities, name="recent_activities"),
    path("departments/", views.department_list, name="department-list"),
    path("departments/create/", views.department_create, name="department-create"),
    path("departments/edit/<int:pk>/", views.department_edit, name="department-edit"),
    path(
        "departments/delete/<int:pk>/",
        views.department_delete,
        name="department-delete",
    ),
    path("export-sessions/", views.export_sessions, name="export-excel"),
    path("import-sessions/", views.upload_sessions_excel, name="import-sessions"),
]
