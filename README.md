# 基于TensorFlow Serving的深度学习模型的面部识别自动签到系统

## 项目简介

本项目是一个基于深度学习的人脸识别自动签到系统，采用TensorFlow Serving作为模型服务，实现高效、准确的人脸识别功能。系统支持员工注册、人脸采集、自动签到/签退以及考勤记录管理等功能。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (Web Browser)                        │
│    HTML5 + CSS3 + JavaScript + Bootstrap 5                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Nginx (反向代理)                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask Backend (REST API)                      │
│    - 用户管理                                                      │
│    - 人脸注册                                                      │
│    - 签到签退                                                      │
│    - 考勤统计                                                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────────┐
│     SQLite Database      │    │    TensorFlow Serving        │
│  - 用户信息               │    │    - FaceNet 模型             │
│  - 人脸编码               │    │    - 人脸特征提取             │
│  - 考勤记录               │    │    - 相似度计算               │
└──────────────────────────┘    └──────────────────────────────┘
```

## 功能特性

### 核心功能
- ✅ **用户注册管理**: 添加、编辑、删除员工信息
- ✅ **人脸采集**: 通过摄像头采集员工人脸图像
- ✅ **人脸识别签到**: 自动识别人脸并记录签到时间
- ✅ **人脸识别签退**: 自动识别人脸并记录签退时间
- ✅ **考勤记录查询**: 按日期、员工查询考勤记录
- ✅ **考勤统计**: 统计考勤率、平均工作时长等

### 技术特点
- 🚀 **深度学习模型**: 基于FaceNet架构的人脸识别模型
- 🔧 **TensorFlow Serving**: 高性能模型服务，支持模型热更新
- 🐳 **容器化部署**: Docker Compose一键部署
- 🔌 **RESTful API**: 标准化接口，易于集成
- 📱 **响应式设计**: 支持PC和移动端访问

## 项目结构

```
├── config/                    # 配置文件
│   ├── __init__.py
│   └── config.py              # 系统配置
├── docker/                    # Docker配置
│   ├── docker-compose.yml     # Docker Compose配置
│   ├── Dockerfile.backend     # 后端Dockerfile
│   ├── Dockerfile.tf-serving  # TensorFlow Serving Dockerfile
│   └── nginx.conf             # Nginx配置
├── docs/                      # 文档目录
├── models/                    # 模型文件
│   └── models.config          # TensorFlow Serving模型配置
├── scripts/                   # 脚本
│   └── prepare_model.py       # 模型准备脚本
├── src/                       # 源代码
│   ├── backend/               # 后端代码
│   │   ├── __init__.py
│   │   ├── app.py             # Flask应用主入口
│   │   ├── attendance_service.py  # 考勤服务
│   │   ├── db_service.py      # 数据库服务
│   │   ├── tf_serving_client.py   # TensorFlow Serving客户端
│   │   └── user_service.py    # 用户服务
│   ├── frontend/              # 前端代码
│   │   ├── static/            # 静态资源
│   │   │   ├── css/style.css
│   │   │   └── js/app.js
│   │   └── templates/         # HTML模板
│   │       └── index.html
│   ├── models/                # 数据模型
│   │   ├── __init__.py
│   │   └── database.py        # 数据库模型
│   └── utils/                 # 工具函数
│       ├── __init__.py
│       └── face_utils.py      # 人脸处理工具
├── tests/                     # 测试代码
│   ├── __init__.py
│   └── test_system.py         # 系统测试
├── requirements.txt           # Python依赖
└── README.md                  # 项目说明
```

## 快速开始

### 环境要求

- Python 3.9+
- Docker & Docker Compose
- 支持WebRTC的现代浏览器

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/your-repo/face-recognition-attendance.git
cd face-recognition-attendance
```

2. **安装Python依赖**
```bash
pip install -r requirements.txt
```

3. **准备模型**
```bash
python scripts/prepare_model.py --output-dir models/facenet --version 1
```

4. **使用Docker Compose启动**
```bash
cd docker
docker-compose up -d
```

5. **访问系统**
```
http://localhost:80
```

### 本地开发

1. **启动TensorFlow Serving**
```bash
docker run -p 8501:8501 \
  --mount type=bind,source=$(pwd)/models/facenet,target=/models/facenet \
  -e MODEL_NAME=facenet \
  -t tensorflow/serving
```

2. **启动后端服务**
```bash
python -m src.backend.app
```

3. **访问系统**
```
http://localhost:5000
```

## API文档

### 健康检查
```
GET /api/health
```

### 用户管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/users | 获取所有用户 |
| GET | /api/users/{id} | 获取指定用户 |
| POST | /api/users | 创建用户 |
| PUT | /api/users/{id} | 更新用户 |
| DELETE | /api/users/{id} | 删除用户 |

### 人脸管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/users/{id}/face | 注册人脸 |
| POST | /api/face/recognize | 人脸识别 |

### 考勤管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/attendance/check-in | 签到 |
| POST | /api/attendance/check-out | 签退 |
| GET | /api/attendance | 查询考勤记录 |
| GET | /api/attendance/statistics | 考勤统计 |

## 配置说明

主要配置项（可通过环境变量覆盖）：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| TF_SERVING_HOST | localhost | TensorFlow Serving主机地址 |
| TF_SERVING_PORT | 8501 | TensorFlow Serving端口 |
| DATABASE_URI | sqlite:///attendance.db | 数据库连接URI |
| FACE_RECOGNITION_THRESHOLD | 0.6 | 人脸识别阈值 |
| SERVER_PORT | 5000 | 后端服务端口 |

## 技术栈

### 后端
- Python 3.9
- Flask 2.x
- SQLAlchemy
- OpenCV
- NumPy

### 前端
- HTML5
- CSS3
- JavaScript
- Bootstrap 5
- Font Awesome

### 深度学习
- TensorFlow Serving 2.x
- FaceNet (InceptionResNetV2)

### 部署
- Docker
- Docker Compose
- Nginx

## 测试

运行测试：
```bash
pytest tests/ -v
```

运行测试并生成覆盖率报告：
```bash
pytest tests/ -v --cov=src --cov-report=html
```

## 许可证

MIT License

## 作者

毕业设计项目
