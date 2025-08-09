// Modern Kütüphane Yönetim Sistemi - DONMA PROBLEMİ ÇÖZÜLMÜŞ
// Hızlı yanıt ve stabil çalışma için optimize edildi

// HIZLI ÇALIŞMA İÇİN KONFİGÜRASYON
const AppConfig = {
    timeout: 3000,          // 3 saniye (çok hızlı)
    maxLoadingTime: 4000,   // 4 saniye maksimum
    itemsPerPage: 20,
    debounceDelay: 150      // 150ms (çok hızlı tepki)
};

// BASİT GLOBAL DEĞİŞKENLER
let isLoadingActive = false;
let loadingTimeout = null;
let activeRequests = new Set();

// ESC TUŞU İLE ACİL ÇIKIŞ - GÜÇLENDİRİLMİŞ
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        console.log('🛑 ESC - Acil çıkış!');
        e.preventDefault();
        e.stopPropagation();
        emergencyCleanup();
        return false;
    }
}, true);

// HIZLI AJAX KURULUMU
$.ajaxSetup({
    timeout: AppConfig.timeout,
    beforeSend: function(xhr) {
        activeRequests.add(xhr);
        if (!isLoadingActive) {
            showQuickLoading();
        }
    },
    complete: function(xhr) {
        activeRequests.delete(xhr);
        if (activeRequests.size === 0) {
            hideQuickLoading();
        }
    },
    error: function(xhr, status, error) {
        hideQuickLoading();
        if (status === 'timeout') {
            showToast('İşlem zaman aşımına uğradı', 'warning');
        } else if (xhr.status === 0) {
            showToast('Bağlantı hatası', 'danger');
        } else {
            showToast('Hata: ' + (xhr.responseJSON?.message || error), 'danger');
        }
    }
});

// UYGULAMA BAŞLATMA - OPTİMİZE EDİLMİŞ
$(document).ready(function() {
    console.log('🚀 Kütüphane sistemi başlatılıyor...');
    
    try {
        // Temel bileşenleri hızla başlat
        initializeBasics();
        
        // Sayfa verilerini güvenli şekilde yükle
        setTimeout(loadPageData, 100);
        
        console.log('✅ Sistem başlatıldı');
    } catch (error) {
        console.error('Başlatma hatası:', error);
        showToast('Sistem başlatılırken hata oluştu', 'warning');
    }
});

// TEMEL BİLEŞENLER
function initializeBasics() {
    // Tooltip'leri başlat
    try {
        $('[data-bs-toggle="tooltip"]').tooltip();
    } catch (e) {
        console.warn('Tooltip hatası:', e);
    }
    
    // Tema yükle
    loadTheme();
    
    // Event listener'lar
    $('#darkModeToggle').on('click', toggleDarkMode);
    $('#themeSelector').on('change', changeTheme);
    
    // Auto-hide alerts
    setTimeout(() => {
        $('.alert:not(.alert-permanent)').fadeOut();
    }, 3000);
}

// TEMA YÖNETİMİ - GELİŞTİRİLMİŞ
function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'default';
    applyTheme(savedTheme);
    
    // Tema seçiciyi güncelle
    if ($('#themeSelector').length) {
        $('#themeSelector').val(savedTheme);
    }
}

function applyTheme(theme) {
    // Önceki tema sınıflarını kaldır
    $('body').removeClass('theme-red theme-grey theme-bordo theme-rainbow dark-mode');
    
    // Yeni tema sınıfını ekle
    if (theme === 'dark') {
        $('body').addClass('dark-mode');
    } else if (theme !== 'default') {
        $('body').addClass(`theme-${theme}`);
    }
    
    // LocalStorage'a kaydet
    localStorage.setItem('theme', theme);
    
    console.log(`🎨 Tema değiştirildi: ${theme}`);
}

function changeTheme() {
    const selectedTheme = $('#themeSelector').val();
    applyTheme(selectedTheme);
    
    // Sunucuya tema tercihini gönder
    if (isUserAuthenticated()) {
        $.post('/api/user/theme', { theme: selectedTheme })
            .done(function() {
                showToast('Tema tercihiniz kaydedildi', 'success');
            })
            .fail(function() {
                showToast('Tema tercihi kaydedilemedi', 'warning');
            });
    }
}

