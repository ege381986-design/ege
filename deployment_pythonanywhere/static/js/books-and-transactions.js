// Kütüphane Yönetimi - Kitap ve İşlem Fonksiyonları - OPTİMİZE EDİLMİŞ
// Donma problemleri çözüldü, hızlı çalışma için basitleştirildi

// SAYFA DEĞİŞKENLERİ
let currentBookPage = 1;
let currentMemberPage = 1;
let currentTransactionPage = 1;

// ==================== KİTAP YÖNETİMİ - OPTİMİZE EDİLMİŞ ====================

// Kitapları yükle - Hızlı versiyon
function loadBooks(page = 1) {
    const search = $('#bookSearch').val() || '';
    
    $.ajax({
        url: '/api/books',
        method: 'GET',
        data: { 
            page: page, 
            per_page: 20, 
            search: search
        },
        timeout: 3000,
        success: function(data) {
            displayBooks(data.books);
            updatePagination(data.total, page, 'booksPagination');
            currentBookPage = page;
        },
        error: function() {
            $('#booksTableBody').html('<tr><td colspan="8" class="text-center text-danger">Yükleme hatası</td></tr>');
        }
    });
}

// Kitapları göster - Basitleştirilmiş
function displayBooks(books) {
    const tbody = $('#booksTableBody');
    tbody.empty();
    
    if (!books || books.length === 0) {
        tbody.html('<tr><td colspan="8" class="text-center text-muted">Kitap bulunamadı</td></tr>');
        return;
    }
    
    books.forEach(book => {
        const available = book.available > 0 ? 
            `<span class="badge bg-success">${book.available}</span>` : 
            `<span class="badge bg-danger">0</span>`;
            
        const location = (book.shelf || book.cupboard) ? 
            `${book.shelf || ''} ${book.cupboard || ''}`.trim() : '-';
            
        // Kapak görseli
        const coverImg = book.image_path ? `<img src="${book.image_path}" alt="Kapak" style="height:48px;max-width:40px;object-fit:cover;border-radius:4px;">` : '<span class="text-muted">-</span>';
        
        tbody.append(`
            <tr>
                <td>${coverImg}</td>
                <td><code>${book.isbn}</code></td>
                <td><strong>${book.title}</strong><br><small class="text-muted">${book.authors}</small></td>
                <td>${book.publishers || '-'}</td>
                <td><span class="badge bg-primary">${book.quantity}</span></td>
                <td>${available}</td>
                <td>${location}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-info" onclick="viewBook('${book.isbn}')" title="Görüntüle">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-outline-warning" onclick="editBook('${book.isbn}')" title="Düzenle">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="confirmDeleteBook('${book.isbn}')" title="Sil">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `);
    });
}

// Kitap ekle modalını göster
function showAddBookModal() {
    $('#addBookForm')[0].reset();
    $('#addBookModal').modal('show');
}

// Kitap ekle
function addBook() {
    const form = $('#addBookForm');
    const data = {
        isbn: form.find('#addBookISBN').val().trim(),
        title: form.find('#addBookTitle').val().trim(),
        authors: form.find('#addBookAuthors').val().trim(),
        publish_date: form.find('#addBookPublishDate').val().trim(),
        number_of_pages: parseInt(form.find('#addBookPages').val()) || 0,
        publishers: form.find('#addBookPublishers').val().trim(),
        languages: form.find('#addBookLanguages').val().trim(),
        quantity: parseInt(form.find('#addBookQuantity').val()) || 1,
        shelf: form.find('#addBookShelf').val().trim(),
        cupboard: form.find('#addBookCupboard').val().trim()
    };
    
    // Validation
    if (!data.isbn || !data.title || !data.authors) {
        showToast('ISBN, başlık ve yazar gerekli', 'warning');
        return;
    }
    
    // AJAX call
    $.ajax({
        url: '/api/books/add',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(resp) {
            showToast(resp.message || 'Kitap eklendi', 'success');
            $('#addBookModal').modal('hide');
            form[0].reset(); // Form'u temizle
            if (typeof loadBooks === 'function') {
                loadBooks(currentBookPage || 1);
            }
        },
        error: function(xhr) {
            const errorMsg = xhr.responseJSON?.message || 'Ekleme hatası';
            showToast(errorMsg, 'error');
            console.error('Book add error:', xhr);
        }
    });
}

