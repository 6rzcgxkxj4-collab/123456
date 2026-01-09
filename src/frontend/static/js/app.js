/**
 * Face Recognition Attendance System - Frontend JavaScript
 */

// API Base URL
const API_BASE = '/api';

// Global state
let currentUserId = null;
let videoStream = null;

// DOM Elements
document.addEventListener('DOMContentLoaded', function() {
    // Initialize page navigation
    initNavigation();
    
    // Initialize video streams
    initVideoStream('video');
    initVideoStream('register-video');
    
    // Initialize event handlers
    initEventHandlers();
    
    // Load initial data
    loadUsers();
    loadUserSelect();
    
    // Set default date
    document.getElementById('record-date').valueAsDate = new Date();
});

/**
 * Initialize page navigation
 */
function initNavigation() {
    const navLinks = document.querySelectorAll('[data-page]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const pageName = this.getAttribute('data-page');
            showPage(pageName);
            
            // Update active nav link
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

/**
 * Show a specific page
 */
function showPage(pageName) {
    const pages = document.querySelectorAll('.page');
    pages.forEach(page => page.classList.remove('active'));
    
    const targetPage = document.getElementById(pageName + '-page');
    if (targetPage) {
        targetPage.classList.add('active');
    }
}

/**
 * Initialize video stream for webcam
 */
async function initVideoStream(videoId) {
    const video = document.getElementById(videoId);
    if (!video) return;
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: 'user'
            }
        });
        video.srcObject = stream;
        videoStream = stream;
    } catch (err) {
        console.error('Error accessing camera:', err);
        showToast('无法访问摄像头，请确保已授权摄像头权限。', 'error');
    }
}

/**
 * Capture image from video element
 */
function captureImage(videoId, canvasId) {
    const video = document.getElementById(videoId);
    const canvas = document.getElementById(canvasId);
    const context = canvas.getContext('2d');
    
    // Set canvas dimensions to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw video frame to canvas
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Get base64 image data
    return canvas.toDataURL('image/jpeg', 0.9);
}

/**
 * Initialize event handlers
 */
function initEventHandlers() {
    // Check-in button
    document.getElementById('check-in-btn').addEventListener('click', handleCheckIn);
    
    // Check-out button
    document.getElementById('check-out-btn').addEventListener('click', handleCheckOut);
    
    // Register form
    document.getElementById('register-form').addEventListener('submit', handleRegisterUser);
    
    // Capture face button
    document.getElementById('capture-face-btn').addEventListener('click', handleCaptureFace);
    
    // Search records button
    document.getElementById('search-records-btn').addEventListener('click', loadAttendanceRecords);
}

/**
 * Handle check-in
 */
