"""
系统测试脚本
测试各个模块的基本功能
"""

import sys
import numpy as np

print("=" * 60)
print("面部识别签到系统 - 模块测试")
print("=" * 60)

# 测试数据库模块
print("\n1. 测试数据库模块...")
try:
    from database.models import init_db, User, AttendanceRecord
    from database.db_manager import DatabaseManager
    
    # 初始化测试数据库
    db = DatabaseManager('sqlite:///test_attendance.db')
    print("   ✓ 数据库模块加载成功")
    print("   ✓ 数据库连接成功")
except Exception as e:
    print(f"   ✗ 数据库模块测试失败: {e}")
    sys.exit(1)

# 测试人脸检测模块
print("\n2. 测试人脸检测模块...")
try:
    from models.face_detector import FaceDetector
    
    detector = FaceDetector(model='hog')
    print("   ✓ 人脸检测器初始化成功")
    
    # 创建一个测试图像
    import cv2
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    locations = detector.detect_faces(test_image)
    print(f"   ✓ 人脸检测功能正常 (检测到 {len(locations)} 个人脸)")
except Exception as e:
    print(f"   ✗ 人脸检测模块测试失败: {e}")
    sys.exit(1)

# 测试人脸编码模块
print("\n3. 测试人脸编码模块...")
try:
    from models.face_encoder import FaceEncoder
    
    encoder = FaceEncoder()
    print("   ✓ 人脸编码器初始化成功")
    
    # 测试编码转换
    test_encoding = np.random.rand(128)
    encoding_list = encoder.encoding_to_list(test_encoding)
    recovered = encoder.list_to_encoding(encoding_list)
    
    if np.allclose(test_encoding, recovered):
        print("   ✓ 编码转换功能正常")
    else:
        print("   ✗ 编码转换测试失败")
except Exception as e:
    print(f"   ✗ 人脸编码模块测试失败: {e}")
    sys.exit(1)

# 测试配置模块
print("\n4. 测试配置模块...")
try:
    from config.config import Config
    
    config = Config()
    print(f"   ✓ 配置加载成功")
    print(f"   - 数据库URL: {config.DATABASE_URL}")
    print(f"   - 上传目录: {config.UPLOAD_FOLDER}")
    print(f"   - 识别阈值: {config.FACE_RECOGNITION_TOLERANCE}")
    print(f"   - 使用TF Serving: {config.USE_TF_SERVING}")
except Exception as e:
    print(f"   ✗ 配置模块测试失败: {e}")
    sys.exit(1)

# 测试Flask应用
print("\n5. 测试Flask应用...")
try:
    from app import app
    
    print("   ✓ Flask应用加载成功")
    
    # 测试应用配置
    with app.app_context():
        print(f"   - 应用名称: {app.name}")
        print(f"   - 调试模式: {app.debug}")
        
    # 测试路由
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    print(f"   ✓ 已注册 {len(routes)} 个路由")
    print(f"   - 主要路由: /, /register, /checkin, /records")
    print(f"   - API路由: /api/register, /api/checkin, /api/records")
except Exception as e:
    print(f"   ✗ Flask应用测试失败: {e}")
    sys.exit(1)

# 测试数据库操作
print("\n6. 测试数据库操作...")
try:
    # 创建测试用户
    test_encoding = np.random.rand(128)
    user = db.add_user(
        name="测试用户",
        employee_id="TEST001",
        face_encoding=test_encoding
    )
    
    if user:
        print(f"   ✓ 用户创建成功: {user.name} ({user.employee_id})")
        
        # 测试查询
        found_user = db.get_user_by_employee_id("TEST001")
        if found_user:
            print(f"   ✓ 用户查询成功")
            
            # 测试签到记录
            record = db.add_attendance_record(
                user_id=found_user.id,
                user_name=found_user.name,
                employee_id=found_user.employee_id,
                confidence=0.95
            )
            
            if record:
                print(f"   ✓ 签到记录创建成功")
                
                # 查询记录
                records = db.get_attendance_records(limit=10)
                print(f"   ✓ 签到记录查询成功 (共 {len(records)} 条)")
        else:
            print("   ✗ 用户查询失败")
    else:
        print("   ✗ 用户创建失败")
        
except Exception as e:
    print(f"   ✗ 数据库操作测试失败: {e}")
    import traceback
    traceback.print_exc()

# 清理测试数据库
print("\n7. 清理测试环境...")
try:
    import os
    db.close()
    if os.path.exists('test_attendance.db'):
        os.remove('test_attendance.db')
        print("   ✓ 测试数据库已删除")
except Exception as e:
    print(f"   ⚠ 清理失败: {e}")

print("\n" + "=" * 60)
print("所有测试完成！")
print("=" * 60)
print("\n系统已准备就绪，可以使用以下命令启动:")
print("  python init_db.py  # 初始化数据库")
print("  python app.py      # 启动应用")
print("\n访问 http://localhost:5000 开始使用")
print("=" * 60)