// Kitap düzenle
function editBook(isbn) {
    $.ajax({
        url: `/api/books/${isbn}`,
        method: 'GET',
        timeout: 2000,
        success: function(book) {
            // Form alanlarını doldur
            $('#editBookISBN').val(book.isbn);
            $('#editBookISBNDisplay').val(book.isbn);
            $('#editBookTitle').val(book.title);
            $('#editBookAuthors').val(book.authors);
            $('#editBookPublishDate').val(book.publish_date);
            $('#editBookPages').val(book.number_of_pages);
            $('#editBookPublishers').val(book.publishers);
            $('#editBookLanguages').val(book.languages);
            $('#editBookQuantity').val(book.quantity);
            $('#editBookShelf').val(book.shelf);
            $('#editBookCupboard').val(book.cupboard);
            
            $('#editBookModal').modal('show');
        },
        error: function() {
            showToast('Kitap bilgileri alınamadı', 'error');
        }
    });
}

// Kitap güncelle
function updateBook() {
    const isbn = $('#editBookISBN').val();
    const form = $('#editBookForm');
    const data = {
        title: form.find('#editBookTitle').val().trim(),
        authors: form.find('#editBookAuthors').val().trim(),
        publish_date: form.find('#editBookPublishDate').val().trim(),
        number_of_pages: parseInt(form.find('#editBookPages').val()) || 0,
        publishers: form.find('#editBookPublishers').val().trim(),
        languages: form.find('#editBookLanguages').val().trim(),
        quantity: parseInt(form.find('#editBookQuantity').val()) || 1,
        shelf: form.find('#editBookShelf').val().trim(),
        cupboard: form.find('#editBookCupboard').val().trim()
    };
    
    // Validation
    if (!data.title || !data.authors) {
        showToast('Başlık ve yazar gerekli', 'warning');
        return;
    }
    
    $.ajax({
        url: `/api/books/${isbn}`,
        method: 'PUT',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(resp) {
            showToast(resp.message || 'Kitap güncellendi', 'success');
            $('#editBookModal').modal('hide');
            if (typeof loadBooks === 'function') {
                loadBooks(currentBookPage || 1);
            }
        },
        error: function(xhr) {
            const errorMsg = xhr.responseJSON?.message || 'Güncelleme hatası';
            showToast(errorMsg, 'error');
            console.error('Book update error:', xhr);
        }
    });
}

// Kitap silme onayı
function confirmDeleteBook(isbn) {
    if (confirm('Bu kitabı silmek istediğinizden emin misiniz?')) {
        deleteBook(isbn);
    }
}

// Kitap sil
function deleteBook(isbn) {
    $.ajax({
        url: `/api/books/${isbn}`,
        method: 'DELETE',
        success: function(resp) {
            showToast(resp.message || 'Kitap silindi', 'success');
            loadBooks(currentBookPage);
        },
        error: function(xhr) {
            showToast(xhr.responseJSON?.message || 'Silme hatası', 'error');
        }
    });
}

// Kitap görüntüle
function viewBook(isbn) {
    window.location.href = `/book/${isbn}`;
}

// Kitap arama - Hızlı
const searchBooks = debounce(function() {
    loadBooks(1);
}, 300);

// ==================== ÜYE YÖNETİMİ - OPTİMİZE EDİLMİŞ ====================

