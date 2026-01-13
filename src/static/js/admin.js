/**
 * Admin Page JavaScript
 * Handles admin authentication, user management, and check-in records
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const loginSection = document.getElementById('loginSection');
    const loginForm = document.getElementById('loginForm');
    const loginError = document.getElementById('loginError');
    const adminDashboard = document.getElementById('adminDashboard');
    const currentUserSpan = document.getElementById('currentUser');
    const logoutBtn = document.getElementById('logoutBtn');
    
    // Tab elements
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // User modal
    const userModal = document.getElementById('userModal');
    const userForm = document.getElementById('userForm');
    const addUserBtn = document.getElementById('addUserBtn');
    
    // Face modal
    const faceModal = document.getElementById('faceModal');
    
    // State
    let currentUser = null;
    let currentPage = {
        users: 1,
        records: 1
    };
    let faceUserId = null;
    let faceStream = null;
    
    // Check if already logged in
    checkAuth();
    
    // Login form handler
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const employeeId = document.getElementById('employeeId').value;
        const password = document.getElementById('password').value;
        
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    employee_id: employeeId,
                    password: password
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                currentUser = data.user;
                showDashboard();
            } else {
                showError(data.error || '登录失败');
            }
        } catch (error) {
            showError('网络错误: ' + error.message);
        }
    });
    
    // Logout handler
    logoutBtn.addEventListener('click', async function() {
        try {
            await fetch('/api/auth/logout', { method: 'POST' });
        } catch (error) {
            console.error('Logout error:', error);
        }
        currentUser = null;
        showLogin();
    });
    
    // Tab switching
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            
            tabBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === tabId + 'Tab') {
                    content.classList.add('active');
                }
            });
            
            // Load tab data
            if (tabId === 'statistics') loadStatistics();
            if (tabId === 'users') loadUsers();
            if (tabId === 'records') loadRecords();
        });
    });
    
    // User modal handlers
    addUserBtn.addEventListener('click', function() {
        document.getElementById('modalTitle').textContent = '添加用户';
        userForm.reset();
        document.getElementById('userId').value = '';
        document.getElementById('userEmployeeId').disabled = false;
        userModal.style.display = 'flex';
    });
    
    document.querySelectorAll('.close-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            userModal.style.display = 'none';
            faceModal.style.display = 'none';
            stopFaceCamera();
        });
    });
    
    // Close modal on outside click
    window.addEventListener('click', function(e) {
        if (e.target === userModal) {
            userModal.style.display = 'none';
        }
        if (e.target === faceModal) {
            faceModal.style.display = 'none';
            stopFaceCamera();
        }
    });
    
    // User form submit
    userForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const userId = document.getElementById('userId').value;
        const userData = {
            employee_id: document.getElementById('userEmployeeId').value,
            name: document.getElementById('userName').value,
            email: document.getElementById('userEmail').value,
            department: document.getElementById('userDepartment').value,
            is_admin: document.getElementById('userIsAdmin').checked
        };
        
        try {
            let response;
            if (userId) {
                response = await fetch(`/api/users/${userId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(userData)
                });
            } else {
                response = await fetch('/api/users/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(userData)
                });
            }
            
            const data = await response.json();
            
            if (response.ok) {
                userModal.style.display = 'none';
                loadUsers();
            } else {
                alert(data.error || '操作失败');
            }
        } catch (error) {
            alert('网络错误: ' + error.message);
        }
    });
    
    // User search
    document.getElementById('userSearch').addEventListener('input', debounce(function() {
        currentPage.users = 1;
        loadUsers();
    }, 300));
    
    // Record filter
    document.getElementById('filterRecordsBtn').addEventListener('click', function() {
        currentPage.records = 1;
        loadRecords();
    });
    
    // Face registration handlers
    const faceVideo = document.getElementById('faceVideo');
    const faceCanvas = document.getElementById('faceCanvas');
    const startFaceCameraBtn = document.getElementById('startFaceCamera');
    const captureFaceBtn = document.getElementById('captureFaceBtn');
    const faceImageUpload = document.getElementById('faceImageUpload');
    const uploadFaceBtn = document.getElementById('uploadFaceBtn');
    
    startFaceCameraBtn.addEventListener('click', async function() {
        try {
            faceStream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
                audio: false
            });
            faceVideo.srcObject = faceStream;
            startFaceCameraBtn.disabled = true;
            captureFaceBtn.disabled = false;
        } catch (error) {
            alert('无法访问摄像头: ' + error.message);
        }
    });
    
    captureFaceBtn.addEventListener('click', async function() {
        faceCanvas.width = faceVideo.videoWidth;
        faceCanvas.height = faceVideo.videoHeight;
        faceCanvas.getContext('2d').drawImage(faceVideo, 0, 0);
        
        faceCanvas.toBlob(async function(blob) {
            await registerFace(blob);
        }, 'image/jpeg', 0.9);
    });
    
    faceImageUpload.addEventListener('change', function() {
        uploadFaceBtn.disabled = !this.files.length;
    });
    
    uploadFaceBtn.addEventListener('click', async function() {
        const file = faceImageUpload.files[0];
        if (file) {
            await registerFace(file);
        }
    });
    
    async function registerFace(imageBlob) {
        const formData = new FormData();
        formData.append('image', imageBlob);
        
        try {
            const response = await fetch(`/api/users/${faceUserId}/register-face`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                alert('人脸注册成功');
                faceModal.style.display = 'none';
                stopFaceCamera();
                loadUsers();
            } else {
                alert(data.error || '人脸注册失败');
            }
        } catch (error) {
            alert('网络错误: ' + error.message);
        }
    }
    
    function stopFaceCamera() {
        if (faceStream) {
            faceStream.getTracks().forEach(track => track.stop());
            faceStream = null;
        }
        faceVideo.srcObject = null;
        startFaceCameraBtn.disabled = false;
        captureFaceBtn.disabled = true;
        faceImageUpload.value = '';
        uploadFaceBtn.disabled = true;
    }
    
    // Helper functions
    async function checkAuth() {
        try {
            const response = await fetch('/api/auth/me');
            if (response.ok) {
                const data = await response.json();
                currentUser = data.user;
                if (currentUser.is_admin) {
                    showDashboard();
                } else {
                    showLogin();
                    showError('需要管理员权限');
                }
            } else {
                showLogin();
            }
        } catch (error) {
            showLogin();
        }
    }
    
    function showLogin() {
        loginSection.style.display = 'block';
        adminDashboard.style.display = 'none';
        loginError.style.display = 'none';
        loginForm.reset();
    }
    
    function showDashboard() {
        loginSection.style.display = 'none';
        adminDashboard.style.display = 'block';
        currentUserSpan.textContent = `欢迎, ${currentUser.name}`;
        loadStatistics();
    }
    
    function showError(message) {
        loginError.textContent = message;
        loginError.style.display = 'block';
    }
    
    async function loadStatistics() {
        try {
            const response = await fetch('/api/checkin/statistics');
            if (response.ok) {
                const data = await response.json();
                document.getElementById('totalCheckins').textContent = data.total_checkins;
                document.getElementById('uniqueUsers').textContent = data.unique_users_checked_in;
                document.getElementById('totalUsers').textContent = data.total_active_users;
                document.getElementById('attendanceRate').textContent = data.attendance_rate + '%';
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
        }
    }
    
    async function loadUsers() {
        const search = document.getElementById('userSearch').value;
        const params = new URLSearchParams({
            page: currentPage.users,
            per_page: 20,
            search: search
        });
        
        try {
            const response = await fetch('/api/users/?' + params);
            if (response.ok) {
                const data = await response.json();
                renderUsersTable(data.users);
                renderPagination('usersPagination', data.pages, currentPage.users, (page) => {
                    currentPage.users = page;
                    loadUsers();
                });
            }
        } catch (error) {
            console.error('Error loading users:', error);
        }
    }
    
    function renderUsersTable(users) {
        const tbody = document.getElementById('usersTableBody');
        tbody.innerHTML = '';
        
        users.forEach(user => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${escapeHtml(user.employee_id)}</td>
                <td>${escapeHtml(user.name)}</td>
                <td>${escapeHtml(user.department || '-')}</td>
                <td>
                    <span class="badge ${user.has_face_registered ? 'badge-success' : 'badge-warning'}">
                        ${user.has_face_registered ? '已注册' : '未注册'}
                    </span>
                </td>
                <td>
                    <span class="badge ${user.is_active ? 'badge-success' : 'badge-danger'}">
                        ${user.is_active ? '启用' : '禁用'}
                    </span>
                </td>
                <td class="actions">
                    <button class="btn btn-secondary" onclick="editUser(${user.id})">编辑</button>
                    <button class="btn btn-primary" onclick="registerFaceForUser(${user.id}, '${escapeHtml(user.name)}')">
                        ${user.has_face_registered ? '更新人脸' : '注册人脸'}
                    </button>
                    ${!user.is_admin ? `<button class="btn btn-danger" onclick="deleteUser(${user.id})">删除</button>` : ''}
                </td>
            `;
            tbody.appendChild(tr);
        });
    }
    
    async function loadRecords() {
        const dateFrom = document.getElementById('dateFrom').value;
        const dateTo = document.getElementById('dateTo').value;
        const params = new URLSearchParams({
            page: currentPage.records,
            per_page: 50
        });
        
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        
        try {
            const response = await fetch('/api/checkin/records?' + params);
            if (response.ok) {
                const data = await response.json();
                renderRecordsTable(data.records);
                renderPagination('recordsPagination', data.pages, currentPage.records, (page) => {
                    currentPage.records = page;
                    loadRecords();
                });
            }
        } catch (error) {
            console.error('Error loading records:', error);
        }
    }
    
    function renderRecordsTable(records) {
        const tbody = document.getElementById('recordsTableBody');
        tbody.innerHTML = '';
        
        records.forEach(record => {
            const tr = document.createElement('tr');
            const time = new Date(record.check_in_time).toLocaleString('zh-CN');
            tr.innerHTML = `
                <td>${time}</td>
                <td>${escapeHtml(record.employee_id || '-')}</td>
                <td>${escapeHtml(record.user_name || '-')}</td>
                <td>${record.check_in_type === 'face' ? '人脸识别' : '手动签到'}</td>
                <td>${record.confidence ? (record.confidence * 100).toFixed(1) + '%' : '-'}</td>
            `;
            tbody.appendChild(tr);
        });
    }
    
    function renderPagination(containerId, totalPages, currentPageNum, onPageClick) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';
        
        if (totalPages <= 1) return;
        
        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement('button');
            btn.textContent = i;
            btn.className = i === currentPageNum ? 'active' : '';
            btn.addEventListener('click', () => onPageClick(i));
            container.appendChild(btn);
        }
    }
    
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    function escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Global functions for inline handlers
    window.editUser = async function(userId) {
        try {
            const response = await fetch(`/api/users/${userId}`);
            if (response.ok) {
                const data = await response.json();
                const user = data.user;
                
                document.getElementById('modalTitle').textContent = '编辑用户';
                document.getElementById('userId').value = user.id;
                document.getElementById('userEmployeeId').value = user.employee_id;
                document.getElementById('userEmployeeId').disabled = true;
                document.getElementById('userName').value = user.name;
                document.getElementById('userEmail').value = user.email || '';
                document.getElementById('userDepartment').value = user.department || '';
                document.getElementById('userIsAdmin').checked = user.is_admin;
                
                userModal.style.display = 'flex';
            }
        } catch (error) {
            alert('加载用户信息失败');
        }
    };
    
    window.deleteUser = async function(userId) {
        if (!confirm('确定要删除此用户吗？')) return;
        
        try {
            const response = await fetch(`/api/users/${userId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                loadUsers();
            } else {
                const data = await response.json();
                alert(data.error || '删除失败');
            }
        } catch (error) {
            alert('网络错误: ' + error.message);
        }
    };
    
    window.registerFaceForUser = function(userId, userName) {
        faceUserId = userId;
        document.getElementById('faceModalUser').textContent = `为 ${userName} 注册人脸`;
        stopFaceCamera();
        faceModal.style.display = 'flex';
    };
});
