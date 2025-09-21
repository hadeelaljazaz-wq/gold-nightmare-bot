#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gold Nightmare Bot - Fixed & Enhanced with Permanent License System
بوت تحليل الذهب الاحترافي - مُحسن ومُصلح مع نظام المفاتيح الثابت
Version: 7.0 Professional Fixed
Author: odai - Gold Nightmare School
"""

import logging
import asyncio
import base64
import io
import json
import aiohttp
import secrets
import string
from datetime import datetime, timedelta, date, timezone
from collections import defaultdict
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import os
from dotenv import load_dotenv
import pytz
from functools import wraps
import pickle
import aiofiles
import asyncpg
from urllib.parse import urlparse

# Telegram imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.constants import ChatAction, ParseMode

# AI and Image Processing
import anthropic
from PIL import Image
import numpy as np

# Optional Technical Analysis (graceful fallback if not installed)
try:
    import talib
    import yfinance as yf
    from scipy import stats
    ADVANCED_ANALYSIS_AVAILABLE = True
except ImportError:
    ADVANCED_ANALYSIS_AVAILABLE = False
    print("⚠️ Advanced analysis libraries not found. Basic analysis will be used.")

# Load environment variables
load_dotenv()

# ==================== Fixed Performance Configuration ====================
class PerformanceConfig:
    # تحسينات الأداء المُصلحة
    CLAUDE_TIMEOUT = 180  # تقليل timeout
    DATABASE_TIMEOUT = 5   # تقليل database timeout
    HTTP_TIMEOUT = 10      # timeout HTTP
    CACHE_TTL = 300        # 5 دقائق cache
    MAX_RETRIES = 2        # محاولات إعادة
    CONNECTION_POOL_SIZE = 3  # تقليل pool size
    TELEGRAM_TIMEOUT = 5   # timeout تيليجرام

# ==================== Pre-generated License Keys (Fixed Static 40 Keys) ====================
PERMANENT_LICENSE_KEYS = {
    "GOLD-X1A2-B3C4-D5E6": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-F7G8-H9I0-J1K2": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-L3M4-N5O6-P7Q8": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-R9S0-T1U2-V3W4": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-X5Y6-Z7A8-B9C0": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-D1E2-F3G4-H5I6": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-J7K8-L9M0-N1O2": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-P3Q4-R5S6-T7U8": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-V9W0-X1Y2-Z3A4": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-B5C6-D7E8-F9G0": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-H1I2-J3K4-L5M6": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-N7O8-P9Q0-R1S2": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-T3U4-V5W6-X7Y8": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-Z9A0-B1C2-D3E4": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-F5G6-H7I8-J9K0": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-L1M2-N3O4-P5Q6": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-R7S8-T9U0-V1W2": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-X3Y4-Z5A6-B7C8": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-D9E0-F1G2-H3I4": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-J5K6-L7M8-N9O0": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-P1Q2-R3S4-T5U6": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-V7W8-X9Y0-Z1A2": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-B3C4-D5E6-F7G8": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-H9I0-J1K2-L3M4": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-N5O6-P7Q8-R9S0": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-T1U2-V3W4-X5Y6": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-Z7A8-B9C0-D1E2": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-F3G4-H5I6-J7K8": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-L9M0-N1O2-P3Q4": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-R5S6-T7U8-V9W0": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-X1Y2-Z3A4-B5C6": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-D7E8-F9G0-H1I2": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-J3K4-L5M6-N7O8": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-P9Q0-R1S2-T3U4": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-V5W6-X7Y8-Z9A0": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-B1C2-D3E4-F5G6": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-H7I8-J9K0-L1M2": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-N3O4-P5Q6-R7S8": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-T9U0-V1W2-X3Y4": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None},
    "GOLD-Z5A6-B7C8-D9E0": {"limit": 50, "used": 0, "active": True, "user_id": None, "username": None}
}

# ==================== Emojis Dictionary ====================
EMOJIS = {
    # أساسي
    'chart': '📊', 'fire': '🔥', 'gold': '💰', 'diamond': '💎', 'rocket': '🚀',
    'star': '⭐', 'crown': '👑', 'trophy': '🏆',
    
    # أسهم واتجاهات
    'up_arrow': '📈', 'down_arrow': '📉', 'right_arrow': '➡️',
    'green_circle': '🟢', 'red_circle': '🔴', 'yellow_circle': '🟡',
    
    # أدوات التداول
    'target': '🎯', 'crystal_ball': '🔮', 'scales': '⚖️', 'shield': '🛡️',
    'zap': '⚡', 'magnifier': '🔍', 'gear': '⚙️',
    
    # واجهة المستخدم
    'key': '🔑', 'phone': '📞', 'back': '🔙', 'refresh': '🔄',
    'check': '✅', 'cross': '❌', 'warning': '⚠️', 'info': '💡',
    
    # إدارية
    'admin': '👨‍💼', 'users': '👥', 'stats': '📊', 'backup': '💾', 'logs': '📝',
    
    # متنوعة
    'clock': '⏰', 'calendar': '📅', 'news': '📰', 'brain': '🧠', 'camera': '📸',
    'folder': '📁', 'progress': '📈', 'percentage': '📉', 'wave': '👋', 'gift': '🎁',
    'construction': '🚧', 'lock': '🔒', 'thumbs_up': '👍', 'people': '👥',
    'man_office': '👨‍💼', 'chart_bars': '📊', 'envelope': '📧', 'bell': '🔔',
    'house': '🏠', 'globe': '🌐', 'link': '🔗', 'signal': '📡', 'question': '❓',
    'stop': '🛑', 'play': '▶️', 'pause': '⏸️', 'prohibited': '⭕',
    'red_dot': '🔴', 'green_dot': '🟢', 'top': '🔝', 'bottom': '🔻',
    'up': '⬆️', 'down': '⬇️', 'plus': '➕'
}

def emoji(name): return EMOJIS.get(name, '')

# ==================== Configuration ====================
class Config:
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    MASTER_USER_ID = int(os.getenv("MASTER_USER_ID", "590918137"))
    
    # Claude Configuration
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514") 
    CLAUDE_MAX_TOKENS = 8000
    CLAUDE_TEMPERATURE = float(os.getenv("CLAUDE_TEMPERATURE", "0.3"))
    
    # Gold API Configuration
    GOLD_API_TOKEN = os.getenv("GOLD_API_TOKEN")
    GOLD_API_URL = "https://www.goldapi.io/api/XAU/USD"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # Cache Configuration
    PRICE_CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL", "60"))
    ANALYSIS_CACHE_TTL = int(os.getenv("ANALYSIS_CACHE_TTL", "300"))
    
    # Image Processing
    MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", "10485760"))
    MAX_IMAGE_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", "1568"))
    IMAGE_QUALITY = int(os.getenv("IMAGE_QUALITY", "85"))
    CHART_ANALYSIS_ENABLED = True
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Timezone
    TIMEZONE = pytz.timezone(os.getenv("TIMEZONE", "Asia/Amman"))
    
    # Secret Analysis Trigger
    NIGHTMARE_TRIGGER = "كابوس الذهب"

# ==================== Logging Setup ====================
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# ==================== Data Models ====================
@dataclass
class User:
    user_id: int
    username: Optional[str]
    first_name: str
    is_activated: bool = False
    activation_date: Optional[datetime] = None
    last_activity: datetime = field(default_factory=datetime.now)
    total_requests: int = 0
    total_analyses: int = 0
    subscription_tier: str = "basic"
    settings: Dict[str, Any] = field(default_factory=dict)
    license_key: Optional[str] = None
    daily_requests_used: int = 0
    last_request_date: Optional[date] = None

@dataclass
class GoldPrice:
    price: float
    timestamp: datetime
    change_24h: float = 0.0
    change_percentage: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    source: str = "goldapi"

@dataclass
class Analysis:
    id: str
    user_id: int
    timestamp: datetime
    analysis_type: str
    prompt: str
    result: str
    gold_price: float
    image_data: Optional[bytes] = None
    indicators: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LicenseKey:
    key: str
    created_date: datetime
    total_limit: int = 50
    used_total: int = 0
    is_active: bool = True
    user_id: Optional[int] = None
    username: Optional[str] = None
    notes: str = ""

class AnalysisType(Enum):
    QUICK = "QUICK"
    SCALPING = "SCALPING"  
    DETAILED = "DETAILED"
    CHART = "CHART"
    NEWS = "NEWS"
    FORECAST = "FORECAST"
    SWING = "SWING"
    REVERSAL = "REVERSAL"
    NIGHTMARE = "NIGHTMARE"

# ==================== ULTRA SIMPLE Database Manager - No Pool Issues ====================
class UltraSimpleDatabaseManager:
    def __init__(self):
        self.database_url = Config.DATABASE_URL
        self.connection_retries = 3
        self.connection_delay = 1
    
    async def get_connection(self):
        """الحصول على اتصال مباشر - بدون pool"""
        for attempt in range(self.connection_retries):
            try:
                conn = await asyncpg.connect(self.database_url)
                return conn
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < self.connection_retries - 1:
                    await asyncio.sleep(self.connection_delay)
                else:
                    raise
    
    async def initialize(self):
        """تهيئة قاعدة البيانات - بسيطة ومباشرة"""
        try:
            conn = await self.get_connection()
            try:
                await self.create_tables(conn)
                print(f"تم الاتصال بـ PostgreSQL بنجاح - بدون pool")
            finally:
                await conn.close()
        except Exception as e:
            print(f"خطأ في الاتصال بقاعدة البيانات: {e}")
            raise
    
    async def create_tables(self, conn):
        """إنشاء الجداول - مباشرة"""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT NOT NULL,
                is_activated BOOLEAN DEFAULT FALSE,
                activation_date TIMESTAMP,
                last_activity TIMESTAMP DEFAULT NOW(),
                total_requests INTEGER DEFAULT 0,
                total_analyses INTEGER DEFAULT 0,
                subscription_tier TEXT DEFAULT 'basic',
                settings JSONB DEFAULT '{}',
                license_key TEXT,
                daily_requests_used INTEGER DEFAULT 0,
                last_request_date DATE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS license_keys (
                key TEXT PRIMARY KEY,
                created_date TIMESTAMP NOT NULL,
                total_limit INTEGER DEFAULT 50,
                used_total INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                user_id BIGINT,
                username TEXT,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                analysis_type TEXT NOT NULL,
                prompt TEXT NOT NULL,
                result TEXT NOT NULL,
                gold_price DECIMAL(10,2) NOT NULL,
                image_data BYTEA,
                indicators JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # إنشاء الفهارس
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_license_key ON users(license_key)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_license_keys_user_id ON license_keys(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id)")
        
        print(f"تم إنشاء/التحقق من الجداول - مباشرة")
    
    async def save_user(self, user: User):
        """حفظ/تحديث بيانات المستخدم - مباشر"""
        try:
            conn = await self.get_connection()
            try:
                await conn.execute("""
                    INSERT INTO users (user_id, username, first_name, is_activated, activation_date, 
                                     last_activity, total_requests, total_analyses, subscription_tier, 
                                     settings, license_key, daily_requests_used, last_request_date, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        is_activated = EXCLUDED.is_activated,
                        activation_date = EXCLUDED.activation_date,
                        last_activity = EXCLUDED.last_activity,
                        total_requests = EXCLUDED.total_requests,
                        total_analyses = EXCLUDED.total_analyses,
                        subscription_tier = EXCLUDED.subscription_tier,
                        settings = EXCLUDED.settings,
                        license_key = EXCLUDED.license_key,
                        daily_requests_used = EXCLUDED.daily_requests_used,
                        last_request_date = EXCLUDED.last_request_date,
                        updated_at = NOW()
                """, user.user_id, user.username, user.first_name, user.is_activated, 
                     user.activation_date, user.last_activity, user.total_requests, 
                     user.total_analyses, user.subscription_tier, json.dumps(user.settings),
                     user.license_key, user.daily_requests_used, user.last_request_date)
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error saving user {user.user_id}: {e}")
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """جلب بيانات المستخدم - مباشر"""
        try:
            conn = await self.get_connection()
            try:
                row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
                if row:
                    return User(
                        user_id=row['user_id'],
                        username=row['username'],
                        first_name=row['first_name'],
                        is_activated=row['is_activated'],
                        activation_date=row['activation_date'],
                        last_activity=row['last_activity'],
                        total_requests=row['total_requests'],
                        total_analyses=row['total_analyses'],
                        subscription_tier=row['subscription_tier'],
                        settings=row['settings'] or {},
                        license_key=row['license_key'],
                        daily_requests_used=row['daily_requests_used'],
                        last_request_date=row['last_request_date']
                    )
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
        return None
    
    async def get_all_users(self) -> List[User]:
        """جلب جميع المستخدمين - مباشر"""
        try:
            conn = await self.get_connection()
            try:
                rows = await conn.fetch("SELECT * FROM users")
                users = []
                for row in rows:
                    users.append(User(
                        user_id=row['user_id'],
                        username=row['username'],
                        first_name=row['first_name'],
                        is_activated=row['is_activated'],
                        activation_date=row['activation_date'],
                        last_activity=row['last_activity'],
                        total_requests=row['total_requests'],
                        total_analyses=row['total_analyses'],
                        subscription_tier=row['subscription_tier'],
                        settings=row['settings'] or {},
                        license_key=row['license_key'],
                        daily_requests_used=row['daily_requests_used'],
                        last_request_date=row['last_request_date']
                    ))
                return users
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    async def save_license_key(self, license_key: LicenseKey):
        """حفظ/تحديث مفتاح التفعيل - مباشر"""
        try:
            conn = await self.get_connection()
            try:
                await conn.execute("""
                    INSERT INTO license_keys (key, created_date, total_limit, used_total, 
                                            is_active, user_id, username, notes, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                    ON CONFLICT (key) DO UPDATE SET
                        total_limit = EXCLUDED.total_limit,
                        used_total = EXCLUDED.used_total,
                        is_active = EXCLUDED.is_active,
                        user_id = EXCLUDED.user_id,
                        username = EXCLUDED.username,
                        notes = EXCLUDED.notes,
                        updated_at = NOW()
                """, license_key.key, license_key.created_date, license_key.total_limit,
                     license_key.used_total, license_key.is_active, license_key.user_id,
                     license_key.username, license_key.notes)
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error saving license key: {e}")
    
    async def get_license_key(self, key: str) -> Optional[LicenseKey]:
        """جلب مفتاح تفعيل - مباشر"""
        try:
            conn = await self.get_connection()
            try:
                row = await conn.fetchrow("SELECT * FROM license_keys WHERE key = $1", key)
                if row:
                    return LicenseKey(
                        key=row['key'],
                        created_date=row['created_date'],
                        total_limit=row['total_limit'],
                        used_total=row['used_total'],
                        is_active=row['is_active'],
                        user_id=row['user_id'],
                        username=row['username'],
                        notes=row['notes'] or ''
                    )
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error getting license key: {e}")
        return None
    
    async def get_all_license_keys(self) -> Dict[str, LicenseKey]:
        """جلب جميع مفاتيح التفعيل - مباشر"""
        try:
            conn = await self.get_connection()
            try:
                rows = await conn.fetch("SELECT * FROM license_keys")
                keys = {}
                for row in rows:
                    keys[row['key']] = LicenseKey(
                        key=row['key'],
                        created_date=row['created_date'],
                        total_limit=row['total_limit'],
                        used_total=row['used_total'],
                        is_active=row['is_active'],
                        user_id=row['user_id'],
                        username=row['username'],
                        notes=row['notes'] or ''
                    )
                return keys
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error getting all license keys: {e}")
            return {}
    
    async def save_analysis(self, analysis: Analysis):
        """حفظ تحليل - مباشر"""
        try:
            conn = await self.get_connection()
            try:
                await conn.execute("""
                    INSERT INTO analyses (id, user_id, timestamp, analysis_type, prompt, result, 
                                        gold_price, image_data, indicators)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (id) DO NOTHING
                """, analysis.id, analysis.user_id, analysis.timestamp, analysis.analysis_type,
                     analysis.prompt, analysis.result, analysis.gold_price, analysis.image_data,
                     json.dumps(analysis.indicators))
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error saving analysis: {e}")

# ==================== Ultra Simple License Manager ====================
class UltraSimpleLicenseManager:
    """إدارة المفاتيح مع اتصال مباشر - بدون pool"""
    
    def __init__(self, database_manager: UltraSimpleDatabaseManager):
        self.database = database_manager
        self.license_keys: Dict[str, Dict] = {}
        
    async def initialize(self):
        """تحميل المفاتيح وإنشاء الثابتة"""
        await self.load_keys_from_db()
        await self.ensure_static_keys()
        print(f"تم تحميل {len(self.license_keys)} مفتاح ثابت - مباشر")
    
    async def ensure_static_keys(self):
        """ضمان وجود المفاتيح الثابتة الـ 40"""
        for key, data in PERMANENT_LICENSE_KEYS.items():
            if key not in self.license_keys:
                license_key = LicenseKey(
                    key=key,
                    created_date=datetime.now(),
                    total_limit=data["limit"],
                    used_total=data["used"],
                    is_active=data["active"],
                    user_id=data["user_id"],
                    username=data["username"],
                    notes="مفتاح ثابت - لا يُحذف أبداً"
                )
                
                await self.database.save_license_key(license_key)
                
                self.license_keys[key] = {
                    "limit": data["limit"],
                    "used": data["used"],
                    "active": data["active"],
                    "user_id": data["user_id"],
                    "username": data["username"]
                }
                
                print(f"تم إنشاء المفتاح الثابت: {key}")
    
    async def load_keys_from_db(self):
        """تحميل جميع المفاتيح - مباشر"""
        try:
            db_keys = await self.database.get_all_license_keys()
            for key, license_key in db_keys.items():
                self.license_keys[key] = {
                    "limit": license_key.total_limit,
                    "used": license_key.used_total,
                    "active": license_key.is_active,
                    "user_id": license_key.user_id,
                    "username": license_key.username
                }
            print(f"تم تحميل {len(self.license_keys)} مفتاح - مباشر")
        except Exception as e:
            print(f"خطأ في تحميل المفاتيح: {e}")
            self.license_keys = {}
    
    async def validate_key(self, key: str, user_id: int) -> Tuple[bool, str]:
        """فحص صحة المفتاح"""
        if key not in self.license_keys:
            return False, f"مفتاح التفعيل غير صالح"
        
        key_data = self.license_keys[key]
        
        if not key_data["active"]:
            return False, f"مفتاح التفعيل معطل"
        
        if key_data["user_id"] and key_data["user_id"] != user_id:
            return False, f"مفتاح التفعيل مستخدم من قبل مستخدم آخر"
        
        if key_data["used"] >= key_data["limit"]:
            return False, f"انتهت صلاحية المفتاح\nتم استنفاد الـ {key_data['limit']} أسئلة\nللحصول على مفتاح جديد: @Odai_xau"
        
        return True, f"مفتاح صالح"
    
    async def use_key(self, key: str, user_id: int, username: str = None, request_type: str = "analysis", points_to_deduct: int = 1) -> Tuple[bool, str]:
        """استخدام المفتاح مع إمكانية خصم نقاط متعددة - مباشر"""
        is_valid, message = await self.validate_key(key, user_id)
        
        if not is_valid:
            return False, message
        
        key_data = self.license_keys[key]
        
        # فحص إذا كانت النقاط المتبقية كافية
        if key_data["used"] + points_to_deduct > key_data["limit"]:
            remaining = key_data["limit"] - key_data["used"]
            return False, f"نقاط غير كافية للتحليل الشامل\nتحتاج {points_to_deduct} نقاط ولديك {remaining} فقط\nللحصول على مفتاح جديد: @Odai_xau"
        
        # ربط المستخدم بالمفتاح إذا لم يكن مربوطاً
        if not key_data["user_id"]:
            key_data["user_id"] = user_id
            key_data["username"] = username
        
        # خصم النقاط المطلوبة
        key_data["used"] += points_to_deduct
        
        # حفظ التحديث - مباشر
        license_key = LicenseKey(
            key=key,
            created_date=datetime.now(),
            total_limit=key_data["limit"],
            used_total=key_data["used"],
            is_active=key_data["active"],
            user_id=key_data["user_id"],
            username=key_data["username"],
            notes="مفتاح ثابت مُحدث"
        )
        
        await self.database.save_license_key(license_key)
        
        remaining = key_data["limit"] - key_data["used"]
        
        if points_to_deduct > 1:
            # رسالة خاصة للتحليل الشامل
            if remaining == 0:
                return True, f"تم خصم {points_to_deduct} نقاط للتحليل الشامل المتقدم\nانتهت صلاحية المفتاح!\nللحصول على مفتاح جديد: @Odai_xau"
            elif remaining <= 5:
                return True, f"تم خصم {points_to_deduct} نقاط للتحليل الشامل المتقدم\nتبقى {remaining} نقاط فقط!"
            else:
                return True, f"تم خصم {points_to_deduct} نقاط للتحليل الشامل المتقدم\nالنقاط المتبقية: {remaining} من {key_data['limit']}"
        else:
            # رسالة عادية للتحليلات الأخرى
            if remaining == 0:
                return True, f"تم استخدام المفتاح بنجاح\nهذا آخر سؤال! انتهت صلاحية المفتاح\nللحصول على مفتاح جديد: @Odai_xau"
            elif remaining <= 5:
                return True, f"تم استخدام المفتاح بنجاح\nتبقى {remaining} أسئلة فقط!"
            else:
                return True, f"تم استخدام المفتاح بنجاح\nالأسئلة المتبقية: {remaining} من {key_data['limit']}"
    
    async def get_key_info(self, key: str) -> Optional[Dict]:
        """الحصول على معلومات المفتاح"""
        if key not in self.license_keys:
            return None
        
        key_data = self.license_keys[key]
        
        return {
            'key': key,
            'is_active': key_data["active"],
            'total_limit': key_data["limit"],
            'used_total': key_data["used"],
            'remaining_total': key_data["limit"] - key_data["used"],
            'user_id': key_data["user_id"],
            'username': key_data["username"],
            'created_date': '2024-08-25',
            'notes': 'مفتاح ثابت دائم'
        }
    
    async def get_all_keys_stats(self) -> Dict:
        """إحصائيات جميع المفاتيح"""
        total_keys = len(self.license_keys)
        active_keys = sum(1 for key_data in self.license_keys.values() if key_data["active"])
        used_keys = sum(1 for key_data in self.license_keys.values() if key_data["user_id"] is not None)
        expired_keys = sum(1 for key_data in self.license_keys.values() if key_data["used"] >= key_data["limit"])
        
        total_usage = sum(key_data["used"] for key_data in self.license_keys.values())
        total_available = sum(key_data["limit"] - key_data["used"] for key_data in self.license_keys.values() if key_data["used"] < key_data["limit"])
        
        return {
            'total_keys': total_keys,
            'active_keys': active_keys,
            'used_keys': used_keys,
            'unused_keys': total_keys - used_keys,
            'expired_keys': expired_keys,
            'total_usage': total_usage,
            'total_available': total_available,
            'avg_usage_per_key': total_usage / total_keys if total_keys > 0 else 0
        }

# ==================== Ultra Simple Database Manager ====================
class UltraSimpleDBManager:
    def __init__(self, database_manager: UltraSimpleDatabaseManager):
        self.database = database_manager
        self.users: Dict[int, User] = {}
        self.analyses: List[Analysis] = []
        
    async def initialize(self):
        """تحميل البيانات - مباشر"""
        try:
            users_list = await self.database.get_all_users()
            self.users = {user.user_id: user for user in users_list}
            print(f"تم تحميل {len(self.users)} مستخدم - مباشر")
        except Exception as e:
            print(f"خطأ في تحميل المستخدمين: {e}")
            self.users = {}
    
    async def add_user(self, user: User):
        """إضافة/تحديث مستخدم - مباشر"""
        self.users[user.user_id] = user
        await self.database.save_user(user)
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """جلب مستخدم - مباشر"""
        if user_id in self.users:
            return self.users[user_id]
        
        user = await self.database.get_user(user_id)
        if user:
            self.users[user_id] = user
        return user
    
    async def add_analysis(self, analysis: Analysis):
        """إضافة تحليل - مباشر"""
        self.analyses.append(analysis)
        await self.database.save_analysis(analysis)
    
    async def get_stats(self) -> Dict[str, Any]:
        """إحصائيات البوت - مباشر"""
        try:
            total_users = len(self.users)
            active_users = sum(1 for user in self.users.values() if user.is_activated)
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'activation_rate': f"{(active_users/total_users*100):.1f}%" if total_users > 0 else "0%",
                'total_analyses': len(self.analyses),
                'recent_analyses': 0
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_users': 0, 'active_users': 0, 'activation_rate': "0%",
                'total_analyses': 0, 'recent_analyses': 0
            }

# ==================== Fixed Cache System ====================
class FixedCacheManager:
    def __init__(self):
        self.price_cache: Optional[Tuple[GoldPrice, datetime]] = None
        self.analysis_cache: Dict[str, Tuple[str, datetime]] = {}
        self.image_cache: Dict[str, Tuple[str, datetime]] = {}
    
    def get_price(self) -> Optional[GoldPrice]:
        """جلب السعر من التخزين المؤقت"""
        if self.price_cache:
            price, timestamp = self.price_cache
            if datetime.now() - timestamp < timedelta(seconds=Config.PRICE_CACHE_TTL):
                return price
        return None
    
    def set_price(self, price: GoldPrice):
        """حفظ السعر في التخزين المؤقت"""
        self.price_cache = (price, datetime.now())
    
    def get_analysis(self, key: str) -> Optional[str]:
        """جلب التحليل من cache"""
        if key in self.analysis_cache:
            result, timestamp = self.analysis_cache[key]
            if datetime.now() - timestamp < timedelta(seconds=Config.ANALYSIS_CACHE_TTL):
                return result
            else:
                del self.analysis_cache[key]
        return None
    
    def set_analysis(self, key: str, result: str):
        """حفظ التحليل في cache"""
        self.analysis_cache[key] = (result, datetime.now())

# ==================== Fixed Gold Price Manager ====================
class FixedGoldPriceManager:
    def __init__(self, cache_manager: FixedCacheManager):
        self.cache = cache_manager
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """جلب جلسة HTTP - مُصلح"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=PerformanceConfig.HTTP_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def get_gold_price(self) -> Optional[GoldPrice]:
        """جلب سعر الذهب - مُصلح"""
        cached_price = self.cache.get_price()
        if cached_price:
            return cached_price
        
        try:
            price = await self._fetch_from_goldapi()
            if price:
                self.cache.set_price(price)
                return price
        except Exception as e:
            logger.warning(f"Gold API error: {e}")
        
        # استخدام سعر افتراضي
        fallback_price = GoldPrice(
            price=2650.0,
            timestamp=datetime.now(),
            change_24h=2.5,
            change_percentage=0.1,
            high_24h=2655.0,
            low_24h=2645.0,
            source="fallback"
        )
        self.cache.set_price(fallback_price)
        return fallback_price
    
    async def _fetch_from_goldapi(self) -> Optional[GoldPrice]:
        """جلب السعر من GoldAPI - مُصلح"""
        try:
            session = await self.get_session()
            headers = {
                "x-access-token": Config.GOLD_API_TOKEN,
                "Content-Type": "application/json"
            }
            
            async with session.get(Config.GOLD_API_URL, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"GoldAPI returned status {response.status}")
                    return None
                
                data = await response.json()
                price = data.get("price")
                if not price:
                    return None
                
                if price > 10000:
                    price = price / 100
                
                return GoldPrice(
                    price=round(price, 2),
                    timestamp=datetime.now(),
                    change_24h=data.get("change", 0),
                    change_percentage=data.get("change_p", 0),
                    high_24h=data.get("high_price", price),
                    low_24h=data.get("low_price", price),
                    source="goldapi"
                )
                
        except Exception as e:
            logger.error(f"GoldAPI error: {e}")
            return None
    
    async def close(self):
        """إغلاق الجلسة"""
        if self.session and not self.session.closed:
            await self.session.close()

# ==================== Fixed Claude AI Manager ====================
class FixedClaudeAIManager:
    def __init__(self, cache_manager: FixedCacheManager):
        self.client = anthropic.Anthropic(api_key=Config.CLAUDE_API_KEY)
        self.cache = cache_manager
        
    async def analyze_gold(self, 
                          prompt: str, 
                          gold_price: GoldPrice,
                          image_base64: Optional[str] = None,
                          analysis_type: AnalysisType = AnalysisType.DETAILED,
                          user_settings: Dict[str, Any] = None) -> str:
        """تحليل الذهب مع Claude - مُصلح"""
        
        # التحقق من cache للتحليل النصي
        if not image_base64:
            cache_key = f"{hash(prompt)}_{gold_price.price}_{analysis_type.value}"
            cached_result = self.cache.get_analysis(cache_key)
            if cached_result:
                return cached_result + f"\n\n{emoji('zap')} *من الذاكرة المؤقتة للسرعة*"
        
        # التحقق من التحليل الخاص السري
        is_nightmare_analysis = Config.NIGHTMARE_TRIGGER in prompt
        
        if is_nightmare_analysis:
            analysis_type = AnalysisType.NIGHTMARE
        
        system_prompt = self._build_system_prompt(analysis_type, gold_price, user_settings, bool(image_base64))
        user_prompt = self._build_user_prompt(prompt, gold_price, analysis_type, bool(image_base64))
        
        # محاولة التحليل مع retry
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                content = []
                
                if image_base64:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    })
                
                content.append({
                    "type": "text",
                    "text": user_prompt
                })
                
                message = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.messages.create,
                        model=Config.CLAUDE_MODEL,
                        max_tokens=Config.CLAUDE_MAX_TOKENS,
                        temperature=Config.CLAUDE_TEMPERATURE,
                        system=system_prompt,
                        messages=[{
                            "role": "user",
                            "content": content
                        }]
                    ),
                    timeout=PerformanceConfig.CLAUDE_TIMEOUT
                )
                
                result = message.content[0].text
                
                # حفظ في cache إذا لم تكن صورة
                if not image_base64:
                    self.cache.set_analysis(cache_key, result)
                
                return result

            except asyncio.TimeoutError:
                logger.warning(f"Claude API timeout - attempt {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    if image_base64:
                        return self._generate_chart_fallback_analysis(gold_price)
                    else:
                        return f"{emoji('warning')} انتهت مهلة التحليل. يرجى المحاولة مرة أخرى."
                
                await asyncio.sleep(2 * (attempt + 1))
                
            except Exception as e:
                error_str = str(e).lower()
                
                if "overloaded" in error_str or "529" in error_str:
                    logger.warning(f"Claude API overloaded - attempt {attempt + 1}/{max_retries}")
                    if attempt == max_retries - 1:
                        if image_base64:
                            return self._generate_chart_fallback_analysis(gold_price)
                        else:
                            return self._generate_text_fallback_analysis(gold_price, analysis_type)
                    
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
                
                elif "rate_limit" in error_str or "429" in error_str:
                    logger.warning(f"Claude API rate limited")
                    if attempt == max_retries - 1:
                        return f"{emoji('warning')} تم تجاوز الحد المسموح. حاول بعد قليل."
                    
                    await asyncio.sleep(5)
                    continue
                
                else:
                    logger.error(f"Claude API error: {e}")
                    if image_base64:
                        return self._generate_chart_fallback_analysis(gold_price)
                    else:
                        return f"{emoji('cross')} خطأ في التحليل. يرجى المحاولة مرة أخرى."
        
        # إذا فشلت جميع المحاولات
        if image_base64:
            return self._generate_chart_fallback_analysis(gold_price)
        else:
            return self._generate_text_fallback_analysis(gold_price, analysis_type)
    
    def _build_system_prompt(self, analysis_type: AnalysisType, 
                           gold_price: GoldPrice,
                           user_settings: Dict[str, Any] = None,
                           has_image: bool = False) -> str:
        """بناء prompt النظام المُحسن"""
        
        base_prompt = f"""أنت خبير عالمي في أسواق المعادن الثمينة والذهب مع خبرة +25 سنة في:
• التحليل الفني والكمي المتقدم متعدد الأطر الزمنية
• اكتشاف النماذج الفنية والإشارات المتقدمة
• إدارة المخاطر والمحافظ الاستثمارية المتخصصة
• تحليل نقاط الانعكاس ومستويات الدعم والمقاومة
• تطبيقات الذكاء الاصطناعي والتداول الخوارزمي المتقدم
• تحليل مناطق العرض والطلب والسيولة المؤسسية"""

        if has_image:
            base_prompt += f"""
• تحليل الشارت الاحترافي المتقدم
• قراءة النماذج الفنية من الشارت
• تحليل الأحجام والمؤشرات التقنية
• اكتشاف نقاط الدخول والخروج من الشارت"""

        base_prompt += f"""

{emoji('trophy')} الانتماء المؤسسي: Gold Nightmare Academy - أكاديمية التحليل المتقدم

البيانات الحية المعتمدة:
{emoji('gold')} السعر: ${gold_price.price} USD/oz
{emoji('chart')} التغيير 24h: {gold_price.change_24h:+.2f} ({gold_price.change_percentage:+.2f}%)
{emoji('up_arrow')} المدى: ${gold_price.low_24h} - ${gold_price.high_24h}
{emoji('clock')} الوقت: {gold_price.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
{emoji('signal')} المصدر: {gold_price.source}
"""
        
        # تخصيص حسب نوع التحليل
        if analysis_type == AnalysisType.NIGHTMARE:
            base_prompt += f"""

{emoji('fire')}{emoji('fire')}{emoji('fire')} **التحليل الشامل المتقدم** {emoji('fire')}{emoji('fire')}{emoji('fire')}

{emoji('target')} **التنسيق المطلوب للتحليل الشامل:**
```
{emoji('chart')} **1. تحليل الأطر الزمنية المتعددة:**
• M5, M15, H1, H4, D1 مع نسب الثقة
• إجماع الأطر الزمنية والتوصية الموحدة

{emoji('target')} **2. نقاط الدخول والخروج الدقيقة:**
• نقاط الدخول بالسنت الواحد مع الأسباب
• مستويات الخروج المتدرجة

{emoji('shield')} **3. مستويات الدعم والمقاومة:**
• الدعوم والمقاومات مع قوة كل مستوى
• المستويات النفسية المهمة

{emoji('refresh')} **4. نقاط الارتداد المحتملة:**
• مناطق الارتداد عالية الاحتمال
• إشارات التأكيد المطلوبة

{emoji('scales')} **5. مناطق العرض والطلب:**
• مناطق العرض المؤسسية
• مناطق الطلب القوية

{emoji('zap')} **6. استراتيجيات السكالبينج:**
• فرص السكالبينج (1-15 دقيقة)
• نقاط الدخول السريعة

{emoji('up_arrow')} **7. استراتيجيات السوينج:**
• فرص التداول متوسط المدى
• نقاط الدخول الاستراتيجية

{emoji('refresh')} **8. تحليل الانعكاس:**
• نقاط الانعكاس المحتملة
• مؤشرات تأكيد الانعكاس

{emoji('chart')} **9. نسب الثقة المبررة:**
• نسبة ثقة لكل تحليل مع المبررات
• احتمالية نجاح كل سيناريو

{emoji('info')} **10. توصيات إدارة المخاطر:**
• حجم الصفقة المناسب
• وقف الخسارة المثالي
```"""

        elif analysis_type == AnalysisType.QUICK:
            base_prompt += f"""

{emoji('zap')} **التحليل السريع - أقصى 150 كلمة:**

{emoji('target')} **التنسيق المطلوب:**
```
{emoji('target')} **التوصية:** [BUY/SELL/HOLD]
{emoji('up_arrow')} **السعر الحالي:** $[السعر]
{emoji('red_dot')} **السبب:** [سبب واحد قوي]

{emoji('chart')} **الأهداف:**
{emoji('trophy')} الهدف الأول: $[السعر]
{emoji('red_dot')} وقف الخسارة: $[السعر]

{emoji('clock')} **الإطار الزمني:** [المدة المتوقعة]
{emoji('fire')} **مستوى الثقة:** [نسبة مئوية]%
```"""

        base_prompt += f"""

{emoji('target')} **متطلبات التنسيق العامة:**
1. استخدام جداول وترتيبات جميلة
2. تقسيم المعلومات إلى أقسام واضحة
3. استخدام رموز تعبيرية مناسبة
4. تنسيق النتائج بطريقة احترافية
5. تقديم نسب ثقة مبررة إحصائياً
6. تحليل احترافي باللغة العربية مع مصطلحات فنية دقيقة
7. نقاط دخول وخروج بالسنت الواحد

{emoji('warning')} ملاحظة: هذا تحليل تعليمي وليس نصيحة استثمارية شخصية"""
        
        return base_prompt

    def _build_user_prompt(self, prompt: str, gold_price: GoldPrice, analysis_type: AnalysisType, has_image: bool = False) -> str:
        """بناء prompt المستخدم"""
        
        context = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{emoji('gold')} **البيانات الأساسية:**
• السعر الحالي: ${gold_price.price}
• التغيير: {gold_price.change_24h:+.2f} USD ({gold_price.change_percentage:+.2f}%)
• المدى اليومي: ${gold_price.low_24h} - ${gold_price.high_24h}
• التوقيت: {gold_price.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{emoji('target')} **طلب المستخدم:** {prompt}

{emoji('folder')} **نوع التحليل المطلوب:** {analysis_type.value}"""

        if has_image:
            context += f"""

{emoji('camera')} **تحليل الشارت المرفق:**
يرجى تحليل الشارت المرفق بالتفصيل واستخراج:
- النماذج الفنية المرئية
- مستويات الدعم والمقاومة
- الترندات والقنوات
- إشارات الدخول والخروج
- المؤشرات التقنية الظاهرة
- توقعات السعر بناءً على الشارت"""
        
        if analysis_type == AnalysisType.NIGHTMARE:
            context += f"""{emoji('fire')} **التحليل الشامل المطلوب:**

المطلوب تحليل شامل ومفصل يشمل جميع النقاط الـ 10 بتنسيق جميل وجداول منظمة مع:
• نقاط دخول وخروج بالسنت الواحد
• نسب ثقة مدروسة ومبررة
• تحليل جميع الأطر الزمنية
• استراتيجيات متنوعة للسكالبينج والسوينج
• إدارة مخاطر تفصيلية

{emoji('target')} **مع تنسيق جميل وجداول منظمة!**"""
        
        elif analysis_type == AnalysisType.QUICK:
            context += f"\n{emoji('zap')} **المطلوب:** إجابة سريعة ومباشرة في 150 كلمة فقط مع نقاط دقيقة"
        else:
            context += f"\n{emoji('chart')} **المطلوب:** تحليل مفصل مع نقاط دخول وخروج دقيقة بالسنت"
            
        return context

    def _generate_chart_fallback_analysis(self, gold_price: GoldPrice) -> str:
        """تحليل شارت بديل عند فشل Claude"""
        return f"""{emoji('camera')} **تحليل الشارت - وضع الطوارئ**

{emoji('warning')} Claude API مشغول حالياً، إليك تحليل أساسي:

{emoji('gold')} **السعر الحالي:** ${gold_price.price}
{emoji('chart')} **التغيير:** {gold_price.change_24h:+.2f} ({gold_price.change_percentage:+.2f}%)

{emoji('target')} **نصائح عامة لتحليل الشارت:**

📈 **ابحث عن:**
• مستويات الدعم والمقاومة الواضحة
• النماذج الفنية (مثلثات، أعلام، رؤوس وأكتاف)
• اتجاه الترند العام (صاعد/هابط/عرضي)
• حجم التداول مع حركة السعر

⚖️ **إدارة المخاطر:**
• لا تخاطر بأكثر من 2% من المحفظة
• ضع وقف خسارة دائماً
• تأكد من نسبة مخاطرة/عائد جيدة (1:2 على الأقل)

{emoji('refresh')} **حاول مرة أخرى بعد دقائق** - Claude سيكون متاحاً
{emoji('phone')} **للحصول على تحليل متخصص:** @Odai_xau

{emoji('info')} هذا تحليل تعليمي عام وليس نصيحة استثمارية"""

    def _generate_text_fallback_analysis(self, gold_price: GoldPrice, analysis_type: AnalysisType) -> str:
        """تحليل نصي بديل عند فشل Claude"""
        
        # تحديد الاتجاه العام
        if gold_price.change_24h > 5:
            trend = "صاعد بقوة"
            recommendation = "BUY"
            target = gold_price.price + 20
            stop_loss = gold_price.price - 10
        elif gold_price.change_24h > 0:
            trend = "صاعد"
            recommendation = "BUY"
            target = gold_price.price + 15
            stop_loss = gold_price.price - 8
        elif gold_price.change_24h < -5:
            trend = "هابط بقوة"
            recommendation = "SELL"
            target = gold_price.price - 20
            stop_loss = gold_price.price + 10
        elif gold_price.change_24h < 0:
            trend = "هابط"
            recommendation = "SELL"
            target = gold_price.price - 15
            stop_loss = gold_price.price + 8
        else:
            trend = "عرضي"
            recommendation = "HOLD"
            target = gold_price.price + 10
            stop_loss = gold_price.price - 10
        
        if analysis_type == AnalysisType.QUICK:
            return f"""{emoji('zap')} **تحليل سريع - وضع الطوارئ**

{emoji('warning')} Claude API مشغول، إليك تحليل أساسي:

{emoji('target')} **التوصية:** {recommendation}
{emoji('up_arrow')} **السعر الحالي:** ${gold_price.price}
{emoji('chart')} **الاتجاه:** {trend}

{emoji('trophy')} **الهدف:** ${target:.2f}
{emoji('shield')} **وقف الخسارة:** ${stop_loss:.2f}
{emoji('fire')} **مستوى الثقة:** 70%

{emoji('refresh')} **حاول مرة أخرى بعد دقائق** - Claude سيكون متاحاً"""
        
        else:
            return f"""{emoji('chart')} **تحليل مفصل - وضع الطوارئ**

{emoji('warning')} Claude API مشغول حالياً، إليك تحليل تقني أساسي:

{emoji('gold')} **معلومات السعر:**
• السعر: ${gold_price.price}
• التغيير 24س: {gold_price.change_24h:+.2f} ({gold_price.change_percentage:+.2f}%)
• المدى: ${gold_price.low_24h} - ${gold_price.high_24h}

{emoji('target')} **التحليل الفني:**
• الاتجاه العام: {trend}
• التوصية: {recommendation}
• الهدف المتوقع: ${target:.2f}
• وقف الخسارة: ${stop_loss:.2f}

{emoji('shield')} **إدارة المخاطر:**
• نسبة المخاطرة المقترحة: 2% من المحفظة
• نسبة المخاطرة/العائد: 1:2
• مستوى الثقة: 70%

{emoji('clock')} **الإطار الزمني:** 
• قصير المدى: حذر بسبب التقلبات
• متوسط المدى: تابع الاتجاه العام

{emoji('refresh')} **حاول مرة أخرى بعد دقائق** - سيكون Claude متاحاً لتحليل أكثر دقة
{emoji('phone')} **للحصول على تحليل متخصص:** @Odai_xau

{emoji('info')} هذا تحليل تعليمي أساسي وليس نصيحة استثمارية"""

# ==================== Fixed Image Processor ====================
class FixedImageProcessor:
    @staticmethod
    def process_image(image_data: bytes) -> Optional[str]:
        """معالجة الصور - مُصلح"""
        try:
            if len(image_data) > Config.MAX_IMAGE_SIZE:
                raise ValueError(f"Image too large: {len(image_data)} bytes")
            
            image = Image.open(io.BytesIO(image_data))
            
            # تحسين جودة الشارت
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image, mask=image.split()[-1])
                image = background
            elif image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            # تحسين الحدة
            if max(image.size) > Config.MAX_IMAGE_DIMENSION:
                ratio = Config.MAX_IMAGE_DIMENSION / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # تحسين الجودة
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=Config.IMAGE_QUALITY, optimize=True)
            
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            logger.info(f"Processed chart image: {image.size}, {len(buffer.getvalue())} bytes")
            return image_base64
            
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            return None

# ==================== Fixed Rate Limiter ====================
class FixedRateLimiter:
    def __init__(self):
        self.requests: Dict[int, List[datetime]] = defaultdict(list)
    
    def is_allowed(self, user_id: int, user: User) -> Tuple[bool, Optional[str]]:
        """فحص الحد المسموح - مُصلح"""
        now = datetime.now()
        
        # تنظيف الطلبات القديمة
        cutoff_time = now - timedelta(seconds=Config.RATE_LIMIT_WINDOW)
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > cutoff_time
        ]
        
        max_requests = Config.RATE_LIMIT_REQUESTS
        if user.subscription_tier == "premium":
            max_requests *= 2
        elif user.subscription_tier == "vip":
            max_requests *= 5
        
        if len(self.requests[user_id]) >= max_requests:
            wait_time = Config.RATE_LIMIT_WINDOW - (now - self.requests[user_id][0]).seconds
            return False, f"{emoji('warning')} تجاوزت الحد المسموح. انتظر {wait_time} ثانية."
        
        self.requests[user_id].append(now)
        return True, None

# ==================== Fixed Security Manager ====================
class FixedSecurityManager:
    def __init__(self):
        self.active_sessions: Dict[int, datetime] = {}
        self.failed_attempts: Dict[int, int] = defaultdict(int)
        self.blocked_users: set = set()
        self.user_keys: Dict[int, str] = {}
    
    def verify_license_key(self, key: str) -> bool:
        """فحص بسيط لصيغة المفتاح"""
        return key.startswith("GOLD-") and len(key) == 19
    
    def is_session_valid(self, user_id: int) -> bool:
        """فحص صحة الجلسة"""
        return user_id in self.user_keys
    
    def create_session(self, user_id: int, license_key: str):
        """إنشاء جلسة جديدة"""
        self.active_sessions[user_id] = datetime.now()
        self.user_keys[user_id] = license_key
        self.failed_attempts[user_id] = 0
    
    def is_blocked(self, user_id: int) -> bool:
        """فحص الحظر"""
        return user_id in self.blocked_users

# ==================== Fixed Utilities ====================
def clean_markdown_text(text: str) -> str:
    """تنظيف النص من markdown المُشكِل"""
    if not text:
        return text
    
    text = text.replace('**', '')
    text = text.replace('*', '')
    text = text.replace('__', '') 
    text = text.replace('_', '')
    text = text.replace('`', '')
    text = text.replace('[', '(')
    text = text.replace(']', ')')
    
    return text

async def send_long_message_fixed(update: Update, text: str, parse_mode: str = None, reply_markup=None):
    """إرسال رسائل طويلة - محسنة بدون تأثير على المحتوى"""
    MAX_LENGTH = 4000
    
    # تنظيف خفيف للنص
    if parse_mode == ParseMode.MARKDOWN:
        text = clean_markdown_text(text)
        parse_mode = None
    
    if len(text) <= MAX_LENGTH:
        try:
            await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            return
        except Exception:
            # تنظيف إضافي فقط عند الخطأ
            clean_text = text.replace('*', '').replace('_', '')
            await update.message.reply_text(clean_text, reply_markup=reply_markup)
            return
    
    # تقسيم ذكي للنص الطويل
    parts = []
    paragraphs = text.split('\n\n')  # تقسيم حسب الفقرات
    current_part = ""
    
    for paragraph in paragraphs:
        if len(current_part) + len(paragraph) + 2 <= MAX_LENGTH:
            current_part += paragraph + '\n\n'
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = paragraph + '\n\n'
    
    if current_part:
        parts.append(current_part.strip())
    
    # إرسال الأجزاء
    for i, part in enumerate(parts):
        try:
            markup = reply_markup if i == len(parts) - 1 else None
            header = f"📄 الجزء {i+1}/{len(parts)}\n\n" if len(parts) > 1 and i > 0 else ""
            await update.message.reply_text(header + part, reply_markup=markup)
            
            if i < len(parts) - 1:
                await asyncio.sleep(0.5)  # توقف قصير
                
        except Exception as e:
            # نسخة احتياطية مبسطة
            simple_part = part.replace('```', '').replace('**', '').replace('*', '')
            await update.message.reply_text(f"الجزء {i+1} (مبسط):\n{simple_part}", reply_markup=markup)

def create_main_keyboard(user: User) -> InlineKeyboardMarkup:
    """إنشاء لوحة المفاتيح الرئيسية - مُصلح"""
    
    is_activated = (user.license_key and user.is_activated) or user.user_id == Config.MASTER_USER_ID
    
    if not is_activated:
        keyboard = [
            [InlineKeyboardButton(f"{emoji('gold')} سعر الذهب المباشر", callback_data="price_now")],
            [InlineKeyboardButton(f"{emoji('target')} تجربة تحليل مجاني", callback_data="demo_analysis")],
            [InlineKeyboardButton(f"{emoji('key')} كيف أحصل على مفتاح؟", callback_data="how_to_get_license")],
            [InlineKeyboardButton(f"{emoji('phone')} تواصل مع Odai", url="https://t.me/Odai_xau")]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton(f"{emoji('zap')} سريع (30 ثانية)", callback_data="analysis_quick"),
                InlineKeyboardButton(f"{emoji('chart')} شامل متقدم", callback_data="analysis_detailed")
            ],
            [
                InlineKeyboardButton(f"{emoji('target')} سكالب (1-15د)", callback_data="analysis_scalping"),
                InlineKeyboardButton(f"{emoji('up_arrow')} سوينج (أيام/أسابيع)", callback_data="analysis_swing")
            ],
            [
                InlineKeyboardButton(f"{emoji('crystal_ball')} توقعات ذكية", callback_data="analysis_forecast"),
                InlineKeyboardButton(f"{emoji('refresh')} نقاط الانعكاس", callback_data="analysis_reversal")
            ],
            [
                InlineKeyboardButton(f"{emoji('gold')} سعر مباشر", callback_data="price_now"),
                InlineKeyboardButton(f"{emoji('camera')} تحليل شارت", callback_data="chart_analysis_info")
            ],
            [
                InlineKeyboardButton(f"{emoji('key')} معلومات المفتاح", callback_data="key_info"),
                InlineKeyboardButton(f"{emoji('gear')} إعدادات", callback_data="settings")
            ]
        ]
        
        if user.user_id == Config.MASTER_USER_ID:
            keyboard.append([
                InlineKeyboardButton(f"{emoji('admin')} لوحة الإدارة", callback_data="admin_panel")
            ])
        
        keyboard.append([
            InlineKeyboardButton(f"{emoji('fire')} التحليل الشامل المتقدم {emoji('fire')}", callback_data="nightmare_analysis")
        ])
    
    return InlineKeyboardMarkup(keyboard)

# ==================== Fixed Decorators ====================
def require_activation_fixed(analysis_type="general"):
    """Decorator مُصلح لفحص التفعيل واستخدام المفتاح"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            
            if context.bot_data['security'].is_blocked(user_id):
                await update.message.reply_text(f"{emoji('cross')} حسابك محظور. تواصل مع الدعم.")
                return
            
            user = await context.bot_data['db'].get_user(user_id)
            if not user:
                user = User(
                    user_id=user_id,
                    username=update.effective_user.username,
                    first_name=update.effective_user.first_name
                )
                await context.bot_data['db'].add_user(user)
            
            if user_id != Config.MASTER_USER_ID and not user.is_activated:
                await update.message.reply_text(
                    f"{emoji('key')} يتطلب تفعيل الحساب\n\n"
                    "للاستخدام، يجب تفعيل حسابك أولاً.\n"
                    "استخدم: /license مفتاح_التفعيل\n\n"
                    f"{emoji('phone')} للتواصل: @Odai_xau"
                )
                return
            
            # فحص واستخدام المفتاح
            if user_id != Config.MASTER_USER_ID:
                license_manager = context.bot_data['license_manager']
                success, message = await license_manager.use_key(
                    user.license_key, 
                    user_id, 
                    user.username,
                    analysis_type
                )
                if not success:
                    await update.message.reply_text(message)
                    return
            
            # تحديث بيانات المستخدم
            user.last_activity = datetime.now()
            await context.bot_data['db'].add_user(user)
            context.user_data['user'] = user
            
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

def admin_only(func):
    """للمشرف فقط"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id != Config.MASTER_USER_ID:
            await update.message.reply_text(f"{emoji('cross')} هذا الأمر للمسؤول فقط.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==================== Fixed Command Handlers ====================
async def start_command_fixed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية - مُصلح"""
    user_id = update.effective_user.id
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    user = await context.bot_data['db'].get_user(user_id)
    if not user:
        user = User(
            user_id=user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name
        )
        await context.bot_data['db'].add_user(user)
    
    # الحصول على سعر الذهب
    try:
        gold_price = await context.bot_data['gold_price_manager'].get_gold_price()
        price_display = f"{emoji('gold')} السعر الحالي: ${gold_price.price}\n{emoji('chart')} التغيير: {gold_price.change_24h:+.2f} ({gold_price.change_percentage:+.2f}%)"
    except:
        price_display = f"{emoji('gold')} السعر: يتم التحديث..."

    is_activated = (user.license_key and user.is_activated) or user_id == Config.MASTER_USER_ID
    
    if is_activated:
        key_info = await context.bot_data['license_manager'].get_key_info(user.license_key) if user.license_key else None
        remaining_msgs = key_info['remaining_total'] if key_info else "∞"

        welcome_message = f"""╔══════════════════════════════════════╗
║     {emoji('fire')} مرحباً في عالم النخبة {emoji('fire')}     ║
╚══════════════════════════════════════╝

{emoji('wave')} أهلاً وسهلاً {update.effective_user.first_name}!

{price_display}

┌─────────────────────────────────────┐
│  {emoji('check')} حسابك مُفعَّل ومجهز للعمل   │
│  {emoji('target')} الأسئلة المتبقية: {remaining_msgs}        │
│  {emoji('info')} مفاتيح ثابتة - لا تُحذف أبداً   │
│  {emoji('zap')} البيانات محفوظة في PostgreSQL    │
│  {emoji('camera')} دعم تحليل الشارت المتقدم       │
└─────────────────────────────────────┘

{emoji('target')} اختر نوع التحليل المطلوب:"""
    else:
        welcome_message = f"""╔══════════════════════════════════════╗
║   {emoji('diamond')} Gold Nightmare Academy {emoji('diamond')}   ║
║     أقوى منصة تحليل الذهب بالعالم     ║
║      {emoji('zap')} مُصلح ومُحسن تماماً       ║
╚══════════════════════════════════════╝

{emoji('wave')} مرحباً {update.effective_user.first_name}!

{price_display}

┌─────────── {emoji('trophy')} لماذا نحن الأفضل؟ ───────────┐
│                                               │
│ {emoji('brain')} ذكاء اصطناعي متطور - Claude 4 Sonnet   │
│ {emoji('chart')} تحليل متعدد الأطر الزمنية بدقة 95%+     │
│ {emoji('target')} نقاط دخول وخروج بالسنت الواحد          │
│ {emoji('shield')} إدارة مخاطر احترافية مؤسسية           │
│ {emoji('up_arrow')} توقعات مستقبلية مع نسب ثقة دقيقة        │
│ {emoji('fire')} تحليل شامل متقدم للمحترفين              │
│ {emoji('camera')} تحليل الشارت المتقدم - الأول من نوعه    │
│ {emoji('zap')} 40 مفتاح ثابت - لا يُحذف أبداً           │
│                                               │
└───────────────────────────────────────────────┘

{emoji('gift')} عرض محدود - مفاتيح ثابتة متاحة الآن!

{emoji('key')} كل مفتاح يعطيك:
   {emoji('zap')} 50 تحليل احترافي كامل
   {emoji('brain')} تحليل بالذكاء الاصطناعي المتقدم
   {emoji('chart')} تحليل متعدد الأطر الزمنية
   {emoji('camera')} تحليل الشارت الاحترافي
   {emoji('target')} وصول للتحليل الشامل المتقدم
   {emoji('phone')} دعم فني مباشر
   {emoji('info')} 40 مفتاح ثابت - محفوظ دائماً
   {emoji('zap')} بياناتك محفوظة بشكل دائم

{emoji('info')} للحصول على مفتاح التفعيل:
تواصل مع المطور المختص"""

        keyboard = [
            [InlineKeyboardButton(f"{emoji('phone')} تواصل مع Odai", url="https://t.me/Odai_xau")],
            [InlineKeyboardButton(f"{emoji('up_arrow')} قناة التوصيات", url="https://t.me/odai_xauusdt")],
            [InlineKeyboardButton(f"{emoji('gold')} سعر الذهب الآن", callback_data="price_now")],
            [InlineKeyboardButton(f"{emoji('question')} كيف أحصل على مفتاح؟", callback_data="how_to_get_license")]
        ]
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        return

    await update.message.reply_text(
        welcome_message,
        reply_markup=create_main_keyboard(user),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

async def license_command_fixed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر تفعيل المفتاح - مُصلح"""
    user_id = update.effective_user.id
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    if not context.args:
        await update.message.reply_text(
            f"{emoji('key')} تفعيل مفتاح الترخيص\n\n"
            "الاستخدام: /license مفتاح_التفعيل\n\n"
            "مثال: /license GOLD-ABC1-DEF2-GHI3\n\n"
            f"{emoji('zap')} النظام مُصلح ومحسن للأداء"
        )
        return
    
    license_key = context.args[0].upper().strip()
    license_manager = context.bot_data['license_manager']
    
    processing_msg = await update.message.reply_text(f"{emoji('clock')} جاري التحقق من المفتاح...")
    
    try:
        is_valid, message = await license_manager.validate_key(license_key, user_id)
        
        if not is_valid:
            await processing_msg.edit_text(f"{emoji('cross')} فشل التفعيل\n\n{message}")
            return
        
        user = await context.bot_data['db'].get_user(user_id)
        if not user:
            user = User(
                user_id=user_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name
            )
        
        user.license_key = license_key
        user.is_activated = True
        user.activation_date = datetime.now()
        
        await context.bot_data['db'].add_user(user)
        
        context.bot_data['security'].create_session(user_id, license_key)
        
        key_info = await license_manager.get_key_info(license_key)
        
        success_message = f"""{emoji('check')} تم التفعيل بنجاح!

{emoji('key')} المفتاح: {license_key}
{emoji('chart')} الحد الإجمالي: {key_info['total_limit']} سؤال
{emoji('up_arrow')} المتبقي: {key_info['remaining_total']} سؤال
{emoji('info')} مفتاح ثابت - محفوظ دائماً
{emoji('zap')} البيانات محفوظة في PostgreSQL
{emoji('camera')} تحليل الشارت المتقدم متاح الآن!

{emoji('star')} يمكنك الآن استخدام البوت والحصول على التحليلات المتقدمة!"""

        await processing_msg.edit_text(
            success_message,
            reply_markup=create_main_keyboard(user)
        )
        
        # حذف الرسالة لحماية المفتاح
        try:
            await update.message.delete()
        except:
            pass
    
    except Exception as e:
        logger.error(f"License activation error: {e}")
        await processing_msg.edit_text(f"{emoji('cross')} خطأ في التفعيل. حاول مرة أخرى.")

@admin_only
async def show_fixed_keys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المفاتيح الثابتة الـ 40 للمشرف"""
    license_manager = context.bot_data['license_manager']
    
    loading_msg = await update.message.reply_text(f"{emoji('clock')} جاري تحميل المفاتيح الثابتة...")
    
    try:
        await license_manager.load_keys_from_db()
        
        if not license_manager.license_keys:
            await loading_msg.edit_text(f"{emoji('cross')} لا توجد مفاتيح")
            return
        
        message = f"{emoji('key')} المفاتيح الثابتة الـ 40 - مُصلحة ودائمة:\n\n"
        
        # إحصائيات عامة
        stats = await license_manager.get_all_keys_stats()
        message += f"{emoji('chart')} الإحصائيات:\n"
        message += f"• إجمالي المفاتيح: {stats['total_keys']}\n"
        message += f"• المفاتيح المستخدمة: {stats['used_keys']}\n"
        message += f"• المفاتيح المتاحة: {stats['unused_keys']}\n"
        message += f"• المفاتيح المنتهية: {stats['expired_keys']}\n"
        message += f"{emoji('zap')} محفوظة في PostgreSQL - مُصلحة\n\n"
        
        # عرض أول 10 مفاتيح
        count = 0
        for key, key_data in license_manager.license_keys.items():
            if count >= 10:
                break
            count += 1
            
            status = f"{emoji('green_dot')} نشط" if key_data["active"] else f"{emoji('red_dot')} معطل"
            user_info = f"{emoji('users')} {key_data['username'] or 'لا يوجد'}" if key_data["user_id"] else f"{emoji('prohibited')} غير مستخدم"
            usage = f"{key_data['used']}/{key_data['limit']}"
            
            message += f"{count:2d}. {key}\n"
            message += f"   {status} | {user_info}\n"
            message += f"   {emoji('chart')} الاستخدام: {usage}\n\n"
        
        if len(license_manager.license_keys) > 10:
            message += f"... و {len(license_manager.license_keys) - 10} مفاتيح أخرى\n\n"
        
        message += f"{emoji('info')} جميع المفاتيح ثابتة ومحفوظة دائماً"
        
        await loading_msg.edit_text(message)
    
    except Exception as e:
        logger.error(f"Show keys error: {e}")
        await loading_msg.edit_text(f"{emoji('cross')} خطأ في تحميل المفاتيح")

@admin_only
async def unused_fixed_keys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المفاتيح المتاحة من الـ 40 الثابتة"""
    license_manager = context.bot_data['license_manager']
    
    loading_msg = await update.message.reply_text(f"{emoji('clock')} جاري تحميل المفاتيح المتاحة...")
    
    try:
        await license_manager.load_keys_from_db()
        
        unused_keys = [key for key, key_data in license_manager.license_keys.items() 
                       if not key_data["user_id"] and key_data["active"]]
        
        if not unused_keys:
            await loading_msg.edit_text(f"{emoji('cross')} لا توجد مفاتيح متاحة من الـ 40")
            return
        
        message = f"{emoji('prohibited')} المفاتيح المتاحة ({len(unused_keys)} من 40):\n"
        message += f"{emoji('zap')} محفوظة بشكل دائم - مُصلحة\n\n"
        
        for i, key in enumerate(unused_keys, 1):
            key_data = license_manager.license_keys[key]
            message += f"{i:2d}. {key}\n"
            message += f"    {emoji('chart')} الحد: {key_data['limit']} أسئلة + شارت\n\n"
        
        message += f"""{emoji('info')} تعليمات إعطاء المفاتيح:
انسخ مفتاح وأرسله للمستخدم مع التعليمات:

```
{emoji('key')} مفتاح التفعيل الخاص بك:
[المفتاح]

{emoji('folder')} كيفية الاستخدام:
/license [المفتاح]

{emoji('warning')} ملاحظات مهمة:
• لديك 50 سؤال إجمالي
• مفتاح ثابت - لا يُحذف أبداً
• {emoji('camera')} تحليل الشارت المتقدم مدعوم
• {emoji('zap')} بياناتك محفوظة في PostgreSQL
```"""
        
        await loading_msg.edit_text(message)
    
    except Exception as e:
        logger.error(f"Unused keys error: {e}")
        await loading_msg.edit_text(f"{emoji('cross')} خطأ في تحميل المفاتيح")

@admin_only
async def stats_command_fixed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات البوت - مُصلحة"""
    stats_msg = await update.message.reply_text(f"{emoji('clock')} جاري جمع الإحصائيات...")
    
    try:
        db_manager = context.bot_data['db']
        license_manager = context.bot_data['license_manager']
        
        stats = await db_manager.get_stats()
        keys_stats = await license_manager.get_all_keys_stats()
        
        stats_text = f"""{emoji('chart')} **إحصائيات البوت - Fixed & Enhanced**

{emoji('users')} **المستخدمين:**
• الإجمالي: {stats['total_users']}
• المفعلين: {stats['active_users']}
• النسبة: {stats['activation_rate']}

{emoji('key')} **المفاتيح الثابتة (40):**
• الإجمالي: {keys_stats['total_keys']}
• المستخدمة: {keys_stats['used_keys']}
• المتاحة: {keys_stats['unused_keys']}
• المنتهية: {keys_stats['expired_keys']}

{emoji('progress')} **الاستخدام:**
• الاستخدام الإجمالي: {keys_stats['total_usage']}
• المتاح الإجمالي: {keys_stats['total_available']}
• متوسط الاستخدام: {keys_stats['avg_usage_per_key']:.1f}

{emoji('zap')} **النظام:**
• قاعدة البيانات: PostgreSQL Fixed
• المفاتيح: 40 ثابت - لا تُحذف أبداً
• الحفظ: دائم ومضمون
• الأداء: مُصلح ومحسن
• تحليل الشارت: {emoji('check') if Config.CHART_ANALYSIS_ENABLED else emoji('cross')}

{emoji('clock')} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        await stats_msg.edit_text(stats_text)
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        await stats_msg.edit_text(f"{emoji('cross')} خطأ في الإحصائيات")

# ==================== Fixed Message Handlers ====================
@require_activation_fixed("text_analysis")
async def handle_text_message_fixed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية - مُصلحة"""
    user = context.user_data['user']
    
    # فحص الحد المسموح
    allowed, message = context.bot_data['rate_limiter'].is_allowed(user.user_id, user)
    if not allowed:
        await update.message.reply_text(message)
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # فحص التحليل السري
    is_nightmare = Config.NIGHTMARE_TRIGGER in update.message.text
    
    if is_nightmare:
        processing_msg = await update.message.reply_text(
            f"{emoji('fire')}{emoji('fire')}{emoji('fire')} تحضير التحليل الشامل المتقدم {emoji('fire')}{emoji('fire')}{emoji('fire')}\n\n"
            f"{emoji('zap')} جمع البيانات من جميع الأطر الزمنية...\n"
            f"{emoji('chart')} تحليل المستويات والنماذج الفنية...\n"
            f"{emoji('target')} حساب نقاط الدخول والخروج الدقيقة بالسنت...\n\n"
            f"{emoji('clock')} التحليل الشامل يحتاج وقت أطول للدقة القصوى..."
        )
    else:
        processing_msg = await update.message.reply_text(f"{emoji('brain')} جاري التحليل الاحترافي...")
    
    try:
        # الحصول على السعر
        price = await context.bot_data['gold_price_manager'].get_gold_price()
        if not price:
            await processing_msg.edit_text(f"{emoji('cross')} لا يمكن الحصول على السعر حالياً.")
            return
        
        # تحديد نوع التحليل من الكلمات المفتاحية
        text_lower = update.message.text.lower()
        analysis_type = AnalysisType.DETAILED
        
        if Config.NIGHTMARE_TRIGGER in update.message.text:
            analysis_type = AnalysisType.NIGHTMARE
        elif any(word in text_lower for word in ['سريع', 'بسرعة', 'quick']):
            analysis_type = AnalysisType.QUICK
        elif any(word in text_lower for word in ['سكالب', 'scalp', 'سكالبينغ']):
            analysis_type = AnalysisType.SCALPING
        elif any(word in text_lower for word in ['سوينج', 'swing']):
            analysis_type = AnalysisType.SWING
        elif any(word in text_lower for word in ['توقع', 'مستقبل', 'forecast']):
            analysis_type = AnalysisType.FORECAST
        elif any(word in text_lower for word in ['انعكاس', 'reversal']):
            analysis_type = AnalysisType.REVERSAL
        elif any(word in text_lower for word in ['خبر', 'أخبار', 'news']):
            analysis_type = AnalysisType.NEWS
        
        result = await context.bot_data['claude_manager'].analyze_gold(
            prompt=update.message.text,
            gold_price=price,
            analysis_type=analysis_type,
            user_settings=user.settings
        )
        
        await processing_msg.delete()
        
        await send_long_message_fixed(update, result)
        
        # حفظ التحليل
        analysis = Analysis(
            id=f"{user.user_id}_{datetime.now().timestamp()}",
            user_id=user.user_id,
            timestamp=datetime.now(),
            analysis_type=analysis_type.value,
            prompt=update.message.text,
            result=result[:500],
            gold_price=price.price
        )
        await context.bot_data['db'].add_analysis(analysis)
        
        # تحديث إحصائيات المستخدم
        user.total_requests += 1
        user.total_analyses += 1
        await context.bot_data['db'].add_user(user)
        
    except Exception as e:
        logger.error(f"Error in text analysis: {e}")
        await processing_msg.edit_text(f"{emoji('cross')} حدث خطأ أثناء التحليل.")

@require_activation_fixed("image_analysis")
async def handle_photo_message_fixed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الصور - مُصلحة مع تحليل الشارت المتقدم"""
    user = context.user_data['user']
    
    # فحص الحد المسموح
    allowed, message = context.bot_data['rate_limiter'].is_allowed(user.user_id, user)
    if not allowed:
        await update.message.reply_text(message)
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    
    # فحص إذا كان التحليل السري في التعليق
    caption = update.message.caption or ""
    is_nightmare = Config.NIGHTMARE_TRIGGER in caption
    
    if is_nightmare:
        processing_msg = await update.message.reply_text(
            f"{emoji('fire')}{emoji('fire')}{emoji('fire')} تحليل شارت شامل متقدم {emoji('fire')}{emoji('fire')}{emoji('fire')}\n\n"
            f"{emoji('camera')} معالجة الصورة بالذكاء الاصطناعي المتقدم...\n"
            f"{emoji('magnifier')} تحليل النماذج الفنية والمستويات بدقة السنت..."
        )
    else:
        processing_msg = await update.message.reply_text(
            f"{emoji('camera')} **تحليل الشارت المتقدم - مُصلح**\n\n"
            f"{emoji('brain')} جاري تحليل الشارت بالذكاء الاصطناعي...\n"
            f"{emoji('magnifier')} استخراج النماذج الفنية والمستويات...\n"
            f"{emoji('target')} تحديد نقاط الدخول والخروج بدقة السنت...\n\n"
            f"{emoji('clock')} تحليل محسن وأسرع..."
        )
    
    try:
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        image_data = await photo_file.download_as_bytearray()
        
        # معالجة الصورة
        image_base64 = FixedImageProcessor.process_image(image_data)
        if not image_base64:
            await processing_msg.edit_text(f"{emoji('cross')} لا يمكن معالجة الصورة. تأكد من وضوح الشارت.")
            return
        
        # الحصول على السعر
        price = await context.bot_data['gold_price_manager'].get_gold_price()
        if not price:
            await processing_msg.edit_text(f"{emoji('cross')} لا يمكن الحصول على السعر حالياً.")
            return
        
        # تحضير prompt خاص لتحليل الشارت
        if not caption:
            caption = "حلل هذا الشارت بالتفصيل الاحترافي مع تحديد النماذج الفنية ونقاط الدخول والخروج بدقة السنت الواحد"
        
        # تحديد نوع التحليل
        analysis_type = AnalysisType.CHART
        if Config.NIGHTMARE_TRIGGER in caption:
            analysis_type = AnalysisType.NIGHTMARE
        
        # التحليل المتقدم للشارت
        result = await context.bot_data['claude_manager'].analyze_gold(
            prompt=caption,
            gold_price=price,
            image_base64=image_base64,
            analysis_type=analysis_type,
            user_settings=user.settings
        )
        
        await processing_msg.delete()
        
        # إضافة هيدر خاص لتحليل الشارت
        chart_header = f"""{emoji('camera')} **تحليل الشارت المتقدم - Fixed & Enhanced**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{result}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{emoji('diamond')} **تم بواسطة Gold Nightmare Academy**
{emoji('camera')} **تحليل الشارت المُصلح والمُحسن**
{emoji('brain')} **ذكاء اصطناعي محسن لقراءة الشارت**
{emoji('target')} **نقاط دخول وخروج بدقة السنت الواحد**
{emoji('zap')} **أداء مُصلح - استجابة سريعة**
{emoji('key')} **40 مفتاح ثابت - لا يُحذف أبداً**

{emoji('warning')} **تنبيه:** هذا تحليل تعليمي وليس نصيحة استثمارية"""
        
        await send_long_message_fixed(update, chart_header)
        
        # حفظ التحليل مع الصورة
        analysis = Analysis(
            id=f"{user.user_id}_{datetime.now().timestamp()}",
            user_id=user.user_id,
            timestamp=datetime.now(),
            analysis_type="chart_image_fixed",
            prompt=caption,
            result=result[:500],
            gold_price=price.price,
            image_data=image_data[:1000]
        )
        await context.bot_data['db'].add_analysis(analysis)
        
        # تحديث إحصائيات المستخدم
        user.total_requests += 1
        user.total_analyses += 1
        await context.bot_data['db'].add_user(user)
        
    except Exception as e:
        logger.error(f"Error in photo analysis: {e}")
        await processing_msg.edit_text(f"{emoji('cross')} حدث خطأ أثناء تحليل الشارت.")

# ==================== Fixed Callback Query Handler ====================
async def handle_callback_query_fixed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأزرار - مُصلحة"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # فحص الحظر
    if context.bot_data['security'].is_blocked(user_id):
        await query.edit_message_text(f"{emoji('cross')} حسابك محظور.")
        return
    
    # الحصول على بيانات المستخدم
    user = await context.bot_data['db'].get_user(user_id)
    if not user:
        user = User(
            user_id=user_id,
            username=query.from_user.username,
            first_name=query.from_user.first_name
        )
        await context.bot_data['db'].add_user(user)
    
    # الأوامر المسموحة بدون تفعيل
    allowed_without_license = [
        "price_now", "how_to_get_license", "back_main", 
        "demo_analysis", "chart_analysis_info"
    ]
    
    # فحص التفعيل للأوامر المحمية
    if (user_id != Config.MASTER_USER_ID and 
        (not user.license_key or not user.is_activated) and 
        data not in allowed_without_license):
        
        await query.edit_message_text(
            f"""{emoji('key')} يتطلب مفتاح تفعيل

لاستخدام هذه الميزة، يجب إدخال مفتاح تفعيل من الـ 40 الثابتة.
استخدم: /license مفتاح_التفعيل

{emoji('zap')} **مميزات النظام المُصلح:**
• 40 مفتاح ثابت - لا يُحذف أبداً
• بياناتك محفوظة في PostgreSQL
• استرداد فوري بعد إعادة التشغيل
• {emoji('camera')} تحليل الشارت المتقدم المُصلح
• أداء محسن وسريع

{emoji('info')} للحصول على مفتاح تواصل مع:
{emoji('admin')} Odai - @Odai_xau

{emoji('fire')} 40 مفتاح ثابت فقط - محدود ودائم!""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('key')} كيف أحصل على مفتاح؟", callback_data="how_to_get_license")],
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")]
            ])
        )
        return
    
    # فحص استخدام المفتاح للعمليات المتقدمة
    advanced_operations = [
        "analysis_quick", "analysis_scalping", "analysis_detailed",
        "analysis_forecast", "analysis_news", "analysis_swing", 
        "analysis_reversal", "nightmare_analysis"
    ]
    
    if user_id != Config.MASTER_USER_ID and data in advanced_operations and user.license_key:
        license_manager = context.bot_data['license_manager']
        
        if data == "nightmare_analysis":
            await query.edit_message_text(f"{emoji('clock')} جاري التحقق من المفتاح للتحليل الشامل...")
        else:
            await query.edit_message_text(f"{emoji('clock')} جاري التحقق من المفتاح...")
        
        try:
            success, use_message = await license_manager.use_key(
                user.license_key, 
                user_id,
                user.username,
                f"callback_{data}"
            )
            
            if not success:
                await query.edit_message_text(use_message)
                return
        except Exception as e:
            logger.error(f"Error using key: {e}")
            await query.edit_message_text(f"{emoji('cross')} خطأ في استخدام المفتاح")
            return
    
    try:
        if data == "price_now":
            await query.edit_message_text(f"{emoji('clock')} جاري جلب السعر...")
            
            try:
                price = await context.bot_data['gold_price_manager'].get_gold_price()
                if not price:
                    await query.edit_message_text(f"{emoji('cross')} لا يمكن الحصول على السعر حالياً.")
                    return
                
                # تحديد اتجاه السعر
                if price.change_24h > 0:
                    trend_emoji = emoji('up_arrow')
                    trend_color = emoji('green_circle')
                    trend_text = "صاعد"
                elif price.change_24h < 0:
                    trend_emoji = emoji('down_arrow')
                    trend_color = emoji('red_circle')
                    trend_text = "هابط"
                else:
                    trend_emoji = emoji('right_arrow')
                    trend_color = emoji('yellow_circle')
                    trend_text = "مستقر"
                
                price_message = f"""╔══════════════════════════════════════╗
║       {emoji('gold')} **سعر الذهب المباشر** {emoji('gold')}       ║
║        {emoji('zap')} Fixed & Enhanced System       ║
╚══════════════════════════════════════╝

{emoji('diamond')} **السعر الحالي:** ${price.price:.2f}
{trend_color} **الاتجاه:** {trend_text} {trend_emoji}
{emoji('chart')} **التغيير 24س:** {price.change_24h:+.2f} ({price.change_percentage:+.2f}%)

{emoji('top')} **أعلى سعر:** ${price.high_24h:.2f}
{emoji('bottom')} **أدنى سعر:** ${price.low_24h:.2f}
{emoji('clock')} **التحديث:** {price.timestamp.strftime('%H:%M:%S')}
{emoji('signal')} **المصدر:** {price.source}

{emoji('camera')} **تحليل الشارت:** أرسل صورة شارت لتحليل مُصلح ومتقدم
{emoji('info')} **للحصول على تحليل دقيق بالسنت استخدم الأزرار أدناه**"""
                
                price_keyboard = [
                    [
                        InlineKeyboardButton(f"{emoji('refresh')} تحديث السعر", callback_data="price_now"),
                        InlineKeyboardButton(f"{emoji('zap')} تحليل سريع", callback_data="analysis_quick")
                    ],
                    [
                        InlineKeyboardButton(f"{emoji('chart')} تحليل شامل", callback_data="analysis_detailed"),
                        InlineKeyboardButton(f"{emoji('camera')} معلومات الشارت", callback_data="chart_analysis_info")
                    ],
                    [
                        InlineKeyboardButton(f"{emoji('back')} رجوع للقائمة", callback_data="back_main")
                    ]
                ]
                
                await query.edit_message_text(
                    price_message,
                    reply_markup=InlineKeyboardMarkup(price_keyboard)
                )
                
            except Exception as e:
                logger.error(f"Error in price display: {e}")
                await query.edit_message_text(f"{emoji('cross')} خطأ في جلب بيانات السعر")
        
        elif data == "how_to_get_license":
            help_text = f"""{emoji('key')} كيفية الحصول على مفتاح التفعيل

{emoji('diamond')} Gold Nightmare Bot يقدم تحليلات الذهب الأكثر دقة في العالم!
{emoji('zap')} **إصدار مُصلح ومحسن - 40 مفتاح ثابت فقط**

{emoji('phone')} للحصول على مفتاح تفعيل:

{emoji('admin')} تواصل مع Odai:
- Telegram: @Odai_xau
- Channel: @odai_xauusdt  

{emoji('gift')} ماذا تحصل عليه:
- {emoji('zap')} 50 تحليل احترافي إجمالي بدقة السنت
- {emoji('brain')} تحليل بالذكاء الاصطناعي المُصلح والمُحسن
- {emoji('chart')} تحليل متعدد الأطر الزمنية بدقة 95%+
- {emoji('camera')} تحليل الشارت المتقدم - مُصلح ومحسن!
- {emoji('magnifier')} اكتشاف النماذج الفنية من الصور
- {emoji('target')} نقاط دخول وخروج بالسنت الواحد
- {emoji('shield')} إدارة مخاطر احترافية مؤسسية
- {emoji('fire')} التحليل الشامل المتقدم للمحترفين
- {emoji('zap')} مفتاح ثابت - لا يُحذف أبداً!

{emoji('crown')} **المميزات الجديدة المُصلحة:**
- أداء سريع ومحسن
- استجابة في ثواني معدودة
- معالجة أخطاء متقدمة
- timeout protection
- بيانات محفوظة دائماً

{emoji('warning')} **عدد محدود:** 40 مفتاح ثابت فقط!
{emoji('info')} المفتاح ينتهي بعد استنفاد 50 سؤال
{emoji('shield')} مفاتيح ثابتة - لا تُحذف مع التحديثات!

{emoji('star')} انضم لمجتمع النخبة الآن!"""

            keyboard = [
                [InlineKeyboardButton(f"{emoji('phone')} تواصل مع Odai", url="https://t.me/Odai_xau")],
                [InlineKeyboardButton(f"{emoji('up_arrow')} قناة التوصيات", url="https://t.me/odai_xauusdt")],
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")]
            ]
            
            await query.edit_message_text(
                help_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data == "key_info":
            if not user or not user.license_key:
                await query.edit_message_text(
                    f"""{emoji('cross')} لا يوجد مفتاح مفعل

للحصول على مفتاح تفعيل ثابت تواصل مع المطور""",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"{emoji('phone')} تواصل مع Odai", url="https://t.me/Odai_xau")],
                        [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")]
                    ])
                )
                return
            
            await query.edit_message_text(f"{emoji('clock')} جاري تحديث معلومات المفتاح...")
            
            try:
                key_info = await context.bot_data['license_manager'].get_key_info(user.license_key)
                if not key_info:
                    await query.edit_message_text(f"{emoji('cross')} لا يمكن جلب معلومات المفتاح")
                    return
                
                usage_percentage = (key_info['used_total'] / key_info['total_limit']) * 100
                
                key_info_message = f"""╔══════════════════════════════════════╗
║        {emoji('key')} معلومات المفتاح الثابت {emoji('key')}        ║
║          {emoji('zap')} Fixed & Enhanced System         ║
╚══════════════════════════════════════╝

{emoji('users')} المعرف: {key_info['username'] or 'غير محدد'}
{emoji('key')} المفتاح: {key_info['key'][:8]}***
{emoji('calendar')} نوع المفتاح: ثابت دائم

{emoji('chart')} الاستخدام: {key_info['used_total']}/{key_info['total_limit']} أسئلة
{emoji('up_arrow')} المتبقي: {key_info['remaining_total']} أسئلة
{emoji('percentage')} نسبة الاستخدام: {usage_percentage:.1f}%

{emoji('camera')} **المميزات المتاحة:**
• تحليل نصي متقدم مُصلح ✅
• تحليل الشارت المُحسن ✅
• التحليل الشامل المتقدم ✅
• نقاط دخول وخروج بالسنت ✅
• جميع أنواع التحليل مُصلحة ✅

{emoji('zap')} **مميزات النظام المُصلح:**
• مفتاح ثابت - لا يُحذف أبداً
• بيانات محفوظة بشكل دائم
• أداء مُصلح ومحسن
• استجابة سريعة
• معالجة أخطاء متقدمة

{emoji('diamond')} Gold Nightmare Academy - عضوية ثابتة ودائمة
{emoji('rocket')} أنت جزء من الـ 40 المختارين!"""
                
                await query.edit_message_text(
                    key_info_message,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"{emoji('refresh')} تحديث المعلومات", callback_data="key_info")],
                        [InlineKeyboardButton(f"{emoji('camera')} معلومات الشارت", callback_data="chart_analysis_info")],
                        [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")]
                    ])
                )
                
            except Exception as e:
                logger.error(f"Error in key info: {e}")
                await query.edit_message_text(f"{emoji('cross')} خطأ في جلب معلومات المفتاح")

        elif data == "chart_analysis_info":
            chart_info = f"""{emoji('camera')} **تحليل الشارت المُصلح والمُحسن**

{emoji('fire')} **الميزة الثورية - مُصلحة تماماً!**

{emoji('target')} **كيف يعمل:**
1. {emoji('camera')} أرسل صورة لأي شارت ذهب
2. {emoji('brain')} الذكاء الاصطناعي المُحسن يحلل الشارت
3. {emoji('chart')} تحصل على تحليل فني متقدم بدقة السنت

{emoji('magnifier')} **ما يمكن اكتشافه - مُحسن:**
• النماذج الفنية (Head & Shoulders, Triangles, Flags...)
• مستويات الدعم والمقاومة بدقة السنت الواحد
• الترندات والقنوات السعرية الدقيقة
• نقاط الدخول والخروج المثلى بالسنت
• إشارات الانعكاس والاستمرار
• تحليل الأحجام والمؤشرات المُحسن

{emoji('diamond')} **المميزات الجديدة المُصلحة:**
{emoji('check')} تحليل مُصلح وسريع
{emoji('check')} نقاط دخول بالسنت الواحد
{emoji('check')} نسب ثقة مدروسة ومحسوبة
{emoji('check')} توقعات زمنية دقيقة
{emoji('check')} تحذيرات متقدمة من المخاطر
{emoji('check')} نصائح إدارة المخاطر احترافية
{emoji('check')} استجابة سريعة - ثواني معدودة

{emoji('star')} **للاستخدام:**
فقط أرسل صورة شارت مع أي تعليق وسيتم التحليل المُحسن تلقائياً!

{emoji('warning')} **متطلبات:**
• مفتاح تفعيل ثابت من الـ 40
• صورة شارت واضحة
• حجم الصورة أقل من 10 ميجا

{emoji('zap')} **النظام مُصلح ومحسن - استجابة فورية!**"""

            await query.edit_message_text(
                chart_info,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{emoji('camera')} جرب تحليل شارت", callback_data="demo_chart_analysis")],
                    [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")]
                ])
            )
                        
        elif data == "back_main":
            main_message = f"""{emoji('trophy')} Gold Nightmare Bot - Fixed & Enhanced

{emoji('zap')} 40 مفتاح ثابت - لا يُحذف أبداً!
{emoji('camera')} تحليل الشارت المُصلح والمُحسن!
{emoji('target')} نقاط دخول وخروج بدقة السنت الواحد!

اختر الخدمة المطلوبة:"""
            
            await query.edit_message_text(
                main_message,
                reply_markup=create_main_keyboard(user)
            )
        
        elif data.startswith("analysis_") or data == "nightmare_analysis" or data == "confirm_nightmare":
            # معالجة أنواع التحليل المختلفة
            if data == "nightmare_analysis":
                # عرض تحذير التحليل الشامل المتقدم
                key_info = await context.bot_data['license_manager'].get_key_info(user.license_key) if user.license_key else None
                remaining_points = key_info['remaining_total'] if key_info else 0
                
                warning_message = f"""⚠️ **تحذير: التحليل الشامل المتقدم**

🔥 هذا التحليل الأقوى والأشمل في البوت!

💰 **التكلفة:** 5 نقاط (بدلاً من نقطة واحدة)
📊 **النقاط المتبقية لديك:** {remaining_points}
📊 **النقاط بعد التحليل:** {remaining_points - 5} (إذا تابعت)

🎯 **ما ستحصل عليه مقابل 5 نقاط:**
• تحليل شامل لجميع الأطر الزمنية (M5, M15, H1, H4, D1)
• نقاط دخول وخروج بدقة السنت الواحد
• مستويات دعم ومقاومة متعددة مع قوة كل مستوى  
• سيناريوهات متعددة مع احتماليات دقيقة
• استراتيجيات سكالبينج وسوينج
• تحليل نقاط الانعكاس المحتملة
• مناطق العرض والطلب المؤسسية
• توقعات قصيرة ومتوسطة المدى
• إدارة مخاطر تفصيلية
• تنسيق احترافي بجداول منظمة

⏰ **وقت التحليل:** 30-60 ثانية (تحليل معمق)

هل تريد المتابعة وخصم 5 نقاط للحصول على التحليل الأقوى؟"""

                if remaining_points < 5:
                    warning_message += f"""

❌ **تحذير:** نقاط غير كافية!
تحتاج 5 نقاط ولديك {remaining_points} فقط.

للحصول على مفتاح جديد تواصل مع: @Odai_xau"""
                    
                    await query.edit_message_text(
                        warning_message,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odai_xau")],
                            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_main")]
                        ])
                    )
                    return
                else:
                    await query.edit_message_text(
                        warning_message,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔥 نعم، أريد التحليل الشامل (5 نقاط)", callback_data="confirm_nightmare")],
                            [InlineKeyboardButton("🔙 لا، رجوع للقائمة", callback_data="back_main")]
                        ])
                    )
                    return
                    
            elif data == "confirm_nightmare":
                # تنفيذ التحليل الشامل بعد التأكيد
                analysis_type = AnalysisType.NIGHTMARE
                type_name = "🔥 التحليل الشامل المتقدم (5 نقاط)"
                points_to_deduct = 5
            else:
                analysis_type_map = {
                    "analysis_quick": (AnalysisType.QUICK, "⚡ تحليل سريع", 1),
                    "analysis_scalping": (AnalysisType.SCALPING, "🎯 سكالبينج", 1),
                    "analysis_detailed": (AnalysisType.DETAILED, "📊 تحليل مفصل", 1),
                    "analysis_swing": (AnalysisType.SWING, "📈 سوينج", 1),
                    "analysis_forecast": (AnalysisType.FORECAST, "🔮 توقعات", 1),
                    "analysis_reversal": (AnalysisType.REVERSAL, "🔄 مناطق انعكاس", 1),
                    "analysis_news": (AnalysisType.NEWS, "📰 تحليل الأخبار", 1)
                }
                
                if data in analysis_type_map:
                    analysis_type, type_name, points_to_deduct = analysis_type_map[data]
                else:
                    return
            
            # فحص واستخدام المفتاح مع النقاط المحددة
            if user_id != Config.MASTER_USER_ID and user.license_key:
                license_manager = context.bot_data['license_manager']
                
                processing_msg = await query.edit_message_text(
                    f"⏰ جاري التحقق من المفتاح لـ {type_name}..."
                )
                
                try:
                    success, use_message = await license_manager.use_key(
                        user.license_key, 
                        user_id,
                        user.username,
                        f"callback_{data}",
                        points_to_deduct=points_to_deduct
                    )
                    
                    if not success:
                        await processing_msg.edit_text(use_message)
                        return
                        
                    # عرض رسالة نجح الخصم
                    await processing_msg.edit_text(f"✅ {use_message}\n\n🧠 جاري إعداد {type_name}...")
                    
                except Exception as e:
                    logger.error(f"Error using key: {e}")
                    await processing_msg.edit_text("❌ خطأ في استخدام المفتاح")
                    return
            else:
                processing_msg = await query.edit_message_text(
                    f"🧠 جاري إعداد {type_name}...\n\n⏰ استجابة سريعة ومحسنة..."
                )
            
            try:
                price = await context.bot_data['gold_price_manager'].get_gold_price()
                if not price:
                    await processing_msg.edit_text("❌ لا يمكن الحصول على السعر حالياً.")
                    return
                
                # إنشاء prompt مناسب لنوع التحليل
                if analysis_type == AnalysisType.QUICK:
                    prompt = "تحليل سريع للذهب الآن مع توصية واضحة ونقاط دقيقة بالسنت"
                elif analysis_type == AnalysisType.SCALPING:
                    prompt = "تحليل سكالبينج للذهب للـ 15 دقيقة القادمة مع نقاط دخول وخروج دقيقة بالسنت الواحد"
                elif analysis_type == AnalysisType.SWING:
                    prompt = "تحليل سوينج للذهب للأيام والأسابيع القادمة مع نقاط دقيقة بالسنت"
                elif analysis_type == AnalysisType.FORECAST:
                    prompt = "توقعات الذهب لليوم والأسبوع القادم مع احتماليات ونقاط دقيقة"
                elif analysis_type == AnalysisType.REVERSAL:
                    prompt = "تحليل نقاط الانعكاس المحتملة للذهب مع مستويات الدعم والمقاومة بدقة السنت"
                elif analysis_type == AnalysisType.NEWS:
                    prompt = "تحليل تأثير الأخبار الحالية على الذهب مع نقاط التداول"
                elif analysis_type == AnalysisType.NIGHTMARE:
                    prompt = f"""أريد التحليل الشامل المتقدم للذهب - التحليل الأكثر تقدماً وتفصيلاً مع:

                    1. تحليل شامل لجميع الأطر الزمنية (M5, M15, H1, H4, D1) مع نسب ثقة دقيقة
                    2. مستويات دعم ومقاومة متعددة مع قوة كل مستوى بدقة السنت
                    3. نقاط دخول وخروج بالسنت الواحد مع أسباب كل نقطة
                    4. سيناريوهات متعددة (صاعد، هابط، عرضي) مع احتماليات
                    5. استراتيجيات سكالبينج وسوينج بنقاط دقيقة
                    6. تحليل نقاط الانعكاس المحتملة
                    7. مناطق العرض والطلب المؤسسية
                    8. توقعات قصيرة ومتوسطة المدى
                    9. إدارة مخاطر تفصيلية
                    10. جداول منظمة وتنسيق احترافي

                    {Config.NIGHTMARE_TRIGGER}
                    
                    اجعله التحليل الأقوى والأشمل على الإطلاق بدقة السنت الواحد!"""
                else:
                    prompt = "تحليل شامل ومفصل للذهب مع جداول منظمة ونقاط دقيقة بالسنت"
                
                result = await context.bot_data['claude_manager'].analyze_gold(
                    prompt=prompt,
                    gold_price=price,
                    analysis_type=analysis_type,
                    user_settings=user.settings
                )
                
                # إضافة توقيع خاص للتحليل الشامل المتقدم
                if analysis_type == AnalysisType.NIGHTMARE:
                    enhanced_result = f"""{result}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 **تم بواسطة Gold Nightmare Academy** 🔥
💎 **التحليل الشامل المتقدم - Premium (5 نقاط)**
⚡ **تحليل متقدم بالذكاء الاصطناعي Claude المحسن**
🎯 **دقة التحليل: 95%+ - نقاط بالسنت الواحد**
📸 **تحليل الشارت المتقدم متاح - أرسل صورة!**
🛡️ **40 مفتاح ثابت فقط - لا يُحذف أبداً**
🔑 **النظام مُصلح - اتصال مباشر فقط**
💰 **تكلفة هذا التحليل: 5 نقاط (يستحق كل نقطة)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **تنبيه هام:** هذا تحليل تعليمي متقدم وليس نصيحة استثمارية
💡 **استخدم إدارة المخاطر دائماً ولا تستثمر أكثر مما تستطيع خسارته**"""
                    result = enhanced_result
                
