from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    path('', views.BookListView.as_view(), name='book_list'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('<int:pk>/', views.BookDetailView.as_view(), name='book_detail'),
    path('online-borrow/', views.OnlineBorrowView.as_view(), name='online_borrow'),
    path('my-online-requests/', views.MyOnlineRequestsView.as_view(), name='my_online_requests'),
    path('online-borrow-requests/', views.OnlineBorrowRequestsView.as_view(), name='online_borrow_requests'),
    path('my-reservations/', views.MyReservationsView.as_view(), name='my_reservations'),
]
