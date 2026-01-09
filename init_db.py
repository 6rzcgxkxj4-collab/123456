"""
数据库初始化脚本
"""

from database.models import init_db

if __name__ == '__main__':
    print("初始化数据库...")
    engine = init_db('sqlite:///attendance.db')
    print("数据库初始化完成！")
    print("数据库文件：attendance.db")
