"""
数据库模型定义
使用SQLAlchemy ORM
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment='姓名')
    employee_id = Column(String(50), unique=True, nullable=False, comment='学号/工号')
    face_encoding = Column(Text, nullable=False, comment='人脸特征编码(JSON格式)')
    photo_path = Column(String(255), comment='照片路径')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    def set_encoding(self, encoding):
        """设置人脸编码"""
        self.face_encoding = json.dumps(encoding.tolist() if hasattr(encoding, 'tolist') else encoding)
    
    def get_encoding(self):
        """获取人脸编码"""
        import numpy as np
        return np.array(json.loads(self.face_encoding))
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'employee_id': self.employee_id,
            'photo_path': self.photo_path,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class AttendanceRecord(Base):
    """签到记录表"""
    __tablename__ = 'attendance_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment='用户ID')
    user_name = Column(String(100), nullable=False, comment='用户姓名')
    employee_id = Column(String(50), nullable=False, comment='学号/工号')
    checkin_time = Column(DateTime, default=datetime.now, comment='签到时间')
    checkin_photo = Column(String(255), comment='签到照片路径')
    confidence = Column(Float, comment='识别置信度')
    location = Column(String(255), comment='签到地点')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'employee_id': self.employee_id,
            'checkin_time': self.checkin_time.strftime('%Y-%m-%d %H:%M:%S') if self.checkin_time else None,
            'checkin_photo': self.checkin_photo,
            'confidence': self.confidence,
            'location': self.location
        }


def init_db(db_url='sqlite:///attendance.db'):
    """
    初始化数据库
    
    Args:
        db_url: 数据库连接URL
    """
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """
    获取数据库会话
    
    Args:
        engine: 数据库引擎
        
    Returns:
        数据库会话
    """
    Session = sessionmaker(bind=engine)
    return Session()
