from django.urls import path

from management import views

urlpatterns = [
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("add-user/", views.add_user, name="add_user"),
    path("my-profile/", views.my_profile, name="my_profile"),
    path("users/", views.user_list, name="user_list"),
    path("users/edit/<int:user_id>/", views.edit_user, name="edit_user"),
    path("change-password/", views.change_password, name="change_password"),
    path("", views.home, name="home"),
    path("sessions/", views.all_sessions_view, name="session_list"),
    path(
        "sessions/<int:session_id>/edit/", views.edit_session_view, name="edit_session"
    ),
    path(
        "sessions/<int:session_id>/delete/",
        views.delete_session_view,
        name="delete_session",
    ),
    path("create-topic/", views.create_topic, name="create-topic"),
    path(
        "create-learning-topic/",
        views.create_external_topic,
        name="create-learning-topic",
    ),
    path("learning-view/", views.learning_view, name="learning-view"),
]
