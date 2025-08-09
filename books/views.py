from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse

from .models import Book, Category, Review, OnlineBorrowRequest, Reservation
from accounts.models import Member
from transactions.models import Transaction, Fine


class BookListView(ListView):
    """Kitap listesi - sayfalama ve filtreleme"""
    model = Book
    template_name = 'books.html'
    context_object_name = 'books'
    paginate_by = 20

    def get_queryset(self):
        qs = Book.objects.all().prefetch_related('categories', 'reviews')
        q = self.request.GET.get('q')
        cat = self.request.GET.get('category')
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(authors__icontains=q) |
                Q(isbn__icontains=q)
            ).distinct()
        if cat:
            qs = qs.filter(categories__id=cat)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'categories': Category.objects.all(),
            'search_query': self.request.GET.get('q', ''),
            'selected_category': self.request.GET.get('category', ''),
        })
        return ctx


class BookDetailView(DetailView):
    """Kitap detay sayfası"""
    model = Book
    template_name = 'book_detail.html'
    context_object_name = 'book'
    slug_field = 'isbn'
    slug_url_kwarg = 'isbn'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        book = self.object
        ctx.update({
            'reviews': book.reviews.filter(is_approved=True).select_related('user').order_by('-created_at')[:10],
            'similar_books': Book.objects.filter(
                categories__in=book.categories.all()
            ).exclude(id=book.id).distinct().order_by('-average_rating')[:6],
        })
        return ctx


class SearchView(TemplateView):
    """Arama sonuçları - AJAX destekli"""
    template_name = 'search.html'

    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        results = []
        if query:
            books = Book.objects.filter(
                Q(title__icontains=query) |
                Q(authors__icontains=query) |
                Q(isbn__icontains=query)
            )[:10]
            results = [
                {
                    'isbn': b.isbn,
                    'title': b.title,
                    'authors': b.authors,
                    'url': reverse('books:book_detail', kwargs={'isbn': b.isbn})
                } for b in books
            ]
        return JsonResponse({'results': results})


class OnlineBorrowView(TemplateView):
    """Online ödünç alma formu"""
    template_name = 'online_borrow.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('accounts:login'))
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('accounts:login'))

        book_isbn = request.POST.get('isbn')
        pickup_date = request.POST.get('pickup_date')
        pickup_time = request.POST.get('pickup_time')
        notes = request.POST.get('notes', '')

        book = get_object_or_404(Book, isbn=book_isbn)
        member = request.user.member_profile

        OnlineBorrowRequest.objects.create(
            book=book,
            user=request.user,
            member=member,
            pickup_date=pickup_date,
            pickup_time=pickup_time,
            notes=notes,
        )
        return redirect('books:my_online_requests')


class MyOnlineRequestsView(TemplateView):
    """Kullanıcının online ödünç istekleri"""
    template_name = 'my_online_requests.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('accounts:login'))
        requests = OnlineBorrowRequest.objects.filter(user=request.user).order_by('-created_at')
        return render(request, self.template_name, {'requests': requests})


class OnlineBorrowRequestsView(TemplateView):
    """Tüm online ödünç istekleri (personel için)"""
    template_name = 'online_borrow_requests.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseRedirect(reverse('accounts:login'))
        reqs = OnlineBorrowRequest.objects.all().order_by('-created_at')
        return render(request, self.template_name, {'requests': reqs})


class MyReservationsView(TemplateView):
    """Kullanıcının rezervasyonları"""
    template_name = 'my_reservations.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('accounts:login'))
        reservations = Reservation.objects.filter(user=request.user).order_by('-reservation_date')
        return render(request, self.template_name, {'reservations': reservations})
