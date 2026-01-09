// 签到页面JavaScript

let video = document.getElementById('video');
let canvas = document.getElementById('canvas');
let checkinBtn = document.getElementById('checkinBtn');
let status = document.getElementById('status');
let result = document.getElementById('result');
let userInfo = document.getElementById('userInfo');
let todayRecordsList = document.getElementById('todayRecordsList');

let stream = null;

// 初始化摄像头
async function initCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480 } 
        });
        video.srcObject = stream;
        status.textContent = '✅ 摄像头已就绪，点击按钮开始签到';
        status.style.color = '#28a745';
    } catch (err) {
        console.error('摄像头访问失败:', err);
        status.textContent = '❌ 无法访问摄像头，请检查权限设置';
        status.style.color = '#dc3545';
    }
}

// 签到
checkinBtn.addEventListener('click', async () => {
    // 拍照
    let context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);
    
    let imageData = canvas.toDataURL('image/jpeg');
    
    // 显示处理状态
    status.textContent = '正在识别...';
    status.style.color = '#007bff';
    checkinBtn.disabled = true;
    
    try {
        let response = await fetch('/api/checkin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image: imageData,
                location: '未知'
            })
        });
        
        let data = await response.json();
        
        if (data.success) {
            // 显示成功消息
            status.textContent = '✅ ' + data.message;
            status.style.color = '#28a745';
            
            // 显示用户信息
            document.getElementById('userName').textContent = data.user.name;
            document.getElementById('userEmployeeId').textContent = data.user.employee_id;
            document.getElementById('checkinTime').textContent = data.record.checkin_time;
            document.getElementById('confidence').textContent = (data.confidence * 100).toFixed(2) + '%';
            
            userInfo.style.display = 'block';
            result.style.display = 'none';
            
            // 刷新今日记录
            loadTodayRecords();
        } else {
            status.textContent = '❌ ' + data.message;
            status.style.color = '#dc3545';
            result.innerHTML = `<p style="color: #dc3545;">${data.message}</p>`;
            userInfo.style.display = 'none';
        }
    } catch (err) {
        console.error('签到失败:', err);
        status.textContent = '❌ 网络错误，请重试';
        status.style.color = '#dc3545';
    } finally {
        checkinBtn.disabled = false;
    }
});

// 加载今日签到记录
async function loadTodayRecords() {
    try {
        let response = await fetch('/api/records/today');
        let data = await response.json();
        
        if (data.success && data.records.length > 0) {
            let html = '<table class="records-table"><thead><tr>';
            html += '<th>姓名</th><th>学号/工号</th><th>签到时间</th><th>置信度</th>';
            html += '</tr></thead><tbody>';
            
            data.records.forEach(record => {
                html += '<tr>';
                html += `<td>${record.user_name}</td>`;
                html += `<td>${record.employee_id}</td>`;
                html += `<td>${record.checkin_time}</td>`;
                html += `<td>${(record.confidence * 100).toFixed(2)}%</td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            todayRecordsList.innerHTML = html;
        } else {
            todayRecordsList.innerHTML = '<p class="hint">暂无今日签到记录</p>';
        }
    } catch (err) {
        console.error('加载记录失败:', err);
        todayRecordsList.innerHTML = '<p class="hint">加载失败</p>';
    }
}

// 页面加载时初始化
window.addEventListener('load', () => {
    initCamera();
    loadTodayRecords();
});

// 页面卸载时关闭摄像头
window.addEventListener('beforeunload', () => {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
});
