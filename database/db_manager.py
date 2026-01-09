"""
数据库管理模块
提供数据库操作的高级接口
"""

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database.models import Base, User, AttendanceRecord
from datetime import datetime
from typing import List, Optional
import numpy as np


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_url='sqlite:///attendance.db'):
        """
        初始化数据库管理器
        
        Args:
            db_url: 数据库连接URL
        """
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    # 用户相关操作
    
    def add_user(self, name: str, employee_id: str, face_encoding: np.ndarray, 
                 photo_path: str = None) -> Optional[User]:
        """
        添加新用户
        
        Args:
            name: 用户姓名
            employee_id: 学号/工号
            face_encoding: 人脸特征编码
            photo_path: 照片路径
            
        Returns:
            用户对象，如果失败返回None
        """
        try:
            # 检查是否已存在
            existing_user = self.get_user_by_employee_id(employee_id)
            if existing_user:
                print(f"用户 {employee_id} 已存在")
                return None
            
            user = User(
                name=name,
                employee_id=employee_id,
                photo_path=photo_path
            )
            user.set_encoding(face_encoding)
            
            self.session.add(user)
            self.session.commit()
            
            return user
        except Exception as e:
            self.session.rollback()
            print(f"添加用户失败: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return self.session.query(User).filter_by(id=user_id).first()
    
    def get_user_by_employee_id(self, employee_id: str) -> Optional[User]:
        """根据学号/工号获取用户"""
        return self.session.query(User).filter_by(employee_id=employee_id).first()
    
    def get_all_users(self) -> List[User]:
        """获取所有用户"""
        return self.session.query(User).all()
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            **kwargs: 要更新的字段
            
        Returns:
            是否成功
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"更新用户失败: {e}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            self.session.delete(user)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"删除用户失败: {e}")
            return False
    
    # 签到记录相关操作
    
    def add_attendance_record(self, user_id: int, user_name: str, employee_id: str,
                             checkin_photo: str = None, confidence: float = None,
                             location: str = None) -> Optional[AttendanceRecord]:
        """
        添加签到记录
        
        Args:
            user_id: 用户ID
            user_name: 用户姓名
            employee_id: 学号/工号
            checkin_photo: 签到照片路径
            confidence: 识别置信度
            location: 签到地点
            
        Returns:
            签到记录对象
        """
        try:
            record = AttendanceRecord(
                user_id=user_id,
                user_name=user_name,
                employee_id=employee_id,
                checkin_photo=checkin_photo,
                confidence=confidence,
                location=location
            )
            
            self.session.add(record)
            self.session.commit()
            
            return record
        except Exception as e:
            self.session.rollback()
            print(f"添加签到记录失败: {e}")
            return None
    
    def get_attendance_records(self, user_id: int = None, limit: int = 100) -> List[AttendanceRecord]:
        """
        获取签到记录
        
        Args:
            user_id: 用户ID，如果为None则获取所有记录
            limit: 返回记录数量限制
            
        Returns:
            签到记录列表
        """
        query = self.session.query(AttendanceRecord)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        return query.order_by(desc(AttendanceRecord.checkin_time)).limit(limit).all()
    
    def get_today_attendance(self, user_id: int = None) -> List[AttendanceRecord]:
        """
        获取今天的签到记录
        
        Args:
            user_id: 用户ID，如果为None则获取所有用户
            
        Returns:
            今天的签到记录
        """
        today = datetime.now().date()
        query = self.session.query(AttendanceRecord).filter(
            AttendanceRecord.checkin_time >= datetime.combine(today, datetime.min.time())
        )
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        return query.order_by(desc(AttendanceRecord.checkin_time)).all()
    
    def close(self):
        """关闭数据库连接"""
        self.session.close()