# حذف رسالة "جاري التحليل" وإرسال النتيجة
                await processing_msg.delete()
                await query.message.reply_text(result)
                
                # حفظ التحليل
                analysis = Analysis(
                    id=f"{user.user_id}_{datetime.now().timestamp()}",
                    user_id=user.user_id,
                    timestamp=datetime.now(),
                    analysis_type=data,
                    prompt=prompt,
                    result=result[:500],
                    gold_price=price.price
                )
                await context.bot_data['db'].add_analysis(analysis)
                
                # إضافة زر رجوع في رسالة منفصلة
                keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_main")]]
                await query.message.reply_text(
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            
            except Exception as e:
                logger.error(f"Analysis error: {e}")
                await processing_msg.edit_text(f"❌ حدث خطأ في {type_name}")
        
        
        elif data == "admin_panel" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(
                f"{emoji('admin')} لوحة الإدارة - Fixed & Enhanced\n\n"
                f"{emoji('zap')} 40 مفتاح ثابت - محفوظ دائماً\n"
                f"{emoji('shield')} النظام مُصلح ومحسن\n"
                f"{emoji('camera')} تحليل الشارت المُحسن\n\n"
                "اختر العملية المطلوبة:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(f"{emoji('chart')} إحصائيات", callback_data="admin_stats"),
                        InlineKeyboardButton(f"{emoji('key')} عرض المفاتيح", callback_data="admin_show_keys")
                    ],
                    [
                        InlineKeyboardButton(f"{emoji('prohibited')} المفاتيح المتاحة", callback_data="admin_unused_keys"),
                        InlineKeyboardButton(f"{emoji('backup')} نسخة احتياطية", callback_data="admin_backup")
                    ],
                    [
                        InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")
                    ]
                ])
            )
        
        elif data == "admin_stats" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(f"{emoji('clock')} جاري جمع الإحصائيات...")
            
            try:
                db_manager = context.bot_data['db']
                license_manager = context.bot_data['license_manager']
                
                stats = await db_manager.get_stats()
                keys_stats = await license_manager.get_all_keys_stats()
                
                stats_message = f"""{emoji('chart')} **إحصائيات شاملة - Fixed & Enhanced**

{emoji('users')} **المستخدمين:**
• إجمالي المستخدمين: {stats['total_users']}
• المستخدمين النشطين: {stats['active_users']}
• معدل التفعيل: {stats['activation_rate']}

{emoji('key')} **المفاتيح الثابتة (40 فقط):**
• إجمالي المفاتيح: {keys_stats['total_keys']}
• المفاتيح المستخدمة: {keys_stats['used_keys']}
• المفاتيح المتاحة: {keys_stats['unused_keys']}
• المفاتيح المنتهية: {keys_stats['expired_keys']}

{emoji('chart')} **الاستخدام:**
• الاستخدام الإجمالي: {keys_stats['total_usage']}
• المتاح الإجمالي: {keys_stats['total_available']}
• متوسط الاستخدام: {keys_stats['avg_usage_per_key']:.1f}

{emoji('zap')} **النظام المُصلح:**
• قاعدة البيانات: PostgreSQL Fixed
• حالة الاتصال: متصل ونشط
• المفاتيح: 40 ثابت - لا تُحذف أبداً
• الأداء: مُصلح ومحسن
• تحليل الشارت: {emoji('check') if Config.CHART_ANALYSIS_ENABLED else emoji('cross')}

{emoji('clock')} آخر تحديث: {datetime.now().strftime('%H:%M:%S')}"""
                
                await query.edit_message_text(
                    stats_message,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"{emoji('refresh')} تحديث", callback_data="admin_stats")],
                        [InlineKeyboardButton(f"{emoji('back')} رجوع للإدارة", callback_data="admin_panel")]
                    ])
                )
                
            except Exception as e:
                logger.error(f"Error in admin stats: {e}")
                await query.edit_message_text(f"{emoji('cross')} خطأ في جلب الإحصائيات")

        elif data == "admin_show_keys" and user_id == Config.MASTER_USER_ID:
            # إصلاح عرض المفاتيح مباشرة في callback
            await query.edit_message_text(f"جاري تحميل المفاتيح الثابتة...")
            
            try:
                license_manager = context.bot_data['license_manager']
                await license_manager.load_keys_from_db()
                
                if not license_manager.license_keys:
                    await query.edit_message_text(f"لا توجد مفاتيح",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(f"رجوع", callback_data="admin_panel")]
                        ])
                    )
                    return
                
                message = f"المفاتيح الثابتة الـ 40 - Ultra Simple:\n\n"
                
                # إحصائيات عامة
                stats = await license_manager.get_all_keys_stats()
                message += f"الإحصائيات:\n"
                message += f"• إجمالي المفاتيح: {stats['total_keys']}\n"
                message += f"• المفاتيح المستخدمة: {stats['used_keys']}\n"
                message += f"• المفاتيح المتاحة: {stats['unused_keys']}\n"
                message += f"• المفاتيح المنتهية: {stats['expired_keys']}\n"
                message += f"محفوظة باتصال مباشر - مُصلح\n\n"
                
                # عرض أول 10 مفاتيح
                count = 0
                for key, key_data in license_manager.license_keys.items():
                    if count >= 10:
                        break
                    count += 1
                    
                    status = "نشط" if key_data["active"] else "معطل"
                    user_info = f"({key_data['username']})" if key_data['username'] else "(غير مستخدم)"
                    usage = f"{key_data['used']}/{key_data['limit']}"
                    
                    message += f"{count:2d}. {key[:15]}...\n"
                    message += f"   {status} | {user_info}\n"
                    message += f"   الاستخدام: {usage}\n\n"
                
                if len(license_manager.license_keys) > 10:
                    message += f"... و {len(license_manager.license_keys) - 10} مفاتيح أخرى\n\n"
                
                message += f"جميع المفاتيح ثابتة ومحفوظة بالاتصال المباشر"
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"رجوع للإدارة", callback_data="admin_panel")]
                    ])
                )
            
            except Exception as e:
                logger.error(f"Admin show keys error: {e}")
                await query.edit_message_text(f"خطأ في تحميل المفاتيح: {str(e)}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"رجوع", callback_data="admin_panel")]
                    ])
                )

        elif data == "admin_unused_keys" and user_id == Config.MASTER_USER_ID:
            # إصلاح عرض المفاتيح المتاحة مباشرة في callback
            await query.edit_message_text(f"جاري تحميل المفاتيح المتاحة...")
            
            try:
                license_manager = context.bot_data['license_manager']
                await license_manager.load_keys_from_db()
                
                unused_keys = [key for key, key_data in license_manager.license_keys.items() 
                               if not key_data["user_id"] and key_data["active"]]
                
                if not unused_keys:
                    await query.edit_message_text(f"لا توجد مفاتيح متاحة من الـ 40",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(f"رجوع", callback_data="admin_panel")]
                        ])
                    )
                    return
                
                message = f"المفاتيح المتاحة ({len(unused_keys)} من 40):\n"
                message += f"محفوظة بالاتصال المباشر - مُصلح\n\n"
                
                for i, key in enumerate(unused_keys[:15], 1):  # أول 15 فقط
                    key_data = license_manager.license_keys[key]
                    message += f"{i:2d}. {key}\n"
                    message += f"    الحد: {key_data['limit']} أسئلة + شارت\n\n"
                
                if len(unused_keys) > 15:
                    message += f"... و {len(unused_keys) - 15} مفاتيح أخرى\n\n"
                
                message += f"""تعليمات إعطاء المفاتيح:
انسخ مفتاح وأرسله للمستخدم مع التعليمات:

```
مفتاح التفعيل الخاص بك:
[المفتاح]

كيفية الاستخدام:
/license [المفتاح]

ملاحظات مهمة:
• لديك 50 سؤال إجمالي
• مفتاح ثابت - لا يُحذف أبداً
• تحليل الشارت المتقدم مدعوم
• بياناتك محفوظة بالاتصال المباشر
```"""
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"رجوع للإدارة", callback_data="admin_panel")]
                    ])
                )
            
            except Exception as e:
                logger.error(f"Unused keys error: {e}")
                await query.edit_message_text(f"خطأ في تحميل المفاتيح المتاحة: {str(e)}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"رجوع", callback_data="admin_panel")]
                    ])
                )

        elif data == "admin_backup" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(f"{emoji('backup')} جاري إنشاء النسخة الاحتياطية...")
            
            try:
                db_manager = context.bot_data['db']
                license_manager = context.bot_data['license_manager']
                
                await license_manager.load_keys_from_db()
                stats = await db_manager.get_stats()
                keys_stats = await license_manager.get_all_keys_stats()
                
                # إنشاء النسخة الاحتياطية
                backup_data = {
                    'timestamp': datetime.now().isoformat(),
                    'version': '7.0 Fixed & Enhanced',
                    'system': 'Fixed 40 Static Keys',
                    'features': {
                        'static_keys': True,
                        'permanent_storage': True,
                        'chart_analysis_fixed': Config.CHART_ANALYSIS_ENABLED,
                        'performance_optimized': True
                    },
                    'stats': stats,
                    'keys_stats': keys_stats,
                    'license_keys': {k: {
                        'key': k,
                        'limit': v["limit"],
                        'used': v["used"],
                        'active': v["active"],
                        'user_id': v["user_id"],
                        'username': v["username"]
                    } for k, v in license_manager.license_keys.items()}
                }
                
                backup_filename = f"backup_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                async with aiofiles.open(backup_filename, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(backup_data, ensure_ascii=False, indent=2))
                
                await query.edit_message_text(
                    f"""{emoji('check')} تم إنشاء النسخة الاحتياطية المُصلحة

{emoji('folder')} الملف: {backup_filename}
{emoji('key')} المفاتيح الثابتة: {len(license_manager.license_keys)}
{emoji('users')} المستخدمين: {stats['total_users']}
{emoji('chart')} الاستخدام الإجمالي: {keys_stats['total_usage']}
{emoji('clock')} الوقت: {datetime.now().strftime('%H:%M:%S')}

{emoji('shield')} النسخة الاحتياطية تحتوي على:
• جميع المفاتيح الثابتة الـ 40
• بيانات المستخدمين كاملة
• إعدادات النظام المُصلح
• إحصائيات شاملة

{emoji('zap')} النظام مُصلح - البيانات آمنة ودائمة!""",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"{emoji('back')} رجوع للإدارة", callback_data="admin_panel")]
                    ])
                )
                
            except Exception as e:
                logger.error(f"Backup error: {e}")
                await query.edit_message_text(f"{emoji('cross')} خطأ في إنشاء النسخة الاحتياطية")

        # تحديث بيانات المستخدم
        user.last_activity = datetime.now()
        await context.bot_data['db'].add_user(user)
        context.user_data['user'] = user
    
    except Exception as e:
        logger.error(f"Error in callback query handler: {e}")
        await query.edit_message_text(
            f"{emoji('cross')} حدث خطأ مؤقت - النظام مُصلح",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('back')} رجوع للقائمة", callback_data="back_main")]
            ])
        )

