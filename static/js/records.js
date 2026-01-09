// 签到记录页面JavaScript

let recordsBody = document.getElementById('recordsBody');
let todayBtn = document.getElementById('todayBtn');
let allBtn = document.getElementById('allBtn');
let refreshBtn = document.getElementById('refreshBtn');
let totalRecordsElem = document.getElementById('totalRecords');
let todayRecordsElem = document.getElementById('todayRecords');
let totalUsersElem = document.getElementById('totalUsers');

let currentView = 'all'; // 'all' or 'today'

// 加载所有记录
async function loadAllRecords() {
    currentView = 'all';
    try {
        let response = await fetch('/api/records?limit=100');
        let data = await response.json();
        
        if (data.success) {
            displayRecords(data.records);
            updateStatistics();
        } else {
            recordsBody.innerHTML = '<tr><td colspan="6" class="loading">加载失败</td></tr>';
        }
    } catch (err) {
        console.error('加载记录失败:', err);
        recordsBody.innerHTML = '<tr><td colspan="6" class="loading">网络错误</td></tr>';
    }
}

// 加载今日记录
async function loadTodayRecords() {
    currentView = 'today';
    try {
        let response = await fetch('/api/records/today');
        let data = await response.json();
        
        if (data.success) {
            displayRecords(data.records);
            updateStatistics();
        } else {
            recordsBody.innerHTML = '<tr><td colspan="6" class="loading">加载失败</td></tr>';
        }
    } catch (err) {
        console.error('加载记录失败:', err);
        recordsBody.innerHTML = '<tr><td colspan="6" class="loading">网络错误</td></tr>';
    }
}

// 显示记录
function displayRecords(records) {
    if (records.length === 0) {
        recordsBody.innerHTML = '<tr><td colspan="6" class="loading">暂无记录</td></tr>';
        return;
    }
    
    let html = '';
    records.forEach((record, index) => {
        html += '<tr>';
        html += `<td>${index + 1}</td>`;
        html += `<td>${record.user_name}</td>`;
        html += `<td>${record.employee_id}</td>`;
        html += `<td>${record.checkin_time}</td>`;
        html += `<td>${record.confidence ? (record.confidence * 100).toFixed(2) + '%' : 'N/A'}</td>`;
        html += `<td>${record.location || '未知'}</td>`;
        html += '</tr>';
    });
    
    recordsBody.innerHTML = html;
}

// 更新统计信息
async function updateStatistics() {
    try {
        // 获取所有记录
        let allResponse = await fetch('/api/records?limit=1000');
        let allData = await allResponse.json();
        
        // 获取今日记录
        let todayResponse = await fetch('/api/records/today');
        let todayData = await todayResponse.json();
        
        // 获取用户数
        let usersResponse = await fetch('/api/users');
        let usersData = await usersResponse.json();
        
        if (allData.success) {
            totalRecordsElem.textContent = allData.records.length;
        }
        
        if (todayData.success) {
            todayRecordsElem.textContent = todayData.records.length;
        }
        
        if (usersData.success) {
            totalUsersElem.textContent = usersData.users.length;
        }
    } catch (err) {
        console.error('更新统计信息失败:', err);
    }
}

// 按钮事件
todayBtn.addEventListener('click', () => {
    todayBtn.classList.add('btn-primary');
    todayBtn.classList.remove('btn-secondary');
    allBtn.classList.add('btn-secondary');
    allBtn.classList.remove('btn-primary');
    loadTodayRecords();
});

allBtn.addEventListener('click', () => {
    allBtn.classList.add('btn-primary');
    allBtn.classList.remove('btn-secondary');
    todayBtn.classList.add('btn-secondary');
    todayBtn.classList.remove('btn-primary');
    loadAllRecords();
});

refreshBtn.addEventListener('click', () => {
    if (currentView === 'all') {
        loadAllRecords();
    } else {
        loadTodayRecords();
    }
});

// 页面加载时加载所有记录
window.addEventListener('load', () => {
    loadAllRecords();
});