async function handleCheckIn() {
    const imageData = captureImage('video', 'canvas');
    const resultDiv = document.getElementById('attendance-result');
    
    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/attendance/check-in`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: imageData,
                location: 'Main Office',
                device_id: 'WEB-001'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            resultDiv.className = 'alert alert-success';
            resultDiv.innerHTML = `
                <h5><i class="fas fa-check-circle me-2"></i>签到成功！</h5>
                <p>姓名: ${data.data.user.name}</p>
                <p>员工ID: ${data.data.user.employee_id}</p>
                <p>签到时间: ${formatDateTime(data.data.attendance.check_in_time)}</p>
                <p>置信度: ${(data.data.confidence * 100).toFixed(2)}%</p>
            `;
            showToast(`${data.data.user.name} 签到成功！`, 'success');
        } else {
            resultDiv.className = 'alert alert-danger';
            resultDiv.innerHTML = `<i class="fas fa-times-circle me-2"></i>${data.error}`;
            showToast(data.error, 'error');
        }
        resultDiv.classList.remove('d-none');
    } catch (err) {
        console.error('Check-in error:', err);
        showToast('签到失败，请重试。', 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Handle check-out
 */
async function handleCheckOut() {
    const imageData = captureImage('video', 'canvas');
    const resultDiv = document.getElementById('attendance-result');
    
    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/attendance/check-out`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: imageData,
                location: 'Main Office',
                device_id: 'WEB-001'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            resultDiv.className = 'alert alert-success';
            resultDiv.innerHTML = `
                <h5><i class="fas fa-check-circle me-2"></i>签退成功！</h5>
                <p>姓名: ${data.data.user.name}</p>
                <p>员工ID: ${data.data.user.employee_id}</p>
                <p>签退时间: ${formatDateTime(data.data.attendance.check_out_time)}</p>
                <p>置信度: ${(data.data.confidence * 100).toFixed(2)}%</p>
            `;
            showToast(`${data.data.user.name} 签退成功！`, 'success');
        } else {
            resultDiv.className = 'alert alert-danger';
            resultDiv.innerHTML = `<i class="fas fa-times-circle me-2"></i>${data.error}`;
            showToast(data.error, 'error');
        }
        resultDiv.classList.remove('d-none');
    } catch (err) {
        console.error('Check-out error:', err);
        showToast('签退失败，请重试。', 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Handle user registration
 */
async function handleRegisterUser(e) {
    e.preventDefault();
    
    const userData = {
        employee_id: document.getElementById('employee_id').value,
        name: document.getElementById('name').value,
        email: document.getElementById('email').value,
        department: document.getElementById('department').value
    };
    
    const resultDiv = document.getElementById('register-user-result');
    
    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            resultDiv.className = 'alert alert-success';
            resultDiv.innerHTML = `<i class="fas fa-check-circle me-2"></i>用户 ${data.data.name} 注册成功！请在右侧采集人脸。`;
            currentUserId = data.data.id;
            
            // Reload user selects
            loadUserSelect();
            loadUsers();
            
            // Reset form
            document.getElementById('register-form').reset();
            
            showToast('用户注册成功！', 'success');
        } else {
            resultDiv.className = 'alert alert-danger';
            resultDiv.innerHTML = `<i class="fas fa-times-circle me-2"></i>${data.error}`;
            showToast(data.error, 'error');
        }
        resultDiv.classList.remove('d-none');
    } catch (err) {
        console.error('Registration error:', err);
        showToast('注册失败，请重试。', 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Handle face capture
 */
async function handleCaptureFace() {
    const userId = document.getElementById('user-select').value;
    if (!userId) {
        showToast('请先选择用户。', 'error');
        return;
    }
    
    const imageData = captureImage('register-video', 'register-canvas');
    const resultDiv = document.getElementById('register-face-result');
    
    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/users/${userId}/face`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        
        const data = await response.json();
        
        if (data.success) {
            resultDiv.className = 'alert alert-success';
            resultDiv.innerHTML = `<i class="fas fa-check-circle me-2"></i>人脸采集成功！`;
            showToast('人脸采集成功！', 'success');
        } else {
            resultDiv.className = 'alert alert-danger';
            resultDiv.innerHTML = `<i class="fas fa-times-circle me-2"></i>${data.error}`;
            showToast(data.error, 'error');
        }
        resultDiv.classList.remove('d-none');
    } catch (err) {
        console.error('Face capture error:', err);
        showToast('人脸采集失败，请重试。', 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Load users for select dropdown
 */
async function loadUserSelect() {
    try {
        const response = await fetch(`${API_BASE}/users`);
        const data = await response.json();
        
        if (data.success) {
            const select = document.getElementById('user-select');
            const recordSelect = document.getElementById('record-user');
            
            // Clear existing options
            select.innerHTML = '<option value="">-- 请选择用户 --</option>';
            recordSelect.innerHTML = '<option value="">全部用户</option>';
            
            // Add user options
            data.data.forEach(user => {
                const option = `<option value="${user.id}">${user.name} (${user.employee_id})</option>`;
                select.innerHTML += option;
                recordSelect.innerHTML += option;
            });
        }
    } catch (err) {
        console.error('Error loading users:', err);
    }
}

/**
 * Load all users for user management page
 */
async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE}/users?active_only=false`);
        const data = await response.json();
        
        if (data.success) {
            const tbody = document.getElementById('users-table-body');
            tbody.innerHTML = '';
            
            data.data.forEach(user => {
                const statusBadge = user.is_active 
                    ? '<span class="badge bg-success">活跃</span>'
                    : '<span class="badge bg-danger">禁用</span>';
                
                const row = `
                    <tr>
                        <td>${user.id}</td>
                        <td>${user.employee_id}</td>
                        <td>${user.name}</td>
                        <td>${user.email || '-'}</td>
                        <td>${user.department || '-'}</td>
                        <td>${statusBadge}</td>
                        <td>${formatDateTime(user.created_at)}</td>
                        <td>
                            <button class="btn btn-sm btn-warning" onclick="toggleUserStatus(${user.id}, ${!user.is_active})">
                                ${user.is_active ? '禁用' : '启用'}
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteUser(${user.id})">
                                删除
                            </button>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
    } catch (err) {
        console.error('Error loading users:', err);
    }
}

/**
 * Load attendance records
 */
async function loadAttendanceRecords() {
    const date = document.getElementById('record-date').value;
    const userId = document.getElementById('record-user').value;
    
    let url = `${API_BASE}/attendance`;
    const params = new URLSearchParams();
    
    if (date) params.append('date', date);
    if (userId) params.append('user_id', userId);
    
    if (params.toString()) {
        url += '?' + params.toString();
    }
    
    try {
        showLoading(true);
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            const tbody = document.getElementById('records-table-body');
            tbody.innerHTML = '';
            
            if (data.data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">暂无记录</td></tr>';
                return;
            }
            
            data.data.forEach(record => {
                const confidenceClass = getConfidenceClass(record.confidence);
                const row = `
                    <tr>
                        <td>${record.id}</td>
                        <td>${record.employee_id || '-'}</td>
                        <td>${record.user_name || '-'}</td>
                        <td>${formatDateTime(record.check_in_time)}</td>
                        <td>${record.check_out_time ? formatDateTime(record.check_out_time) : '-'}</td>
                        <td class="${confidenceClass}">${record.confidence ? (record.confidence * 100).toFixed(2) + '%' : '-'}</td>
                        <td>${record.location || '-'}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
    } catch (err) {
        console.error('Error loading attendance records:', err);
    } finally {
        showLoading(false);
    }
}

/**
 * Toggle user status
 */
async function toggleUserStatus(userId, newStatus) {
    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/users/${userId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: newStatus })
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadUsers();
            loadUserSelect();
            showToast('用户状态已更新。', 'success');
        } else {
            showToast(data.error, 'error');
        }
    } catch (err) {
        console.error('Error toggling user status:', err);
        showToast('更新用户状态失败。', 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Delete user
 */
async function deleteUser(userId) {
    if (!confirm('确定要删除该用户吗？此操作不可撤销。')) {
        return;
    }
    
    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/users/${userId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadUsers();
            loadUserSelect();
            showToast('用户已删除。', 'success');
        } else {
            showToast(data.error, 'error');
        }
    } catch (err) {
        console.error('Error deleting user:', err);
        showToast('删除用户失败。', 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Format datetime string
 */
function formatDateTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * Get confidence class based on value
 */
function getConfidenceClass(confidence) {
    if (!confidence) return '';
    if (confidence >= 0.8) return 'confidence-high';
    if (confidence >= 0.6) return 'confidence-medium';
    return 'confidence-low';
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastTitle = document.getElementById('toast-title');
    const toastBody = document.getElementById('toast-body');
    
    // Remove existing classes
    toast.classList.remove('toast-success', 'toast-error', 'toast-info');
    toast.classList.add(`toast-${type}`);
    
    const titles = {
        success: '成功',
        error: '错误',
        info: '提示'
    };
    
    toastTitle.textContent = titles[type] || '通知';
    toastBody.textContent = message;
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

/**
 * Show/hide loading indicator
 */
function showLoading(show) {
    // You can implement a loading overlay here
    // For now, we'll just disable buttons
    const buttons = document.querySelectorAll('button');
    buttons.forEach(btn => btn.disabled = show);
}
