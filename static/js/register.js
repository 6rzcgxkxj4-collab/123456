// 用户注册页面JavaScript

let video = document.getElementById('video');
let canvas = document.getElementById('canvas');
let captureBtn = document.getElementById('captureBtn');
let retakeBtn = document.getElementById('retakeBtn');
let registerForm = document.getElementById('registerForm');
let photoPreview = document.getElementById('photoPreview');
let message = document.getElementById('message');
let cameraStatus = document.getElementById('cameraStatus');

let capturedImage = null;
let stream = null;

// 初始化摄像头
async function initCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480 } 
        });
        video.srcObject = stream;
        cameraStatus.textContent = '✅ 摄像头已就绪';
        cameraStatus.style.color = '#28a745';
    } catch (err) {
        console.error('摄像头访问失败:', err);
        cameraStatus.textContent = '❌ 无法访问摄像头，请检查权限设置';
        cameraStatus.style.color = '#dc3545';
    }
}

// 拍照
captureBtn.addEventListener('click', () => {
    let context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);
    
    capturedImage = canvas.toDataURL('image/jpeg');
    
    // 显示预览
    photoPreview.innerHTML = `<img src="${capturedImage}" alt="预览照片">`;
    
    // 切换按钮
    captureBtn.style.display = 'none';
    retakeBtn.style.display = 'inline-block';
    
    showMessage('照片已拍摄，请填写信息后提交', 'success');
});

// 重拍
retakeBtn.addEventListener('click', () => {
    capturedImage = null;
    photoPreview.innerHTML = '<p class="hint">请先拍照</p>';
    captureBtn.style.display = 'inline-block';
    retakeBtn.style.display = 'none';
    message.style.display = 'none';
});

// 提交注册
registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!capturedImage) {
        showMessage('请先拍照', 'error');
        return;
    }
    
    let name = document.getElementById('name').value.trim();
    let employeeId = document.getElementById('employeeId').value.trim();
    
    if (!name || !employeeId) {
        showMessage('请填写完整信息', 'error');
        return;
    }
    
    // 显示加载状态
    showMessage('正在注册，请稍候...', 'success');
    captureBtn.disabled = true;
    retakeBtn.disabled = true;
    
    try {
        let response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                employee_id: employeeId,
                image: capturedImage
            })
        });
        
        let data = await response.json();
        
        if (data.success) {
            showMessage('✅ 注册成功！', 'success');
            // 3秒后跳转到签到页面
            setTimeout(() => {
                window.location.href = '/checkin';
            }, 3000);
        } else {
            showMessage('❌ ' + data.message, 'error');
            captureBtn.disabled = false;
            retakeBtn.disabled = false;
        }
    } catch (err) {
        console.error('注册失败:', err);
        showMessage('❌ 网络错误，请重试', 'error');
        captureBtn.disabled = false;
        retakeBtn.disabled = false;
    }
});

// 显示消息
function showMessage(text, type) {
    message.textContent = text;
    message.className = 'message ' + type;
    message.style.display = 'block';
}

// 页面加载时初始化摄像头
window.addEventListener('load', initCamera);

// 页面卸载时关闭摄像头
window.addEventListener('beforeunload', () => {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
});
