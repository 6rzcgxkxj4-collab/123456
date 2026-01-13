"""
Main entry point for the Facial Recognition Check-in System.
"""
import os
from src.app import create_app

app = create_app(os.environ.get('FLASK_CONFIG', 'development'))

if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║      面部识别自动签到系统 (Face Recognition Check-in)         ║
    ║──────────────────────────────────────────────────────────────║
    ║  Server running at: http://{host}:{port}                      
    ║  Debug mode: {debug}                                          
    ║                                                              ║
    ║  默认管理员账号: admin / admin123                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host=host, port=port, debug=debug)
