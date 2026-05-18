import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """기본 설정"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')

class WeatherConfig:
    """날씨 API 설정"""
    SERVICE_KEY = os.getenv('WEATHER_SERVICE_KEY')

class EmailConfig:
    """이메일 발송 설정"""
    GMAIL_USER = os.getenv('GMAIL_USER')
    GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
    TEAMS_CHANNEL_EMAIL = os.getenv('TEAMS_CHANNEL_EMAIL')

def get_config():
    """환경에 따른 설정 반환"""
    return Config
