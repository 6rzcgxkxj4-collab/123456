"""
Attendance service for managing attendance records.
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple

import numpy as np

from config.config import config
from src.backend.db_service import db_service
from src.backend.user_service import user_service
from src.models.database import AttendanceRecord, User

logger = logging.getLogger(__name__)


class AttendanceService:
    """Service class for attendance management operations."""
    
    def __init__(self):
        """Initialize attendance service."""
        self.db = db_service
        self.user_service = user_service
    
    def check_in(
        self,
        face_image: np.ndarray,
        location: str = None,
        device_id: str = None
    ) -> Optional[Tuple[AttendanceRecord, User, float]]:
        """
        Process check-in using face recognition.
        
        Args:
            face_image: Face image as numpy array (BGR format).
            location: Optional location information.
            device_id: Optional device identifier.
        
        Returns:
            Tuple of (AttendanceRecord, User, confidence) if successful, None otherwise.
        """
        # Recognize face
        result = self.user_service.recognize_face(face_image)
        if not result:
            logger.warning("Face not recognized for check-in")
            return None
        
        user, confidence = result
        
        # Check if user already checked in today without checking out
        session = self.db.get_session()
        try:
            today_start = datetime.combine(date.today(), datetime.min.time())
            today_end = datetime.combine(date.today(), datetime.max.time())
            
            existing_record = session.query(AttendanceRecord).filter(
                AttendanceRecord.user_id == user.id,
                AttendanceRecord.check_in_time >= today_start,
                AttendanceRecord.check_in_time <= today_end,
                AttendanceRecord.check_out_time.is_(None)
            ).first()
            
            if existing_record:
                logger.info(f"User {user.employee_id} already checked in today")
                return existing_record, user, confidence
            
            # Create new attendance record
            record = AttendanceRecord(
                user_id=user.id,
                check_in_time=datetime.utcnow(),
                confidence=confidence,
                location=location,
                device_id=device_id
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            
            logger.info(f"Check-in recorded for user {user.employee_id}")
            return record, user, confidence
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to record check-in: {e}")
            raise e
        finally:
            session.close()
    
    def check_out(
        self,
        face_image: np.ndarray,
        location: str = None,
        device_id: str = None
    ) -> Optional[Tuple[AttendanceRecord, User, float]]:
        """
        Process check-out using face recognition.
        
        Args:
            face_image: Face image as numpy array (BGR format).
            location: Optional location information.
            device_id: Optional device identifier.
        
        Returns:
            Tuple of (AttendanceRecord, User, confidence) if successful, None otherwise.
        """
        # Recognize face
        result = self.user_service.recognize_face(face_image)
        if not result:
            logger.warning("Face not recognized for check-out")
            return None
        
        user, confidence = result
        
        # Find the latest check-in record without check-out
        session = self.db.get_session()
        try:
            today_start = datetime.combine(date.today(), datetime.min.time())
            today_end = datetime.combine(date.today(), datetime.max.time())
            
            record = session.query(AttendanceRecord).filter(
                AttendanceRecord.user_id == user.id,
                AttendanceRecord.check_in_time >= today_start,
                AttendanceRecord.check_in_time <= today_end,
                AttendanceRecord.check_out_time.is_(None)
            ).order_by(AttendanceRecord.check_in_time.desc()).first()
            
            if not record:
                logger.warning(f"No check-in record found for user {user.employee_id}")
                return None
            
            # Update check-out time
            record.check_out_time = datetime.utcnow()
            session.commit()
            session.refresh(record)
            
            logger.info(f"Check-out recorded for user {user.employee_id}")
            return record, user, confidence
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to record check-out: {e}")
            raise e
        finally:
            session.close()
    
    def get_attendance_by_user(
        self,
        user_id: int,
        start_date: date = None,
        end_date: date = None
    ) -> List[AttendanceRecord]:
        """
        Get attendance records for a specific user.
        
        Args:
            user_id: User's ID.
            start_date: Start date for filtering.
            end_date: End date for filtering.
        
        Returns:
            List of AttendanceRecord objects.
        """
        session = self.db.get_session()
        try:
            query = session.query(AttendanceRecord).filter_by(user_id=user_id)
            
            if start_date:
                query = query.filter(
                    AttendanceRecord.check_in_time >= datetime.combine(start_date, datetime.min.time())
                )
            
            if end_date:
                query = query.filter(
                    AttendanceRecord.check_in_time <= datetime.combine(end_date, datetime.max.time())
                )
            
            return query.order_by(AttendanceRecord.check_in_time.desc()).all()
            
        finally:
            session.close()
    
    def get_attendance_by_date(
        self,
        target_date: date = None
    ) -> List[AttendanceRecord]:
        """
        Get all attendance records for a specific date.
        
        Args:
            target_date: Target date (defaults to today).
        
        Returns:
            List of AttendanceRecord objects.
        """
        if target_date is None:
            target_date = date.today()
        
        session = self.db.get_session()
        try:
            day_start = datetime.combine(target_date, datetime.min.time())
            day_end = datetime.combine(target_date, datetime.max.time())
            
            return session.query(AttendanceRecord).filter(
                AttendanceRecord.check_in_time >= day_start,
                AttendanceRecord.check_in_time <= day_end
            ).order_by(AttendanceRecord.check_in_time.desc()).all()
            
        finally:
            session.close()
    
    def get_attendance_statistics(
        self,
        start_date: date,
        end_date: date
    ) -> dict:
        """
        Get attendance statistics for a date range.
        
        Args:
            start_date: Start date.
            end_date: End date.
        
        Returns:
            Dictionary containing attendance statistics.
        """
        session = self.db.get_session()
        try:
            date_start = datetime.combine(start_date, datetime.min.time())
            date_end = datetime.combine(end_date, datetime.max.time())
            
            records = session.query(AttendanceRecord).filter(
                AttendanceRecord.check_in_time >= date_start,
                AttendanceRecord.check_in_time <= date_end
            ).all()
            
            total_users = session.query(User).filter_by(is_active=True).count()
            
            # Calculate statistics
            total_check_ins = len(records)
            unique_users = len(set(r.user_id for r in records))
            
            # Calculate average work duration
            work_durations = []
            for record in records:
                if record.check_out_time:
                    duration = (record.check_out_time - record.check_in_time).total_seconds()
                    work_durations.append(duration)
            
            avg_duration = sum(work_durations) / len(work_durations) if work_durations else 0
            
            return {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_check_ins": total_check_ins,
                "unique_users": unique_users,
                "total_registered_users": total_users,
                "average_work_duration_hours": round(avg_duration / 3600, 2),
                "attendance_rate": round(unique_users / total_users * 100, 2) if total_users > 0 else 0
            }
            
        finally:
            session.close()
    
    def manual_check_in(
        self,
        user_id: int,
        check_in_time: datetime = None,
        location: str = None,
        device_id: str = None
    ) -> AttendanceRecord:
        """
        Manually create a check-in record.
        
        Args:
            user_id: User's ID.
            check_in_time: Check-in time (defaults to now).
            location: Optional location information.
            device_id: Optional device identifier.
        
        Returns:
            Created AttendanceRecord object.
        """
        session = self.db.get_session()
        try:
            record = AttendanceRecord(
                user_id=user_id,
                check_in_time=check_in_time or datetime.utcnow(),
                location=location,
                device_id=device_id
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            
            return record
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def manual_check_out(
        self,
        record_id: int,
        check_out_time: datetime = None
    ) -> Optional[AttendanceRecord]:
        """
        Manually update a check-out time.
        
        Args:
            record_id: Attendance record ID.
            check_out_time: Check-out time (defaults to now).
        
        Returns:
            Updated AttendanceRecord object, or None if not found.
        """
        session = self.db.get_session()
        try:
            record = session.query(AttendanceRecord).filter_by(id=record_id).first()
            if not record:
                return None
            
            record.check_out_time = check_out_time or datetime.utcnow()
            session.commit()
            session.refresh(record)
            
            return record
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


# Create default attendance service instance
attendance_service = AttendanceService()
