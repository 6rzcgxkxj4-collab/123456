# 基于TensorFlow Serving的面部识别自动签到系统

## 项目简介

本项目是一个基于深度学习的面部识别自动签到系统，使用TensorFlow Serving部署模型，实现了用户注册、人脸识别和自动签到功能。

## 系统架构

- **前端**: HTML/JavaScript，实现用户界面和摄像头调用
- **后端**: Flask Web服务器，提供REST API
- **数据库**: SQLite，存储用户信息和签到记录
- **AI模型**: 使用face_recognition库进行人脸检测和特征提取
- **模型部署**: TensorFlow Serving用于模型推理服务

## 主要功能

1. **用户注册**: 通过摄像头采集人脸照片，提取特征向量并存储
2. **人脸识别签到**: 实时识别人脸并自动记录签到信息
3. **签到记录查询**: 查看历史签到记录
4. **用户管理**: 查看和管理已注册用户

## 项目结构

```
.
├── app.py                      # Flask应用主程序
├── models/                     # 模型相关代码
│   ├── face_detector.py       # 人脸检测模块
│   ├── face_encoder.py        # 人脸编码模块
│   └── model_exporter.py      # TF Serving模型导出
├── database/                   # 数据库模块
│   ├── models.py              # 数据库模型
│   └── db_manager.py          # 数据库管理
├── api/                        # API路由
│   ├── register.py            # 注册接口
│   ├── checkin.py             # 签到接口
│   └── records.py             # 记录查询接口
├── static/                     # 静态文件
│   ├── css/                   # 样式文件
│   ├── js/                    # JavaScript文件
│   └── images/                # 图片资源
├── templates/                  # HTML模板
│   ├── index.html             # 主页
│   ├── register.html          # 注册页面
│   ├── checkin.html           # 签到页面
│   └── records.html           # 记录页面
├── config/                     # 配置文件
│   └── config.py              # 应用配置
├── tf_serving/                 # TensorFlow Serving配置
│   ├── Dockerfile             # Docker配置
│   └── model_config.config    # 模型配置
└── requirements.txt           # Python依赖
```

## 安装说明

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python init_db.py
```

### 3. 启动应用

```bash
python app.py
```

应用将在 http://localhost:5000 启动

## 使用说明

### 注册新用户

1. 访问 http://localhost:5000/register
2. 输入姓名和学号/工号
3. 点击"拍照"按钮采集人脸照片
4. 点击"注册"完成注册

### 签到

1. 访问 http://localhost:5000/checkin
2. 面对摄像头，系统自动识别人脸
3. 识别成功后自动记录签到信息

### 查看记录

访问 http://localhost:5000/records 查看所有签到记录

## TensorFlow Serving部署（可选）

如需使用TensorFlow Serving进行模型部署：

```bash
# 导出模型
python models/model_exporter.py

# 启动TensorFlow Serving（使用Docker）
cd tf_serving
docker-compose up -d
```

## 技术特点

- 使用dlib库的HOG特征检测器进行人脸检测
- 采用深度学习模型提取128维人脸特征向量
- 使用欧氏距离进行人脸匹配
- 支持TensorFlow Serving高性能模型推理
- Web界面友好，支持实时摄像头预览

## 系统要求

- Python 3.7+
- OpenCV
- TensorFlow 2.x
- 摄像头设备

## 注意事项

1. 首次运行需要下载face_recognition的预训练模型
2. 确保摄像头权限已开启
3. 建议在光线良好的环境下使用
4. 注册时需要正面清晰的人脸照片

## 许可证

MIT License