// Üyeleri yükle
function loadMembers(page = 1) {
    const search = $('#memberSearch').val() || '';
    
    $.ajax({
        url: '/api/members',
        method: 'GET',
        data: { 
            page: page, 
            per_page: 20, 
            search: search
        },
        timeout: 3000,
        success: function(data) {
            displayMembers(data.members);
            updatePagination(data.total, page, 'membersPagination');
            currentMemberPage = page;
        },
        error: function() {
            $('#membersTableBody').html('<tr><td colspan="7" class="text-center text-danger">Yükleme hatası</td></tr>');
        }
    });
}

// Üyeleri göster
function displayMembers(members) {
    const tbody = $('#membersTableBody');
    tbody.empty();
    
    if (!members || members.length === 0) {
        tbody.html('<tr><td colspan="7" class="text-center text-muted">Üye bulunamadı</td></tr>');
        return;
    }
    
    members.forEach(member => {
        const typeBadge = {
            'Öğrenci': 'bg-primary',
            'Öğretmen': 'bg-success', 
            'Personel': 'bg-info'
        }[member.uye_turu] || 'bg-secondary';
        
        tbody.append(`
            <tr>
                <td>${member.id}</td>
                <td><strong>${member.ad_soyad}</strong></td>
                <td>${member.sinif || '-'}</td>
                <td><code>${member.numara}</code></td>
                <td>${member.email || '-'}</td>
                <td><span class="badge ${typeBadge}">${member.uye_turu}</span></td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-warning" onclick="editMember(${member.id})" title="Düzenle">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="confirmDeleteMember(${member.id})" title="Sil">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `);
    });
}

// Üye silme onayı
function confirmDeleteMember(id) {
    if (confirm('Bu üyeyi silmek istediğinizden emin misiniz?')) {
        deleteMember(id);
    }
}

// Üye sil
function deleteMember(id) {
    $.ajax({
        url: `/api/members/${id}`,
        method: 'DELETE',
        success: function(resp) {
            showToast(resp.message || 'Üye silindi', 'success');
            loadMembers(currentMemberPage);
        },
        error: function(xhr) {
            showToast(xhr.responseJSON?.message || 'Silme hatası', 'error');
        }
    });
}

// Üye düzenle
function editMember(id) {
    $.ajax({
        url: `/api/members/${id}`,
        method: 'GET',
        timeout: 2000,
        success: function(member) {
            // Form alanlarını doldur
            $('#editMemberId').val(member.id);
            $('#editMemberName').val(member.ad_soyad);
            $('#editMemberClass').val(member.sinif);
            $('#editMemberNumber').val(member.numara);
            $('#editMemberEmail').val(member.email);
            $('#editMemberType').val(member.uye_turu);
            
            $('#editMemberModal').modal('show');
        },
        error: function() {
            showToast('Üye bilgileri alınamadı', 'error');
        }
    });
}

// Üye güncelle
function updateMember() {
    const id = $('#editMemberId').val();
    const form = $('#editMemberForm');
    const data = {
        ad_soyad: form.find('#editMemberName').val().trim(),
        sinif: form.find('#editMemberClass').val(),
        numara: form.find('#editMemberNumber').val().trim(),
        email: form.find('#editMemberEmail').val().trim(),
        uye_turu: form.find('#editMemberType').val()
    };
    
    if (!data.ad_soyad || !data.numara) {
        showToast('Ad soyad ve numara gerekli', 'warning');
        return;
    }
    
    $.ajax({
        url: `/api/members/${id}`,
        method: 'PUT',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(resp) {
            showToast(resp.message || 'Üye güncellendi', 'success');
            $('#editMemberModal').modal('hide');
            if (typeof loadMembers === 'function') {
                loadMembers(currentMemberPage || 1);
            }
        },
        error: function(xhr) {
            showToast(xhr.responseJSON?.message || 'Güncelleme hatası', 'error');
        }
    });
}

// Üye arama
const searchMembers = debounce(function() {
    loadMembers(1);
}, 300);

// Üye ekle modalını göster
function showAddMemberModal() {
    $('#addMemberForm')[0].reset();
    $('#addMemberModal').modal('show');
}