function toggleDarkMode() {
    const currentTheme = localStorage.getItem('theme') || 'default';
    const newTheme = currentTheme === 'dark' ? 'default' : 'dark';
    applyTheme(newTheme);
    
    // Tema seçiciyi güncelle
    if ($('#themeSelector').length) {
        $('#themeSelector').val(newTheme);
    }
    
    showToast(`Tema değiştirildi: ${newTheme === 'dark' ? 'Karanlık' : 'Açık'}`, 'info');
}

// HIZLI LOADİNG - MİNİMALİST
function showQuickLoading() {
    // Yükleniyor spinnerı ve overlay hiç gösterilmesin
    return;
}

function hideQuickLoading() {
    if (!isLoadingActive) return;
    
    isLoadingActive = false;
    console.log('📤 Hiding loading...');
    
    if (loadingTimeout) {
        clearTimeout(loadingTimeout);
        loadingTimeout = null;
    }
    
    $('#quickSpinner').remove();
}

function forceHideLoading() {
    isLoadingActive = false;
    if (loadingTimeout) {
        clearTimeout(loadingTimeout);
        loadingTimeout = null;
    }
    $('#quickSpinner').remove();
    cancelAllRequests();
}

// TOAST BİLDİRİM - HIZLI
function showToast(message, type = 'info', duration = 3000) {
    const colors = {
        'info': 'bg-primary',
        'success': 'bg-success', 
        'warning': 'bg-warning text-dark',
        'danger': 'bg-danger',
        'error': 'bg-danger'
    };
    
    const color = colors[type] || colors.info;
    
    const toast = $(`
        <div class="toast-item" style="position:fixed; top:20px; right:20px; z-index:9999; 
             padding:12px 20px; border-radius:6px; color:white; font-size:14px; 
             box-shadow:0 4px 12px rgba(0,0,0,0.3); cursor:pointer;" class="${color}">
            ${message}
        </div>
    `);
    
    $('body').append(toast);
    
    // Fade in
    toast.hide().fadeIn(200);
    
    // Click to dismiss
    toast.on('click', function() {
        $(this).fadeOut(150, function() { $(this).remove(); });
    });
    
    // Auto remove
    setTimeout(() => {
        toast.fadeOut(150, function() { $(this).remove(); });
    }, duration);
}

// SAYFA VERİLERİNİ GÜVENLİ YÜKLEME
function loadPageData() {
    const path = window.location.pathname;
    console.log('📄 Sayfa verileri:', path);
    
    try {
        switch (path) {
            case '/books':
                if (typeof loadBooks === 'function') {
                    setTimeout(loadBooks, 50);
                }
                break;
            case '/members':
                if (typeof loadMembers === 'function') {
                    setTimeout(loadMembers, 50);
                }
                break;
            case '/transactions':
                if (typeof loadTransactions === 'function') {
                    setTimeout(loadTransactions, 50);
                }
                break;
            case '/notifications':
                if (typeof loadNotifications === 'function') {
                    setTimeout(loadNotifications, 50);
                }
                break;
        }
    } catch (error) {
        console.error('Sayfa yükleme hatası:', error);
        hideQuickLoading();
    }
}

// BİLDİRİM KONTROLÜ - OPTİMİZE
function checkNotifications() {
    if (!isUserAuthenticated()) return;
    
    $.ajax({
        url: '/api/notifications?unread_only=true',
        timeout: 2000,
        showLoading: false,
        success: function(data) {
            const count = data.notifications ? data.notifications.length : 0;
            updateNotificationBadge(count);
        },
        error: function() {
            // Sessizce başarısız ol
        }
    });
}

function updateNotificationBadge(count) {
    const badge = $('#notificationBadge');
    if (count > 0) {
        badge.text(count).show();
    } else {
        badge.hide();
    }
}

// İSTEK İPTAL ETME
function cancelAllRequests() {
    console.log('🛑 Tüm istekler iptal ediliyor:', activeRequests.size);
    activeRequests.forEach(xhr => {
        if (xhr.readyState !== 4) {
            xhr.abort();
        }
    });
    activeRequests.clear();
}

