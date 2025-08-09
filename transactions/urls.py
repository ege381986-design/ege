from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('', views.TransactionListView.as_view(), name='transaction_list'),
    path('<int:pk>/', views.TransactionDetailView.as_view(), name='transaction_detail'),
    path('borrow/', views.BorrowView.as_view(), name='borrow'),
    path('return/', views.ReturnView.as_view(), name='return'),
    path('my-fines/', views.MyFinesView.as_view(), name='my_fines'),
]
