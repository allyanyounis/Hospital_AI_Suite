# -*- coding: utf-8 -*-
"""
Quick Care Connect & AI Healthcare Assistance - Main Application Entry Point
This is the main entry point for running the Flask application.
"""
from app import create_app, db, socketio
from app.models import User, Doctor, Patient, Admin, Appointment, MedicalHistory, Question, Answer, Blog, Disease, Refund, PlatformRevenue, DoctorPayoutRequest, VideoCallRecording

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'User': User,
        'Doctor': Doctor,
        'Patient': Patient,
        'Admin': Admin,
        'Appointment': Appointment,
        'MedicalHistory': MedicalHistory,
        'Question': Question,
        'Answer': Answer,
        'Blog': Blog,
        'Disease': Disease,
        'Refund': Refund,
        'PlatformRevenue': PlatformRevenue,
        'DoctorPayoutRequest': DoctorPayoutRequest,
        'VideoCallRecording': VideoCallRecording,
    }

if __name__ == '__main__':
    import os
    bind_all = os.environ.get('BIND_ALL_INTERFACES', 'false').lower() in ('1', 'true', 'yes')
    host = os.environ.get('FLASK_HOST', '0.0.0.0' if bind_all else '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() in ('1', 'true', 'yes')
    
    ssl_cert = os.environ.get('SSL_CERT', 'localhost+3.pem')
    ssl_key = os.environ.get('SSL_KEY', 'localhost+3-key.pem')
    ssl_context = (ssl_cert, ssl_key) if (os.path.exists(ssl_cert) and os.path.exists(ssl_key)) else None

    socketio.run(
        app,
        debug=debug_mode,
        host=host,
        port=port,
        ssl_context=ssl_context,
        allow_unsafe_werkzeug=True
    )
