from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('members/', views.MemberListView.as_view(), name='member_list'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('my-books/', views.MyBooksView.as_view(), name='my_books'),
    path('member/<int:pk>/', views.MemberDetailView.as_view(), name='member_detail'),
]