// KULLANICI OTURUM KONTROLÜ
function isUserAuthenticated() {
    return $('#userDropdown').length > 0 || $('body').hasClass('authenticated');
}

// SAYFALAMA OLUŞTUR
function createPagination(total, current, perPage, containerId) {
    const totalPages = Math.ceil(total / perPage);
    const container = $(`#${containerId}`);
    
    if (totalPages <= 1) {
        container.empty();
        return;
    }
    
    let pagination = '<nav><ul class="pagination pagination-sm justify-content-center">';
    
    // Önceki sayfa
    if (current > 1) {
        pagination += `<li class="page-item"><a class="page-link" href="#" onclick="loadCurrentPageData(${current - 1})">«</a></li>`;
    }
    
    // Sayfa numaraları (sadece gerekli olanlar)
    const start = Math.max(1, current - 2);
    const end = Math.min(totalPages, current + 2);
    
    for (let i = start; i <= end; i++) {
        const active = i === current ? 'active' : '';
        pagination += `<li class="page-item ${active}"><a class="page-link" href="#" onclick="loadCurrentPageData(${i})">${i}</a></li>`;
    }
    
    // Sonraki sayfa
    if (current < totalPages) {
        pagination += `<li class="page-item"><a class="page-link" href="#" onclick="loadCurrentPageData(${current + 1})">»</a></li>`;
    }
    
    pagination += '</ul></nav>';
    container.html(pagination);
}

// SAYFA VERİSİ YÜKLEME (Dinamik)
function loadCurrentPageData(page) {
    const path = window.location.pathname;
    
    switch (path) {
        case '/books':
            if (typeof loadBooks === 'function') loadBooks(page);
            break;
        case '/members':
            if (typeof loadMembers === 'function') loadMembers(page);
            break;
        case '/transactions':
            if (typeof loadTransactions === 'function') loadTransactions(page);
            break;
    }
}

// DEBOUNCE UTİLİTY
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// TARİH FORMATLAMA
function formatDate(dateString) {
    if (!dateString || dateString === '-') return '-';
    try {
        return new Date(dateString).toLocaleDateString('tr-TR');
    } catch {
        return dateString;
    }
}

// PARA FORMATLAMA
function formatCurrency(amount) {
    try {
        return new Intl.NumberFormat('tr-TR', {
            style: 'currency',
            currency: 'TRY'
        }).format(amount);
    } catch {
        return amount + ' TL';
    }
}

// CONFIRM DİYALOG
function confirmDialog(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// KOPYALA
function copyToClipboard(text) {
    try {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Kopyalandı!', 'success');
        }).catch(() => {
            // Fallback
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showToast('Kopyalandı!', 'success');
        });
    } catch {
        showToast('Kopyalama başarısız', 'warning');
    }
}

// ACİL TEMİZLİK FONKSİYONLARI
window.emergencyCleanup = function() {
    console.log('🧯 ACİL TEMİZLİK!');
    
    try {
        // Loading'i zorla kapat
        forceHideLoading();
        
        // Modal'ları kapat
        $('.modal').modal('hide');
        $('.modal-backdrop').remove();
        $('body').removeClass('modal-open').css('padding-right', '');
        
        // Spinner'ları temizle
        $('#quickSpinner').remove();
        
        showToast('Acil temizlik tamamlandı!', 'success', 2000);
        
    } catch (error) {
        console.error('Acil temizlik hatası:', error);
        location.reload();
    }
};

window.forceReload = function() {
    console.log('🔄 ZORLA YENİLEME!');
    location.reload();
};

// HATA YAKALAYıCı
window.addEventListener('error', function(e) {
    console.error('Global hata:', e.error);
    showToast('Bir hata oluştu', 'warning');
});

// BİLDİRİM BAŞLATMA
if (isUserAuthenticated()) {
    setTimeout(checkNotifications, 1000);
    setInterval(checkNotifications, 60000); // 1 dakikada bir
}

// GLOBAL FONKSİYONLAR
window.LibraryApp = {
    showToast,
    showQuickLoading,
    hideQuickLoading,
    confirmDialog,
    copyToClipboard,
    formatDate,
    formatCurrency,
    emergencyCleanup
};

console.log('📚 Kütüphane JavaScript yüklendi - ESC Desteği Aktif');