// Üye ekle
function addMember() {
    const form = $('#addMemberForm');
    const data = {
        ad_soyad: form.find('#addMemberName').val().trim(),
        sinif: form.find('#addMemberClass').val(),
        numara: form.find('#addMemberNumber').val().trim(),
        email: form.find('#addMemberEmail').val().trim(),
        uye_turu: form.find('#addMemberType').val()
    };
    
    // Validation
    if (!data.ad_soyad || !data.numara) {
        showToast('Ad Soyad ve Numara zorunludur', 'warning');
        return;
    }
    
    // AJAX call
    $.ajax({
        url: '/api/members',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(resp) {
            showToast(resp.message || 'Üye eklendi', 'success');
            $('#addMemberModal').modal('hide');
            form[0].reset(); // Form'u temizle
            if (typeof loadMembers === 'function') {
                loadMembers(1);
            }
        },
        error: function(xhr) {
            const errorMsg = xhr.responseJSON?.message || 'Ekleme hatası';
            showToast(errorMsg, 'error');
            console.error('Member add error:', xhr);
        }
    });
}

// ==================== İŞLEM YÖNETİMİ - OPTİMİZE EDİLMİŞ ====================

// İşlemleri yükle
function loadTransactions(page = 1, status = 'all') {
    $.ajax({
        url: '/api/transactions',
        method: 'GET',
        data: { 
            page: page, 
            per_page: 20, 
            status: status
        },
        timeout: 3000,
        success: function(data) {
            displayTransactions(data.transactions);
            updatePagination(data.total, page, 'transactionsPagination');
            currentTransactionPage = page;
        },
        error: function() {
            $('#transactionsTableBody').html('<tr><td colspan="8" class="text-center text-danger">Yükleme hatası</td></tr>');
        }
    });
}

// İşlemleri göster
function displayTransactions(transactions) {
    const tbody = $('#transactionsTableBody');
    tbody.empty();
    
    if (!transactions || transactions.length === 0) {
        tbody.html('<tr><td colspan="8" class="text-center text-muted">İşlem bulunamadı</td></tr>');
        return;
    }
    
    transactions.forEach(trans => {
        let statusBadge, actionButton = '';
        if (trans.return_date) {
            statusBadge = '<span class="badge bg-success">İade Edildi</span>';
        } else if (trans.is_overdue) {
            statusBadge = '<span class="badge bg-danger">Gecikmiş</span>';
            actionButton = `<button class="btn btn-sm btn-primary" onclick="quickReturn(${trans.id})">Hızlı İade</button>`;
        } else {
            statusBadge = '<span class="badge bg-warning text-dark">Ödünçte</span>';
            actionButton = `<button class="btn btn-sm btn-primary" onclick="quickReturn(${trans.id})">Hızlı İade</button>`;
        }
        // Süre uzat butonu (iade edilmemiş ve yenileme hakkı varsa)
        if (!trans.return_date && trans.can_renew) {
            actionButton += ` <button class="btn btn-sm btn-warning" onclick="renewTransaction(${trans.id})">Süre Uzat</button>`;
        }
        const rowClass = trans.is_overdue ? 'table-danger' : '';
        // Kalan gün/gün gecikme hesaplama
        let kalanGunHtml = '';
        if (trans.due_date && !trans.return_date) {
            const today = new Date();
            const due = new Date(trans.due_date);
            const diffTime = due.setHours(0,0,0,0) - today.setHours(0,0,0,0);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            if (diffDays > 0) {
                kalanGunHtml = `<span class='badge bg-info ms-1'>${diffDays} gün kaldı</span>`;
            } else if (diffDays === 0) {
                kalanGunHtml = `<span class='badge bg-warning text-dark ms-1'>Bugün teslim</span>`;
            } else {
                kalanGunHtml = `<span class='badge bg-danger ms-1'>${-diffDays} gün gecikti</span>`;
            }
        }
        tbody.append(`
            <tr class="${rowClass}">
                <td>${trans.id}</td>
                <td>
                    <strong>${trans.book_title}</strong><br>
                    <small class="text-muted"><code>${trans.isbn}</code></small>
                </td>
                <td>${trans.member_name}</td>
                <td>${formatDate(trans.borrow_date)}</td>
                <td class="${trans.is_overdue ? 'text-danger fw-bold' : ''}">${formatDate(trans.due_date)} ${kalanGunHtml}</td>
                <td>${trans.return_date ? formatDate(trans.return_date) : '-'}</td>
                <td>${statusBadge}</td>
                <td>${actionButton}</td>
            </tr>
        `);
    });
}

