"""
Flask应用主程序
基于TensorFlow Serving的面部识别自动签到系统
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import cv2
import numpy as np
import base64
from datetime import datetime
import json

from config.config import Config
from database.db_manager import DatabaseManager
from models.face_detector import FaceDetector
from models.face_encoder import FaceEncoder

# 初始化Flask应用
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化组件
db_manager = DatabaseManager(app.config['DATABASE_URL'])
face_detector = FaceDetector(model=app.config['FACE_DETECTION_MODEL'])
face_encoder = FaceEncoder()


def base64_to_image(base64_string):
    """将base64字符串转换为OpenCV图像"""
    try:
        # 验证输入
        if not base64_string or not isinstance(base64_string, str):
            return None
        
        # 移除data:image/...;base64,前缀
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # 限制大小 (最大10MB)
        if len(base64_string) > 10 * 1024 * 1024:
            print("图像数据过大")
            return None
        
        # 解码
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return image
    except Exception as e:
        print(f"Base64转图像失败: {e}")
        return None


def save_image(image, prefix='photo'):
    """保存图像到上传目录"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{prefix}_{timestamp}.jpg"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    cv2.imwrite(filepath, image)
    return filename


# 路由定义

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/register')
def register_page():
    """注册页面"""
    return render_template('register.html')


@app.route('/checkin')
def checkin_page():
    """签到页面"""
    return render_template('checkin.html')


@app.route('/records')
def records_page():
    """记录页面"""
    return render_template('records.html')


# API路由

@app.route('/api/register', methods=['POST'])
def api_register():
    """用户注册API"""
    try:
        data = request.get_json()
        name = data.get('name')
        employee_id = data.get('employee_id')
        image_data = data.get('image')
        
        if not all([name, employee_id, image_data]):
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        # 转换图像
        image = base64_to_image(image_data)
        if image is None:
            return jsonify({'success': False, 'message': '图像数据无效'}), 400
        
        # 检测人脸
        face_locations = face_detector.detect_faces(image)
        if len(face_locations) == 0:
            return jsonify({'success': False, 'message': '未检测到人脸'}), 400
        
        if len(face_locations) > 1:
            return jsonify({'success': False, 'message': '检测到多个人脸，请确保只有一人'}), 400
        
        # 获取人脸编码
        face_encoding = face_encoder.encode_face(image, face_locations[0])
        if face_encoding is None:
            return jsonify({'success': False, 'message': '人脸特征提取失败'}), 400
        
        # 保存照片
        photo_filename = save_image(image, f'user_{employee_id}')
        
        # 添加到数据库
        user = db_manager.add_user(
            name=name,
            employee_id=employee_id,
            face_encoding=face_encoding,
            photo_path=photo_filename
        )
        
        if user is None:
            return jsonify({'success': False, 'message': '用户已存在或添加失败'}), 400
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'user': user.to_dict()
        })
        
    except Exception as e:
        print(f"注册错误: {e}")
        return jsonify({'success': False, 'message': f'服务器错误: {str(e)}'}), 500


@app.route('/api/checkin', methods=['POST'])
def api_checkin():
    """签到API"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        location = data.get('location', '未知')
        
        if not image_data:
            return jsonify({'success': False, 'message': '缺少图像数据'}), 400
        
        # 转换图像
        image = base64_to_image(image_data)
        if image is None:
            return jsonify({'success': False, 'message': '图像数据无效'}), 400
        
        # 检测人脸
        face_locations = face_detector.detect_faces(image)
        if len(face_locations) == 0:
            return jsonify({'success': False, 'message': '未检测到人脸'}), 400
        
        # 获取人脸编码
        face_encoding = face_encoder.encode_face(image, face_locations[0])
        if face_encoding is None:
            return jsonify({'success': False, 'message': '人脸特征提取失败'}), 400
        
        # 获取所有已注册用户
        users = db_manager.get_all_users()
        if len(users) == 0:
            return jsonify({'success': False, 'message': '系统中没有已注册用户'}), 400
        
        # 提取所有用户的人脸编码
        known_encodings = [user.get_encoding() for user in users]
        
        # 查找最佳匹配
        best_match_index, distance = face_detector.find_best_match(
            known_encodings,
            face_encoding,
            tolerance=app.config['FACE_RECOGNITION_TOLERANCE']
        )
        
        if best_match_index is None:
            return jsonify({'success': False, 'message': '未识别到已注册用户'}), 400
        
        # 获取匹配的用户
        matched_user = users[best_match_index]
        confidence = 1.0 - distance  # 置信度 = 1 - 距离
        
        # 保存签到照片
        checkin_photo = save_image(image, f'checkin_{matched_user.employee_id}')
        
        # 记录签到
        record = db_manager.add_attendance_record(
            user_id=matched_user.id,
            user_name=matched_user.name,
            employee_id=matched_user.employee_id,
            checkin_photo=checkin_photo,
            confidence=float(confidence),
            location=location
        )
        
        if record is None:
            return jsonify({'success': False, 'message': '签到记录失败'}), 500
        
        return jsonify({
            'success': True,
            'message': f'签到成功！欢迎 {matched_user.name}',
            'user': matched_user.to_dict(),
            'record': record.to_dict(),
            'confidence': float(confidence)
        })
        
    except Exception as e:
        print(f"签到错误: {e}")
        return jsonify({'success': False, 'message': f'服务器错误: {str(e)}'}), 500


@app.route('/api/users', methods=['GET'])
def api_get_users():
    """获取所有用户"""
    try:
        users = db_manager.get_all_users()
        return jsonify({
            'success': True,
            'users': [user.to_dict() for user in users]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/records', methods=['GET'])
def api_get_records():
    """获取签到记录"""
    try:
        user_id = request.args.get('user_id', type=int)
        limit = request.args.get('limit', 100, type=int)
        
        records = db_manager.get_attendance_records(user_id=user_id, limit=limit)
        
        return jsonify({
            'success': True,
            'records': [record.to_dict() for record in records]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/records/today', methods=['GET'])
def api_get_today_records():
    """获取今天的签到记录"""
    try:
        user_id = request.args.get('user_id', type=int)
        records = db_manager.get_today_attendance(user_id=user_id)
        
        return jsonify({
            'success': True,
            'records': [record.to_dict() for record in records]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """访问上传的文件"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    print("=" * 50)
    print("面部识别自动签到系统启动中...")
    print(f"访问地址: http://localhost:{app.config['PORT']}")
    print("=" * 50)
    
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )
