from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView, ListView, DetailView
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import User, Member
from books.models import Book
from transactions.models import Transaction, Fine


class LoginView(TemplateView):
    """
    Kullanıcı giriş view'ı
    """
    template_name = 'login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Giriş başarılı!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Kullanıcı adı veya şifre hatalı!')
            return render(request, self.template_name)


class LogoutView(TemplateView):
    """
    Kullanıcı çıkış view'ı
    """
    
    def get(self, request):
        logout(request)
        messages.info(request, 'Çıkış yapıldı.')
        return redirect('index')


class RegisterView(TemplateView):
    """
    Yeni kullanıcı kayıt view'ı
    """
    template_name = 'register.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Basit validasyon
        if password != confirm_password:
            messages.error(request, 'Şifreler eşleşmiyor!')
            return render(request, self.template_name)
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Bu kullanıcı adı zaten alınmış!')
            return render(request, self.template_name)
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Bu e-posta adresi zaten kayıtlı!')
            return render(request, self.template_name)
        
        # Yeni kullanıcı oluştur
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Üye profili oluştur
        Member.objects.create(
            user=user,
            first_name=username,
            join_date=timezone.now().date()
        )
        
        messages.success(request, 'Kayıt başarılı! Lütfen giriş yapın.')
        return redirect('accounts:login')


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    Kullanıcı profili view'ı
    """
    template_name = 'profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        try:
            member = user.member_profile
            context.update({
                'member': member,
                'transactions': Transaction.objects.filter(
                    user=user
                ).select_related('book').order_by('-created_at')[:10],
                'active_transactions': Transaction.objects.filter(
                    user=user,
                    status='active'
                ).count(),
                'overdue_transactions': Transaction.objects.filter(
                    user=user,
                    status='overdue'
                ).count(),
                'unpaid_fines': Fine.objects.filter(
                    user=user,
                    status='unpaid'
                ).aggregate(total_amount=Sum('amount'))['total_amount'] or 0,
            })
        except Member.DoesNotExist:
            context['member'] = None
        
        return context


class MemberListView(LoginRequiredMixin, ListView):
    """
    Üye listesi view'ı
    """
    model = Member
    template_name = 'members.html'
    context_object_name = 'members'
    paginate_by = 20
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        queryset = Member.objects.filter(is_active=True).select_related('user')
        
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(user__username__icontains=query) |
                Q(email__icontains=query)
            )
        
        return queryset.order_by('first_name', 'last_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class UserListView(LoginRequiredMixin, ListView):
    """
    Kullanıcı listesi view'ı (sadece admin için)
    """
    model = User
    template_name = 'users.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        if not self.request.user.is_staff:
            return User.objects.none()
        
        query = self.request.GET.get('q')
        queryset = User.objects.all()
        
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )
        
        return queryset.order_by('username')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class MyBooksView(LoginRequiredMixin, TemplateView):
    """
    Kullanıcının kitapları view'ı
    """
    template_name = 'my_books.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context.update({
            'active_transactions': Transaction.objects.filter(
                user=user,
                status='active'
            ).select_related('book').order_by('due_date'),
            'overdue_transactions': Transaction.objects.filter(
                user=user,
                status='overdue'
            ).select_related('book').order_by('due_date'),
            'history': Transaction.objects.filter(
                user=user
            ).select_related('book').order_by('-created_at')[:20],
        })
        
        return context


class MemberDetailView(LoginRequiredMixin, DetailView):
    """
    Üye detay view'ı
    """
    model = Member
    template_name = 'member_detail.html'
    context_object_name = 'member'
    slug_field = 'user__username'
    slug_url_kwarg = 'username'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.get_object()
        
        context.update({
            'transactions': Transaction.objects.filter(
                user=member.user
            ).select_related('book').order_by('-created_at')[:20],
            'active_transactions': Transaction.objects.filter(
                user=member.user,
                status='active'
            ).count(),
            'overdue_transactions': Transaction.objects.filter(
                user=member.user,
                status='overdue'
            ).count(),
            'unpaid_fines': Fine.objects.filter(
                user=member.user,
                status='unpaid'
            ).aggregate(total_amount=Sum('amount'))['total_amount'] or 0,
        })
        
        return context
