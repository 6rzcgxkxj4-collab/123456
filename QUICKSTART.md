# 快速开始指南

## 安装步骤

### 1. 克隆仓库

```bash
git clone <repository_url>
cd 123456
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

**注意**: 首次安装face_recognition可能需要较长时间，因为需要下载预训练模型。

### 4. 初始化数据库

```bash
python init_db.py
```

### 5. 启动应用

```bash
python app.py
```

应用将在 http://localhost:5000 启动

## 使用流程

### 第一步：注册用户

1. 在浏览器中打开 http://localhost:5000
2. 点击"用户注册"或直接访问 http://localhost:5000/register
3. 允许浏览器访问摄像头
4. 输入姓名和学号/工号
5. 点击"拍照"按钮采集人脸
6. 点击"提交注册"完成注册

### 第二步：进行签到

1. 访问 http://localhost:5000/checkin
2. 面对摄像头
3. 点击"开始签到"按钮
4. 系统会自动识别人脸并完成签到

### 第三步：查看记录

访问 http://localhost:5000/records 查看签到记录

## 系统配置

可以通过修改 `config/config.py` 来调整系统参数：

- `FACE_DETECTION_MODEL`: 人脸检测模型，'hog'(快速)或'cnn'(精确)
- `FACE_RECOGNITION_TOLERANCE`: 识别阈值，默认0.6，越小越严格
- `USE_TF_SERVING`: 是否使用TensorFlow Serving

## 使用TensorFlow Serving（可选）

如果要使用TensorFlow Serving进行模型部署：

### 1. 导出模型

```bash
python models/model_exporter.py
```

### 2. 使用Docker启动TF Serving

```bash
cd tf_serving
docker-compose up -d
```

### 3. 修改配置

在 `config/config.py` 中设置：
```python
USE_TF_SERVING = True
TF_SERVING_URL = 'http://localhost:8501'
```

## 故障排除

### 摄像头无法访问

- 确保浏览器有摄像头访问权限
- 使用HTTPS或localhost访问
- 检查摄像头是否被其他程序占用

### 人脸识别失败

- 确保光线充足
- 正面面对摄像头
- 保持面部清晰，不要有遮挡
- 降低FACE_RECOGNITION_TOLERANCE值以提高识别准确度

### 安装face_recognition失败

face_recognition依赖dlib，需要C++编译器：

**Windows**: 安装Visual Studio Build Tools
**Linux**: `sudo apt-get install build-essential cmake`
**Mac**: `xcode-select --install`

或者使用预编译的wheel包：
```bash
pip install dlib-19.22.0-cp39-cp39-win_amd64.whl  # Windows示例
```

## 系统要求

- Python 3.7+
- 摄像头设备
- 支持WebRTC的现代浏览器（Chrome, Firefox, Edge等）
- 至少2GB内存
- 推荐使用GPU（可选，用于CNN模型）

## 技术栈

- **后端**: Flask
- **数据库**: SQLite + SQLAlchemy
- **人脸识别**: face_recognition + dlib
- **深度学习**: TensorFlow 2.x
- **模型服务**: TensorFlow Serving
- **前端**: HTML5 + JavaScript + CSS3

## 项目文档

更多详细信息请参阅：
- [README.md](README.md) - 项目概述
- [config/config.py](config/config.py) - 配置说明
- [models/](models/) - 模型代码
- [database/](database/) - 数据库模型

## 许可证

MIT License
