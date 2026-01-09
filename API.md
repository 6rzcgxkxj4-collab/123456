# API 文档

## 基础信息

- **Base URL**: `http://localhost:5000`
- **Content-Type**: `application/json`
- **响应格式**: JSON

## API 端点

### 1. 用户注册

注册新用户并保存人脸特征。

**端点**: `POST /api/register`

**请求体**:
```json
{
  "name": "张三",
  "employee_id": "2021001",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**参数说明**:
- `name` (string, required): 用户姓名
- `employee_id` (string, required): 学号或工号，必须唯一
- `image` (string, required): Base64编码的图像数据

**成功响应**:
```json
{
  "success": true,
  "message": "注册成功",
  "user": {
    "id": 1,
    "name": "张三",
    "employee_id": "2021001",
    "photo_path": "user_2021001_20240109_120000.jpg",
    "created_at": "2024-01-09 12:00:00"
  }
}
```

**错误响应**:
```json
{
  "success": false,
  "message": "未检测到人脸"
}
```

**可能的错误信息**:
- "缺少必要参数"
- "图像数据无效"
- "未检测到人脸"
- "检测到多个人脸，请确保只有一人"
- "人脸特征提取失败"
- "用户已存在或添加失败"

---

### 2. 人脸识别签到

通过人脸识别进行签到。

**端点**: `POST /api/checkin`

**请求体**:
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "location": "教室A101"
}
```

**参数说明**:
- `image` (string, required): Base64编码的图像数据
- `location` (string, optional): 签到地点，默认"未知"

**成功响应**:
```json
{
  "success": true,
  "message": "签到成功！欢迎 张三",
  "user": {
    "id": 1,
    "name": "张三",
    "employee_id": "2021001"
  },
  "record": {
    "id": 1,
    "user_id": 1,
    "user_name": "张三",
    "employee_id": "2021001",
    "checkin_time": "2024-01-09 12:30:00",
    "confidence": 0.92,
    "location": "教室A101"
  },
  "confidence": 0.92
}
```

**错误响应**:
```json
{
  "success": false,
  "message": "未识别到已注册用户"
}
```

**可能的错误信息**:
- "缺少图像数据"
- "图像数据无效"
- "未检测到人脸"
- "人脸特征提取失败"
- "系统中没有已注册用户"
- "未识别到已注册用户"

---

### 3. 获取所有用户

获取系统中所有已注册的用户列表。

**端点**: `GET /api/users`

**成功响应**:
```json
{
  "success": true,
  "users": [
    {
      "id": 1,
      "name": "张三",
      "employee_id": "2021001",
      "photo_path": "user_2021001_20240109_120000.jpg",
      "created_at": "2024-01-09 12:00:00"
    },
    {
      "id": 2,
      "name": "李四",
      "employee_id": "2021002",
      "photo_path": "user_2021002_20240109_120100.jpg",
      "created_at": "2024-01-09 12:01:00"
    }
  ]
}
```

---

### 4. 获取签到记录

获取签到记录列表。

**端点**: `GET /api/records`

**查询参数**:
- `user_id` (integer, optional): 用户ID，用于筛选特定用户的记录
- `limit` (integer, optional): 返回记录数量限制，默认100

**示例**:
- 获取所有记录: `/api/records`
- 获取特定用户的记录: `/api/records?user_id=1`
- 限制返回数量: `/api/records?limit=50`

**成功响应**:
```json
{
  "success": true,
  "records": [
    {
      "id": 1,
      "user_id": 1,
      "user_name": "张三",
      "employee_id": "2021001",
      "checkin_time": "2024-01-09 12:30:00",
      "checkin_photo": "checkin_2021001_20240109_123000.jpg",
      "confidence": 0.92,
      "location": "教室A101"
    }
  ]
}
```

---

### 5. 获取今日签到记录

获取当天的签到记录。

**端点**: `GET /api/records/today`

**查询参数**:
- `user_id` (integer, optional): 用户ID，用于筛选特定用户的记录

**成功响应**:
```json
{
  "success": true,
  "records": [
    {
      "id": 1,
      "user_id": 1,
      "user_name": "张三",
      "employee_id": "2021001",
      "checkin_time": "2024-01-09 12:30:00",
      "confidence": 0.92,
      "location": "教室A101"
    }
  ]
}
```

---

## 静态文件访问

### 访问上传的文件

**端点**: `GET /uploads/<filename>`

**示例**: `/uploads/user_2021001_20240109_120000.jpg`

---

## 错误代码

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

---

## 使用示例

### JavaScript (Fetch API)

```javascript
// 注册用户
async function registerUser(name, employeeId, imageData) {
  const response = await fetch('/api/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: name,
      employee_id: employeeId,
      image: imageData
    })
  });
  
  const data = await response.json();
  return data;
}

// 签到
async function checkin(imageData, location) {
  const response = await fetch('/api/checkin', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      image: imageData,
      location: location
    })
  });
  
  const data = await response.json();
  return data;
}

// 获取记录
async function getRecords() {
  const response = await fetch('/api/records');
  const data = await response.json();
  return data;
}
```

### Python (requests)

```python
import requests
import base64

# 注册用户
def register_user(name, employee_id, image_path):
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode()
    
    response = requests.post('http://localhost:5000/api/register', json={
        'name': name,
        'employee_id': employee_id,
        'image': f'data:image/jpeg;base64,{image_data}'
    })
    
    return response.json()

# 签到
def checkin(image_path, location='未知'):
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode()
    
    response = requests.post('http://localhost:5000/api/checkin', json={
        'image': f'data:image/jpeg;base64,{image_data}',
        'location': location
    })
    
    return response.json()

# 获取记录
def get_records():
    response = requests.get('http://localhost:5000/api/records')
    return response.json()
```

---

## 注意事项

1. **图像格式**: 图像数据必须是Base64编码，建议使用JPEG格式
2. **图像大小**: 建议图像大小不超过5MB
3. **人脸要求**: 
   - 图像中必须包含清晰的正面人脸
   - 注册时确保只有一个人脸
   - 光线充足，面部清晰
4. **识别阈值**: 系统默认阈值为0.6，可在配置中调整
5. **并发请求**: 系统支持并发请求，但建议控制并发数量

---

## 技术支持

如有问题，请参考：
- [README.md](README.md)
- [QUICKSTART.md](QUICKSTART.md)
