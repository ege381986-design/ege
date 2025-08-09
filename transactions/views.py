from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.utils import timezone

from .models import Transaction, Fine
from books.models import Book
from accounts.models import Member

class TransactionListView(LoginRequiredMixin, ListView):
    """
    Kullanıcının tüm işlem listesi
    """
    model = Transaction
    template_name = 'transactions.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        if self.request.user.is_staff:
            return Transaction.objects.all().select_related('book', 'member').order_by('-created_at')
        return Transaction.objects.filter(user=self.request.user).select_related('book').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_staff:
            context['pending_returns'] = Transaction.objects.filter(status='active').select_related('book', 'member')
        return context


class TransactionDetailView(LoginRequiredMixin, DetailView):
    """
    Tek bir işlem detayı
    """
    model = Transaction
    template_name = 'transaction_detail.html'
    context_object_name = 'transaction'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        if self.request.user.is_staff:
            return Transaction.objects.all()
        return Transaction.objects.filter(user=self.request.user)


class BorrowView(LoginRequiredMixin, TemplateView):
    """
    Kitap ödünç alma (basit form)
    """
    template_name = 'borrow.html'

    def post(self, request, *args, **kwargs):
        isbn = request.POST.get('isbn')
        book = get_object_or_404(Book, isbn=isbn)

        # Basit kontrol: mevcut mu?
        if not book.is_available():
            return HttpResponse('Kitap mevcut değil', status=400)

        # İşlem oluştur
        member = request.user.member_profile
        Transaction.objects.create(
            user=request.user,
            member=member,
            book=book,
            status='active',
            borrow_date=timezone.now(),
            due_date=timezone.now() + timezone.timedelta(days=14)
        )
        # Stok güncelle
        book.borrow()
        return redirect('transactions:transaction_list')


class ReturnView(LoginRequiredMixin, TemplateView):
    """
    Kitap iade etme
    """
    template_name = 'return.html'

    def post(self, request, *args, **kwargs):
        transaction_id = request.POST.get('transaction_id')
        transaction = get_object_or_404(Transaction, pk=transaction_id, user=request.user, status='active')
        transaction.status = 'returned'
        transaction.return_date = timezone.now()
        transaction.save()
        # Stok artır
        transaction.book.return_book()
        return redirect('transactions:transaction_list')


class MyFinesView(LoginRequiredMixin, ListView):
    """
    Kullanıcının ceza listesi
    """
    model = Fine
    template_name = 'my_fines.html'
    context_object_name = 'fines'
    paginate_by = 20

    def get_queryset(self):
        return Fine.objects.filter(user=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total = Fine.objects.filter(user=self.request.user, status='unpaid').aggregate(total=Sum('amount'))['total'] or 0
        context['total_unpaid'] = total
        return context
