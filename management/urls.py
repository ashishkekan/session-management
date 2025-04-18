from django.urls import path

from .views import (
    add_user,
    all_sessions_view,
    change_password,
    create_external_topic,
    create_topic,
    delete_session_view,
    edit_session_view,
    edit_user,
    home,
    learning_view,
    my_profile,
    user_list,
    user_login,
    user_logout,
)

urlpatterns = [
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("add-user/", add_user, name="add_user"),
    path("my-profile/", my_profile, name="my_profile"),
    path("users/", user_list, name="user_list"),
    path("users/edit/<int:user_id>/", edit_user, name="edit_user"),
    path('change-password/', change_password, name='change_password'),
    path("", home, name="home"),
    path("sessions/", all_sessions_view, name="session_list"),
    path("sessions/<int:session_id>/edit/", edit_session_view, name="edit_session"),
    path("sessions/<int:session_id>/delete/", delete_session_view, name="delete_session"),
    path("create-topic/", create_topic, name="create-topic"),
    path("create-learning-topic/", create_external_topic, name="create-learning-topic"),
    path("learning-view/", learning_view, name="learning-view"),
    
]