// Hızlı iade
function quickReturn(transactionId) {
    if (confirm('Bu kitabı iade almak istediğinizden emin misiniz?')) {
        $.ajax({
            url: `/api/transactions/${transactionId}/quick-return`,
            method: 'POST',
            success: function() {
                showToast('Kitap iade alındı', 'success');
                loadTransactions(currentTransactionPage);
            },
            error: function(xhr) {
                showToast(xhr.responseJSON?.message || 'İade hatası', 'error');
            }
        });
    }
}

// İşlem filtreleme
function filterTransactions(filter) {
    // Radio button'ları güncelle
    $(`input[value="${filter}"]`).prop('checked', true);
    loadTransactions(1, filter);
}

// ==================== ÖDÜNÇ VER/İADE AL - BASİTLEŞTİRİLMİŞ ====================

// Ödünç ver
function borrowBook() {
    const isbn = $('#borrowISBN').val().trim();
    const schoolNo = $('#borrowMemberNo').val().trim();
    const dueDate = $('#borrowDueDate').val();
    
    if (!isbn || !schoolNo || !dueDate) {
        showToast('Tüm alanları doldurun', 'warning');
        return;
    }
    
    $.ajax({
        url: '/api/transactions/borrow',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            isbn: isbn,
            school_no: schoolNo,
            due_date: dueDate
        }),
        success: function() {
            showToast('Kitap ödünç verildi', 'success');
            $('#borrowForm')[0].reset();
            $('#borrowModal').modal('hide');
            loadTransactions(currentTransactionPage);
        },
        error: function(xhr) {
            showToast(xhr.responseJSON?.message || 'Ödünç verme hatası', 'error');
        }
    });
}

// İade al
function returnBook() {
    const isbn = $('#returnISBN').val().trim();
    const schoolNo = $('#returnMemberNo').val().trim();
    
    if (!isbn || !schoolNo) {
        showToast('ISBN ve üye numarası gerekli', 'warning');
        return;
    }
    
    $.ajax({
        url: '/api/transactions/return',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            isbn: isbn,
            school_no: schoolNo
        }),
        success: function() {
            showToast('Kitap iade alındı', 'success');
            $('#returnForm')[0].reset();
            $('#returnModal').modal('hide');
            loadTransactions(currentTransactionPage);
        },
        error: function(xhr) {
            showToast(xhr.responseJSON?.message || 'İade alma hatası', 'error');
        }
    });
}

// ==================== BİLDİRİM YÖNETİMİ ====================

// Bildirimleri yükle
function loadNotifications() {
    $.ajax({
        url: '/api/notifications',
        method: 'GET',
        timeout: 2000,
        success: function(data) {
            displayNotifications(data.notifications);
        },
        error: function() {
            $('#notificationsContainer').html('<div class="alert alert-danger">Bildirimler yüklenemedi</div>');
        }
    });
}

