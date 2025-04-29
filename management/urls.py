from django.urls import path

from . import views

urlpatterns = [
    # User authentication routes
    path("home/", views.home, name="home"), # Home
    path("login/", views.user_login, name="login"),  # Log in page
    path("logout/", views.user_logout, name="logout"),  # Log out page
    path("add-user/", views.add_user, name="add_user"),  # Add new user
    path("my-profile/", views.my_profile, name="my_profile"),  # User profile page
    path("users/", views.user_list, name="user_list"),  # List of users
    path("users/edit/<int:user_id>/", views.edit_user, name="edit_user"),  # Edit user details
    path('users/delete/<int:user_id>/', views.delete_user, name='delete_user'), # Delete user details
    path('change-password/', views.change_password, name='change_password'),  # Change user password
    
    # Home page
    path("", views.home, name="home"),  # Home page

    # Session management routes
    path("sessions/", views.all_sessions_view, name="session_list"),  # List all sessions
    path("sessions/<int:session_id>/edit/", views.edit_session_view, name="edit_session"),  # Edit session details
    path("sessions/<int:session_id>/delete/", views.delete_session_view, name="delete_session"),  # Delete a session
    
    # Topic management routes
    path("create-topic/", views.create_topic, name="create-topic"),  # Create a new session topic
    path("create-learning-topic/", views.create_external_topic, name="create-learning-topic"),  # Create an external learning topic
    path("learning-view/", views.learning_view, name="learning-view"),  # View all learning topics
    path("learning-view/<int:learning_id>/edit/", views.edit_learning, name="edit-learning"),  # Edit learning topic
    path("learning-view/<int:learning_id>/delete/", views.delete_learning, name="delete-learning")  # Delete learning topic
]
