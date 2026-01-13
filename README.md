# 基于TensorFlow Serving的深度学习面部识别自动签到系统

面部识别自动签到系统 - 毕业设计项目

## 项目简介

本项目是一个基于深度学习的面部识别自动签到系统，使用TensorFlow Serving进行模型部署，实现高效、准确的人脸识别签到功能。系统采用Python Flask作为后端框架，支持Web界面操作，可用于企业考勤、学校签到等场景。

## 功能特性

- 🔍 **人脸检测**: 基于深度学习的人脸检测算法，准确识别摄像头画面中的人脸
- 🧠 **人脸识别**: 使用128维面部特征向量进行人脸比对，识别精度高
- ⚡ **TensorFlow Serving**: 支持TensorFlow Serving模型部署，实现高性能推理
- 📊 **签到统计**: 实时统计签到数据，生成考勤报表
- 👥 **用户管理**: 完整的用户注册、管理功能
- 🔐 **权限控制**: 管理员和普通用户权限分离

## 技术栈

- **后端框架**: Python Flask
- **深度学习**: TensorFlow, face_recognition
- **模型部署**: TensorFlow Serving (REST/gRPC)
- **数据库**: SQLite (可扩展为PostgreSQL/MySQL)
- **前端**: HTML5, CSS3, JavaScript
- **容器化**: Docker, Docker Compose

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Web 浏览器                              │
│                   (签到界面/管理后台)                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask Web 服务器                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ 认证API  │  │ 用户API  │  │ 签到API  │  │ 统计API  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐         ┌─────────────────────────────────┐
│    SQLite DB    │         │      TensorFlow Serving         │
│  (用户/签到记录)  │         │    (人脸识别模型推理)            │
└─────────────────┘         └─────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.8+
- Docker (可选，用于TensorFlow Serving)
- 摄像头 (用于实时人脸识别)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd 123456
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **运行应用**
```bash
python run.py
```

5. **访问系统**
- 首页: http://localhost:5000
- 签到页面: http://localhost:5000/checkin
- 管理后台: http://localhost:5000/admin

### 默认管理员账号
- 员工ID: `admin`
- 密码: `admin123`

## Docker 部署

### 使用 Docker Compose (推荐)

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 单独部署 TensorFlow Serving

```bash
# 导出模型
python scripts/export_model.py --output ./models/face_recognition

# 启动 TensorFlow Serving
bash scripts/start_tf_serving.sh
```

## API 文档

### 认证接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/logout` | POST | 用户登出 |
| `/api/auth/me` | GET | 获取当前用户信息 |

### 用户管理接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/users/` | GET | 获取用户列表 (管理员) |
| `/api/users/` | POST | 创建用户 (管理员) |
| `/api/users/<id>` | GET | 获取用户详情 |
| `/api/users/<id>` | PUT | 更新用户信息 |
| `/api/users/<id>` | DELETE | 删除用户 (管理员) |
| `/api/users/<id>/register-face` | POST | 注册人脸 |

### 签到接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/checkin/face` | POST | 人脸识别签到 |
| `/api/checkin/manual` | POST | 手动签到 (管理员) |
| `/api/checkin/records` | GET | 获取签到记录 |
| `/api/checkin/statistics` | GET | 获取签到统计 |
| `/api/checkin/today` | GET | 获取今日签到 |

## 项目结构

```
123456/
├── config/                 # 配置文件
│   ├── __init__.py
│   └── config.py          # 应用配置
├── src/                   # 源代码
│   ├── api/              # API 路由
│   │   ├── auth.py       # 认证接口
│   │   ├── users.py      # 用户管理接口
│   │   └── checkin.py    # 签到接口
│   ├── models/           # 数据模型
│   │   └── database.py   # 数据库模型
│   ├── utils/            # 工具函数
│   │   ├── face_recognition_utils.py  # 人脸识别工具
│   │   └── tf_serving_client.py       # TF Serving 客户端
│   ├── static/           # 静态文件
│   │   ├── css/
│   │   └── js/
│   ├── templates/        # HTML 模板
│   └── app.py           # Flask 应用工厂
├── scripts/              # 脚本文件
│   ├── export_model.py   # 模型导出脚本
│   └── start_tf_serving.sh
├── tests/                # 测试文件
├── models/               # 模型文件目录
├── data/                 # 数据目录
│   └── faces/           # 人脸图片
├── requirements.txt      # Python 依赖
├── docker-compose.yml    # Docker Compose 配置
├── Dockerfile           # Docker 镜像定义
└── run.py               # 应用入口
```

## 测试

```bash
# 运行所有测试
pytest

# 运行测试并显示覆盖率
pytest --cov=src tests/

# 运行特定测试
pytest tests/test_app.py -v
```

## 配置说明

环境变量配置 (可创建 `.env` 文件):

```env
# Flask 配置
FLASK_CONFIG=development
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
SECRET_KEY=your-secret-key

# 数据库配置
DATABASE_URL=sqlite:///data/checkin.db

# TensorFlow Serving 配置
TF_SERVING_HOST=localhost
TF_SERVING_REST_PORT=8501
TF_SERVING_GRPC_PORT=8500
MODEL_NAME=face_recognition

# 人脸识别配置
FACE_DETECTION_MODEL=hog
FACE_RECOGNITION_TOLERANCE=0.6
CHECK_IN_COOLDOWN=60
```

## 使用说明

### 1. 注册人脸

1. 登录管理后台 (http://localhost:5000/admin)
2. 进入"用户管理"标签
3. 点击用户对应的"注册人脸"按钮
4. 使用摄像头拍照或上传照片
5. 系统自动检测并保存人脸特征

### 2. 签到流程

1. 访问签到页面 (http://localhost:5000/checkin)
2. 启动摄像头
3. 面对摄像头，点击"拍照签到"
4. 系统自动识别并记录签到

### 3. 查看签到记录

1. 登录管理后台
2. 进入"签到记录"标签
3. 可按日期筛选查看

## 注意事项

1. **安全性**: 生产环境请修改 `SECRET_KEY` 和默认管理员密码
2. **性能**: 大规模部署建议使用 PostgreSQL/MySQL 替代 SQLite
3. **GPU 加速**: 使用 `FACE_DETECTION_MODEL=cnn` 需要 GPU 支持
4. **隐私保护**: 请确保人脸数据的安全存储和传输

## License

MIT License

## 作者

毕业设计项目