// Bildirimleri göster
function displayNotifications(notifications) {
    const container = $('#notificationsContainer');
    container.empty();
    
    if (!notifications || notifications.length === 0) {
        container.html('<div class="alert alert-info">Henüz bildirim yok</div>');
        return;
    }
    
    notifications.forEach(notif => {
        const typeClass = {
            'return_reminder': 'alert-warning',
            'overdue': 'alert-danger',
            'success': 'alert-success',
            'info': 'alert-info'
        }[notif.type] || 'alert-secondary';
        
        const readClass = notif.is_read ? 'opacity-75' : '';
        
        container.append(`
            <div class="alert ${typeClass} ${readClass}" data-id="${notif.id}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <strong>${notif.message}</strong><br>
                        <small class="text-muted">${formatDate(notif.created_date)}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary" onclick="markNotificationRead(${notif.id})">
                        ${notif.is_read ? '✓' : 'Okundu işaretle'}
                    </button>
                </div>
            </div>
        `);
    });
}

// Bildirimi okundu işaretle
function markNotificationRead(id) {
    $.ajax({
        url: `/api/notifications/${id}/read`,
        method: 'POST',
        success: function() {
            $(`[data-id="${id}"]`).addClass('opacity-75').find('button').text('✓');
            checkNotifications(); // Badge'i güncelle
        }
    });
}

// ==================== YARDIMCI FONKSİYONLAR ====================

// Pagination güncelle - Basit versiyon
function updatePagination(total, current, containerId) {
    const totalPages = Math.ceil(total / 20);
    const container = $(`#${containerId}`);
    
    if (totalPages <= 1) {
        container.empty();
        return;
    }
    
    let html = '<nav><ul class="pagination pagination-sm justify-content-center">';
    
    // Önceki
    if (current > 1) {
        html += `<li class="page-item"><a class="page-link" href="#" onclick="loadCurrentPageData(${current - 1})">«</a></li>`;
    }
    
    // Sayfa numaraları (sadece yakın olanlar)
    const start = Math.max(1, current - 2);
    const end = Math.min(totalPages, current + 2);
    
    for (let i = start; i <= end; i++) {
        const active = i === current ? 'active' : '';
        html += `<li class="page-item ${active}"><a class="page-link" href="#" onclick="loadCurrentPageData(${i})">${i}</a></li>`;
    }
    
    // Sonraki
    if (current < totalPages) {
        html += `<li class="page-item"><a class="page-link" href="#" onclick="loadCurrentPageData(${current + 1})">»</a></li>`;
    }
    
    html += '</ul></nav>';
    container.html(html);
}

// ==================== EVENT LİSTENER'LAR ====================

$(document).ready(function() {
    console.log('📚 Kitap ve İşlem fonksiyonları yüklendi');
    
    // Arama event'leri
    $('#bookSearch').on('input', searchBooks);
    $('#memberSearch').on('input', searchMembers);
    
    // Form submit event'leri - ESC ile çıkış destekli
    $('#addBookForm').on('submit', function(e) {
        e.preventDefault();
        addBook();
    });
    
    $('#editBookForm').on('submit', function(e) {
        e.preventDefault();
        updateBook();
    });
    
    $('#borrowForm').on('submit', function(e) {
        e.preventDefault();
        borrowBook();
    });
    
    $('#returnForm').on('submit', function(e) {
        e.preventDefault();
        returnBook();
    });
    
    // Modal ESC ile kapanma desteği
    $('.modal').on('hidden.bs.modal', function() {
        $(this).find('form')[0]?.reset();
    });

    $('#addMemberForm').on('submit', function(e) {
        e.preventDefault();
        addMember();
    });
    
    $('#editMemberForm').on('submit', function(e) {
        e.preventDefault();
        updateMember();
    });
});

console.log('📖 Kitap ve İşlem Yönetimi Hazır - Optimize Edilmiş');

function renewTransaction(id) {
    if (confirm('Bu işlemin süresini uzatmak istiyor musunuz?')) {
        $.ajax({
            url: `/api/transactions/${id}/renew`,
            method: 'POST',
            success: function(resp) {
                showToast(resp.message || 'Süre uzatıldı', 'success');
                loadTransactions(currentTransactionPage);
            },
            error: function(xhr) {
                showToast(xhr.responseJSON?.message || 'Süre uzatılamadı', 'error');
            }
        });
    }
}
