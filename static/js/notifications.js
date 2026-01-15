/**
 * Notification System - JavaScript for handling in-app notifications
 */

document.addEventListener('DOMContentLoaded', function () {
    // Only run if notification elements exist
    const notifCount = document.getElementById('notif-count');
    const notifList = document.getElementById('notification-list');
    const markAllBtn = document.getElementById('mark-all-read-btn');

    if (!notifCount || !notifList) return;

    // Fetch notification count on load
    fetchNotificationCount();

    // Refresh count every 30 seconds
    setInterval(fetchNotificationCount, 30000);

    // Load notifications when dropdown is opened
    const notifDropdown = document.getElementById('notifDropdown');
    if (notifDropdown) {
        notifDropdown.addEventListener('click', function () {
            fetchNotifications();
        });
    }

    // Mark all as read
    if (markAllBtn) {
        markAllBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            markAllRead();
        });
    }

    /**
     * Fetch unread notification count
     */
    function fetchNotificationCount() {
        fetch('/notifications/api/count')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateBadge(data.count);
                }
            })
            .catch(error => console.error('Error fetching notification count:', error));
    }

    /**
     * Fetch notification list
     */
    function fetchNotifications() {
        fetch('/notifications/api/list')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    renderNotifications(data.notifications);
                }
            })
            .catch(error => console.error('Error fetching notifications:', error));
    }

    /**
     * Update the badge count
     */
    function updateBadge(count) {
        if (count > 0) {
            notifCount.textContent = count > 99 ? '99+' : count;
            notifCount.style.display = 'inline-block';
        } else {
            notifCount.style.display = 'none';
        }
    }

    /**
     * Render notifications in dropdown
     */
    function renderNotifications(notifications) {
        if (!notifications || notifications.length === 0) {
            notifList.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-bell-slash"></i> ไม่มีการแจ้งเตือน
                </div>
            `;
            return;
        }

        let html = '';
        notifications.forEach(n => {
            const icon = getNotificationIcon(n.type);
            const unreadClass = n.is_read ? '' : 'notification-unread';
            const time = formatTime(n.created_at);

            html += `
                <a href="/notifications/click/${n.id}" 
                   class="dropdown-item notification-item ${unreadClass} py-2 px-3 border-bottom">
                    <div class="d-flex align-items-start">
                        <div class="me-2">${icon}</div>
                        <div class="flex-grow-1" style="min-width: 0;">
                            <div class="d-flex justify-content-between">
                                <strong class="small text-truncate">${n.title}</strong>
                                ${n.is_read ? '' : '<span class="badge bg-primary ms-1" style="font-size: 0.65rem;">ใหม่</span>'}
                            </div>
                            ${n.message ? `<p class="mb-0 text-muted small text-truncate">${n.message}</p>` : ''}
                            <small class="text-muted">${time}</small>
                        </div>
                    </div>
                </a>
            `;
        });

        notifList.innerHTML = html;
    }

    /**
     * Get icon based on notification type
     */
    function getNotificationIcon(type) {
        switch (type) {
            case 'danger':
                return '<i class="bi bi-exclamation-circle-fill text-danger"></i>';
            case 'warning':
                return '<i class="bi bi-exclamation-triangle-fill text-warning"></i>';
            case 'success':
                return '<i class="bi bi-check-circle-fill text-success"></i>';
            default:
                return '<i class="bi bi-info-circle-fill text-info"></i>';
        }
    }

    /**
     * Format timestamp to relative time
     */
    function formatTime(timestamp) {
        if (!timestamp) return '';

        const date = new Date(timestamp);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000); // seconds

        if (diff < 60) return 'เมื่อสักครู่';
        if (diff < 3600) return Math.floor(diff / 60) + ' นาทีที่แล้ว';
        if (diff < 86400) return Math.floor(diff / 3600) + ' ชั่วโมงที่แล้ว';
        if (diff < 604800) return Math.floor(diff / 86400) + ' วันที่แล้ว';

        return date.toLocaleDateString('th-TH', { day: 'numeric', month: 'short' });
    }

    /**
     * Mark all notifications as read
     */
    function markAllRead() {
        fetch('/notifications/api/read-all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateBadge(0);
                    // Remove unread styling from all items
                    document.querySelectorAll('.notification-unread').forEach(el => {
                        el.classList.remove('notification-unread');
                    });
                    // Remove "new" badges
                    document.querySelectorAll('.notification-item .badge.bg-primary').forEach(el => {
                        el.remove();
                    });
                }
            })
            .catch(error => console.error('Error marking all as read:', error));
    }
});
