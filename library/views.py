from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta

from accounts.models import User, Member
from books.models import Book, Category
from transactions.models import Transaction, Fine
from notifications.models import Notification


class IndexView(TemplateView):
    """
    Ana sayfa view'ı
    """
    template_name = 'index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Eğer kullanıcı giriş yapmışsa dashboard'a yönlendir
        if self.request.user.is_authenticated:
            return redirect('dashboard')
        
        # Genel istatistikler
        context.update({
            'total_books': Book.objects.count(),
            'available_books': Book.objects.filter(available_quantity__gt=0).count(),
            'total_members': Member.objects.filter(is_active=True).count(),
            'popular_categories': Category.objects.annotate(
                book_count=Count('bookcategory__book')
            ).order_by('-book_count')[:6],
            'featured_books': Book.objects.filter(
                average_rating__gte=4.0,
                available_quantity__gt=0
            ).order_by('-review_count', '-average_rating')[:8],
        })
        
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard view'ı - giriş yapmış kullanıcılar için
    """
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        try:
            member = user.member_profile
            # Üye dashboard'ı
            context.update({
                'is_member_dashboard': True,
                'member': member,
                'active_transactions': Transaction.objects.filter(
                    user=user,
                    status='active'
                ).select_related('book').order_by('due_date'),
                'overdue_transactions': Transaction.objects.filter(
                    user=user,
                    status='overdue'
                ).select_related('book').order_by('due_date'),
                'recent_transactions': Transaction.objects.filter(
                    user=user
                ).select_related('book').order_by('-created_at')[:5],
                'unpaid_fines': Fine.objects.filter(
                    user=user,
                    status='unpaid'
                ).select_related('transaction__book'),
                'unread_notifications': Notification.objects.filter(
                    user=user,
                    is_read=False
                ).order_by('-created_date')[:5],
                'recommendations': self.get_book_recommendations(user),
            })
        except Member.DoesNotExist:
            member = None
        
        # Kütüphaneci/Admin dashboard'ı
        if user.is_librarian() or user.is_admin():
            context.update({
                'is_staff_dashboard': True,
                'pending_returns': Transaction.objects.filter(
                    status='active'
                ).select_related('book', 'member').order_by('due_date')[:10],
                'overdue_count': Transaction.objects.filter(
                    status='overdue'
                ).count(),
                'fine_total': Fine.objects.filter(
                    status='unpaid'
                ).aggregate(total=Sum('amount'))['total'] or 0,
                'recent_members': Member.objects.filter(
                    is_active=True
                ).order_by('-join_date')[:5],
                'popular_books': Book.objects.filter(
                    total_borrow_count__gt=0
                ).order_by('-total_borrow_count')[:5],
            })
        
        # Genel istatistikler
        context.update({
            'total_books': Book.objects.count(),
            'available_books': Book.objects.filter(available_quantity__gt=0).count(),
            'active_members': Member.objects.filter(is_active=True).count(),
            'active_transactions': Transaction.objects.filter(status='active').count(),
        })
        
        return context
    
    def get_book_recommendations(self, user):
        """
        Kullanıcı için kitap önerileri
        """
        # Kullanıcının daha önce ödünç aldığı kitapların kategorilerini bul
        user_categories = Category.objects.filter(
            bookcategory__book__transactions__user=user
        ).distinct()
        
        if user_categories.exists():
            # Aynı kategorilerden, henüz ödünç almadığı kitapları öner
            recommended_books = Book.objects.filter(
                categories__in=user_categories,
                available_quantity__gt=0
            ).exclude(
                transactions__user=user
            ).distinct().order_by('-average_rating', '-total_borrow_count')[:6]
        else:
            # Yeni kullanıcı için popüler kitapları öner
            recommended_books = Book.objects.filter(
                available_quantity__gt=0,
                average_rating__gte=3.5
            ).order_by('-total_borrow_count', '-average_rating')[:6]
        
        return recommended_books


@login_required
def quick_search(request):
    """
    Hızlı arama view'ı - AJAX için
    """
    query = request.GET.get('q', '').strip()
    results = []
    
    if query and len(query) >= 2:
        # Kitap araması
        books = Book.objects.filter(
            Q(title__icontains=query) |
            Q(authors__icontains=query) |
            Q(isbn__icontains=query)
        )[:10]
        
        results = [{
            'type': 'book',
            'id': book.isbn,
            'title': book.title,
            'authors': book.authors,
            'available': book.is_available(),
            'url': f'/books/{book.isbn}/'
        } for book in books]
    
    return JsonResponse({'results': results})


def library_stats(request):
    """
    Kütüphane istatistikleri API endpoint'i
    """
    if not request.user.is_authenticated or not request.user.is_librarian():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Son 30 günün istatistikleri
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    stats = {
        'total_books': Book.objects.count(),
        'available_books': Book.objects.filter(available_quantity__gt=0).count(),
        'total_members': Member.objects.filter(is_active=True).count(),
        'active_transactions': Transaction.objects.filter(status='active').count(),
        'overdue_transactions': Transaction.objects.filter(status='overdue').count(),
        'unpaid_fines': Fine.objects.filter(status='unpaid').count(),
        'recent_activity': {
            'new_members': Member.objects.filter(
                join_date__gte=thirty_days_ago
            ).count(),
            'books_borrowed': Transaction.objects.filter(
                borrow_date__gte=thirty_days_ago
            ).count(),
            'books_returned': Transaction.objects.filter(
                return_date__gte=thirty_days_ago
            ).count(),
        }
    }
    
    return JsonResponse(stats)
