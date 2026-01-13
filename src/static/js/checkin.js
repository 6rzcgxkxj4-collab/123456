/**
 * Check-in Page JavaScript
 * Handles camera capture and face recognition check-in
 */

document.addEventListener('DOMContentLoaded', function() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const videoOverlay = document.getElementById('video-overlay');
    const startCameraBtn = document.getElementById('startCamera');
    const stopCameraBtn = document.getElementById('stopCamera');
    const captureBtn = document.getElementById('captureBtn');
    const resultContainer = document.getElementById('result');
    const imageUpload = document.getElementById('imageUpload');
    const uploadBtn = document.getElementById('uploadBtn');
    
    let stream = null;
    
    // Start camera
    startCameraBtn.addEventListener('click', async function() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                },
                audio: false
            });
            
            video.srcObject = stream;
            videoOverlay.style.display = 'none';
            startCameraBtn.disabled = true;
            stopCameraBtn.disabled = false;
            captureBtn.disabled = false;
            
        } catch (error) {
            console.error('Error accessing camera:', error);
            showResult(false, '无法访问摄像头', error.message);
        }
    });
    
    // Stop camera
    stopCameraBtn.addEventListener('click', function() {
        stopCamera();
    });
    
    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        video.srcObject = null;
        videoOverlay.style.display = 'flex';
        startCameraBtn.disabled = false;
        stopCameraBtn.disabled = true;
        captureBtn.disabled = true;
    }
    
    // Capture photo and check-in
    captureBtn.addEventListener('click', async function() {
        if (!stream) return;
        
        captureBtn.disabled = true;
        captureBtn.textContent = '处理中...';
        
        // Capture frame from video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);
        
        // Convert to base64
        const imageData = canvas.toDataURL('image/jpeg', 0.9);
        const base64Data = imageData.split(',')[1];
        
        try {
            const response = await fetch('/api/checkin/face', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image_base64: base64Data,
                    location: 'Web Camera',
                    device_id: 'web-client'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showResult(true, data.message, `置信度: ${(data.confidence * 100).toFixed(1)}%`);
            } else {
                showResult(false, data.message || '签到失败', data.error || '');
            }
            
        } catch (error) {
            console.error('Check-in error:', error);
            showResult(false, '签到请求失败', error.message);
        }
        
        captureBtn.disabled = false;
        captureBtn.textContent = '📸 拍照签到';
    });
    
    // File upload handling
    imageUpload.addEventListener('change', function() {
        uploadBtn.disabled = !this.files.length;
    });
    
    uploadBtn.addEventListener('click', async function() {
        const file = imageUpload.files[0];
        if (!file) return;
        
        uploadBtn.disabled = true;
        uploadBtn.textContent = '处理中...';
        
        const formData = new FormData();
        formData.append('image', file);
        
        try {
            const response = await fetch('/api/checkin/face', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                showResult(true, data.message, `置信度: ${(data.confidence * 100).toFixed(1)}%`);
            } else {
                showResult(false, data.message || '签到失败', data.error || '');
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            showResult(false, '上传失败', error.message);
        }
        
        uploadBtn.disabled = false;
        uploadBtn.textContent = '上传签到';
        imageUpload.value = '';
    });
    
    // Show result message
    function showResult(success, message, details) {
        resultContainer.style.display = 'block';
        resultContainer.className = 'result-container ' + (success ? 'success' : 'error');
        
        resultContainer.querySelector('.result-icon').textContent = success ? '✅' : '❌';
        resultContainer.querySelector('.result-message').textContent = message;
        resultContainer.querySelector('.result-details').textContent = details;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            resultContainer.style.display = 'none';
        }, 5000);
    }
});