# ==================== Fixed Error Handler ====================
async def error_handler_fixed(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأخطاء المُصلح"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # معالجة أخطاء مختلفة بطريقة مُصلحة
    if "Can't parse entities" in str(context.error):
        error_msg = f"{emoji('cross')} تم إصلاح خطأ التنسيق تلقائياً."
    elif "network" in str(context.error).lower() or "connection" in str(context.error).lower():
        error_msg = f"{emoji('warning')} مشكلة شبكة مؤقتة - النظام مُصلح."
    else:
        error_msg = f"{emoji('cross')} خطأ مؤقت - النظام مُصلح ومحسن."
    
    # محاولة إرسال رسالة خطأ للمستخدم
    try:
        if update and hasattr(update, 'message') and update.message:
            await update.message.reply_text(
                f"{error_msg}\n"
                f"{emoji('zap')} لا تقلق - بياناتك محفوظة والنظام مُصلح!\n"
                f"{emoji('key')} مفاتيحك الثابتة محفوظة دائماً\n"
                "استخدم /start للمتابعة."
            )
        elif update and hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                f"{error_msg}\n"
                f"{emoji('zap')} النظام مُصلح - بياناتك آمنة!"
            )
    except:
        pass

# ==================== Fixed Main Function ====================
def main():
    """الدالة الرئيسية - Ultra Simple & Fixed"""
    
    # التحقق من متغيرات البيئة
    if not Config.TELEGRAM_BOT_TOKEN:
        print("خطأ: TELEGRAM_BOT_TOKEN غير موجود")
        return
    
    if not Config.CLAUDE_API_KEY:
        print("خطأ: CLAUDE_API_KEY غير موجود")
        return
    
    if not Config.DATABASE_URL:
        print("خطأ: DATABASE_URL غير موجود")
        print("⚠️ تحتاج إضافة PostgreSQL في Render")
        return
    
    print("🚀 تشغيل Gold Nightmare Bot - Ultra Simple & Fixed...")
    
    # إنشاء التطبيق
    global application
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    # إنشاء المكونات البسيطة الجديدة - بدون pools
    cache_manager = FixedCacheManager()
    database_manager = UltraSimpleDatabaseManager()  # النظام الجديد البسيط
    db_manager = UltraSimpleDBManager(database_manager)
    license_manager = UltraSimpleLicenseManager(database_manager)  # النظام الجديد البسيط
    gold_price_manager = FixedGoldPriceManager(cache_manager)
    claude_manager = FixedClaudeAIManager(cache_manager)
    rate_limiter = FixedRateLimiter()
    security_manager = FixedSecurityManager()
    
    # تحميل البيانات بالنظام البسيط الجديد
    async def initialize_ultra_simple_data():
        print("⚡ تهيئة النظام البسيط الجديد...")
        await database_manager.initialize()
        
        print("🔑 تحميل المفاتيح الثابتة الـ 40...")
        await license_manager.initialize()
        
        print("👥 تحميل المستخدمين...")
        await db_manager.initialize()
        
        print("✅ اكتمال التحميل - النظام البسيط جاهز!")
        print(f"📸 تحليل الشارت: {'مفعل' if Config.CHART_ANALYSIS_ENABLED else 'معطل'}")
    
    # تشغيل تحميل البيانات البسيط
    asyncio.get_event_loop().run_until_complete(initialize_ultra_simple_data())
    
    # حفظ في bot_data
    application.bot_data.update({
        'db': db_manager,
        'license_manager': license_manager,
        'gold_price_manager': gold_price_manager,
        'claude_manager': claude_manager,
        'rate_limiter': rate_limiter,
        'security': security_manager,
        'cache': cache_manager,
        'database': database_manager
    })
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command_fixed))
    application.add_handler(CommandHandler("license", license_command_fixed))
    application.add_handler(CommandHandler("keys", show_fixed_keys_command))
    application.add_handler(CommandHandler("unusedkeys", unused_fixed_keys_command))
    application.add_handler(CommandHandler("stats", stats_command_fixed))
    
    # معالجات الرسائل
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message_fixed))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message_fixed))
    
    # معالج الأزرار
    application.add_handler(CallbackQueryHandler(handle_callback_query_fixed))
    
    # معالج الأخطاء
    application.add_error_handler(error_handler_fixed)
    
    print("✅ جاهز للعمل - النظام البسيط المُصلح!")
    print(f"📊 تم تحميل {len(license_manager.license_keys)} مفتاح ثابت")
    print(f"👥 تم تحميل {len(db_manager.users)} مستخدم")
    print("🔑 40 مفتاح ثابت - لا يُحذف أبداً!")
    print("🛡️ النظام بسيط ومُصلح - بدون connection pools")
    print("="*50)
    print("🌐 البوت يعمل على Render مع Ultra Simple System...")
    
    # إعداد webhook بسيط
    async def setup_ultra_simple_webhook():
        """إعداد webhook بسيط"""
        try:
            await application.bot.delete_webhook(drop_pending_updates=True)
            webhook_url = f"{Config.WEBHOOK_URL}/webhook"
            await application.bot.set_webhook(webhook_url)
            print(f"✅ تم تعيين Ultra Simple Webhook: {webhook_url}")
        except Exception as e:
            print(f"❌ خطأ في إعداد Webhook: {e}")
    
    asyncio.get_event_loop().run_until_complete(setup_ultra_simple_webhook())
    
    # تشغيل webhook على Render
    port = int(os.getenv("PORT", "10000"))
    webhook_url = Config.WEBHOOK_URL or "https://your-app-name.onrender.com"
    
    print(f"🔗 Ultra Simple Webhook URL: {webhook_url}/webhook")
    print(f"🚀 استمع على المنفذ: {port}")
    print(f"🛡️ PostgreSQL Database: اتصال مباشر - بدون pool")
    print(f"📸 Chart Analysis: {'Fixed & Ready' if Config.CHART_ANALYSIS_ENABLED else 'Disabled'}")
    print(f"⚡ Performance: Ultra Simple & Direct")
    print(f"🔑 License Keys: 40 Static & Permanent")
    print("🎯 لا توجد connection pools - اتصال مباشر فقط")
    
    try:
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="webhook",
            webhook_url=f"{webhook_url}/webhook",
            drop_pending_updates=True
        )
    except Exception as e:
        print(f"❌ خطأ في تشغيل Ultra Simple Webhook: {e}")
        logger.error(f"Ultra Simple webhook error: {e}")

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║              🚀 Gold Nightmare Bot - ULTRA SIMPLE & FIXED 🚀          ║
║                   No Connection Pools - Direct Only                  ║
║                    Version 7.1 Ultra Simple Fixed                    ║
║                    🔥 مشكلة اتصال قاعدة البيانات مُصلحة 🔥          ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ✅ **الحل النهائي لمشكلة قاعدة البيانات:**                           ║
║  • إزالة connection pools تماماً                                    ║
║  • اتصال مباشر لكل عملية                                            ║
║  • إغلاق فوري للاتصالات                                             ║
║  • retry logic للاتصالات الفاشلة                                    ║
║  • معالجة أخطاء مبسطة وواضحة                                       ║
║  • لا توجد timeouts معقدة                                           ║
║                                                                      ║
║  🔑 **نظام المفاتيح الثابتة - بسيط:**                                ║
║  • 40 مفتاح ثابت فقط                                               ║
║  • كل مفتاح = 50 سؤال إجمالي                                       ║
║  • حفظ مباشر في PostgreSQL                                          ║
║  • لا يتأثر بأي مشاكل اتصال                                         ║
║                                                                      ║
║  🔥 **تحليل الشارت - مُحسن:**                                        ║
║  📸 **يعمل بكفاءة عالية**                                           ║
║  • تحليل مُصلح بدقة السنت                                           ║
║  • استجابة سريعة                                                    ║
║  • معالجة صور محسنة                                                 ║
║                                                                      ║
║  ⚡ **Ultra Simple Performance:**                                     ║
║  • لا توجد connection pools                                          ║
║  • اتصال مباشر فقط                                                  ║
║  • إغلاق فوري للاتصالات                                             ║
║  • معالجة أخطاء بسيطة                                               ║
║  • retry mechanism                                                   ║
║                                                                      ║
║  💾 **PostgreSQL - Ultra Simple:**                                   ║
║  • جميع العمليات مباشرة                                             ║
║  • لا توجد pools معقدة                                              ║
║  • اتصال منفصل لكل عملية                                            ║
║  • إغلاق تلقائي للاتصالات                                           ║
║  • المفاتيح محفوظة بأمان                                            ║
║                                                                      ║
║  🎯 **جميع الميزات تعمل:**                                            ║
║  ✅ التحليل الشامل المتقدم                                          ║
║  ✅ تحليل الشارت المُحسن                                            ║
║  ✅ نقاط دخول وخروج بالسنت                                          ║
║  ✅ 40 مفتاح ثابت                                                   ║
║  ✅ إدارة متقدمة للمشرف                                             ║
║  ✅ واجهة عربية جميلة                                               ║
║                                                                      ║
║  🏆 **النتيجة النهائية:**                                           ║
║  لا توجد مشاكل اتصال قاعدة البيانات + جميع الميزات تعمل بكفاءة      ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    main()
