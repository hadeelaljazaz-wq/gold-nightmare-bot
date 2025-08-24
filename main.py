#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gold Nightmare Bot - Complete Advanced Analysis & Risk Management System
بوت تحليل الذهب الاحترافي مع نظام مفاتيح التفعيل المتقدم
Version: 6.0 Professional Enhanced - Render Webhook Edition
Author: odai - Gold Nightmare School
"""

import logging
import logging.handlers
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

# ==================== Emojis Dictionary ====================
EMOJIS = {
    # أساسي
    'chart': '📊',
    'fire': '🔥', 
    'gold': '💰',
    'diamond': '💎',
    'rocket': '🚀',
    'star': '⭐',
    'crown': '👑',
    'trophy': '🏆',
    
    # أسهم واتجاهات
    'up_arrow': '📈',
    'down_arrow': '📉', 
    'right_arrow': '➡️',
    'green_circle': '🟢',
    'red_circle': '🔴',
    'yellow_circle': '🟡',
    
    # أدوات التداول
    'target': '🎯',
    'crystal_ball': '🔮',
    'scales': '⚖️',
    'shield': '🛡️',
    'zap': '⚡',
    'magnifier': '🔍',
    'gear': '⚙️',
    
    # واجهة المستخدم
    'key': '🔑',
    'phone': '📞',
    'back': '🔙',
    'refresh': '🔄',
    'check': '✅',
    'cross': '❌',
    'warning': '⚠️',
    'info': '💡',
    
    # إدارية
    'admin': '👨‍💼',
    'users': '👥',
    'stats': '📊',
    'backup': '💾',
    'logs': '📝',
    
    # متنوعة
    'clock': '⏰',
    'calendar': '📅',
    'news': '📰',
    'brain': '🧠',
    'camera': '📸',
    'folder': '📁',
    'progress': '📈',
    'percentage': '📉',
    'wave': '👋',
    'gift': '🎁',
    'construction': '🚧',
    'lock': '🔒',
    'thumbs_up': '👍',
    'people': '👥',
    'man_office': '👨‍💼',
    'chart_bars': '📊',
    'envelope': '📧',
    'bell': '🔔',
    'house': '🏠',
    'globe': '🌐',
    'link': '🔗',
    'signal': '📡',
    'question': '❓',
    'stop': '🛑',
    'play': '▶️',
    'pause': '⏸️',
    'prohibited': '⭕',
    'red_dot': '🔴',
    'green_dot': '🟢',
    'top': '🔝',
    'bottom': '🔻',
    'up': '⬆️',
    'down': '⬇️'
}

# دالة مساعدة لاستخدام الـ emojis
def emoji(name):
    """إرجاع emoji بواسطة الاسم"""
    return EMOJIS.get(name, '')

# ==================== Configuration ====================
class Config:
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # For Render webhook
    MASTER_USER_ID = int(os.getenv("MASTER_USER_ID", "590918137"))
    
    # Claude Configuration
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
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
    
    # Database
    DB_PATH = os.getenv("DB_PATH", "gold_bot_data.db")
    KEYS_FILE = os.getenv("KEYS_FILE", "license_keys.json")
    
    # Timezone
    TIMEZONE = pytz.timezone(os.getenv("TIMEZONE", "Asia/Amman"))
    
    # Secret Analysis Trigger (Hidden from users)
    NIGHTMARE_TRIGGER = "كابوس الذهب"

# ==================== Logging Setup ====================
def setup_logging():
    """Configure advanced logging"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/gold_bot.log',
        maxBytes=10*1024*1024,
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    console_handler.setFormatter(simple_formatter)
    file_handler.setFormatter(detailed_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

# ==================== Markdown Text Cleaner ====================
def clean_markdown_text(text: str) -> str:
    """تنظيف النص من markdown المُشكِل"""
    if not text:
        return text
    
    # استبدال الرموز المُشكِلة
    text = text.replace('**', '')  # حذف النجمتين
    text = text.replace('*', '')   # حذف النجمة الواحدة  
    text = text.replace('__', '')  # حذف الخطوط السفلية
    text = text.replace('_', '')   # حذف الخط السفلي الواحد
    text = text.replace('`', '')   # حذف الـ backticks
    text = text.replace('[', '(')  # استبدال الأقواس المربعة
    text = text.replace(']', ')')
    
    return text

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
    total_limit: int = 50  # 50 سؤال إجمالي بدلاً من يومي
    used_total: int = 0    # العدد المستخدم إجمالياً
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

# ==================== License Manager ====================
class LicenseManager:
    def __init__(self, keys_file: str = None):
        self.keys_file = keys_file or Config.KEYS_FILE
        self.license_keys: Dict[str, LicenseKey] = {}
        
    async def initialize(self):
        """تحميل المفاتيح وإنشاء المفاتيح الأولية"""
        await self.load_keys()
        
        if len(self.license_keys) == 0:
            await self.generate_initial_keys(40)
            await self.save_keys()
    
    async def generate_initial_keys(self, count: int = 40):
        """إنشاء المفاتيح الأولية - 50 سؤال لكل مفتاح"""
        print(f"{emoji('key')} إنشاء {count} مفتاح تفعيل...")
        
        for i in range(count):
            key = self.generate_unique_key()
            license_key = LicenseKey(
                key=key,
                created_date=datetime.now(),
                total_limit=50,  # 50 سؤال إجمالي
                notes=f"مفتاح أولي رقم {i+1}"
            )
            self.license_keys[key] = license_key
        
        print(f"{emoji('check')} تم إنشاء {count} مفتاح بنجاح!")
        print("\n" + "="*70)
        print(f"{emoji('key')} مفاتيح التفعيل المُنشأة (احفظها في مكان آمن):")
        print("="*70)
        for i, (key, _) in enumerate(self.license_keys.items(), 1):
            print(f"{i:2d}. {key}")
        print("="*70)
        print(f"{emoji('info')} كل مفتاح يعطي 50 سؤال إجمالي وينتهي")
        print("="*70)
    
    def generate_unique_key(self) -> str:
        """إنشاء مفتاح فريد"""
        chars = string.ascii_uppercase + string.digits
        
        while True:
            key_parts = []
            for _ in range(3):
                part = ''.join(secrets.choice(chars) for _ in range(4))
                key_parts.append(part)
            
            key = f"GOLD-{'-'.join(key_parts)}"
            
            if key not in self.license_keys:
                return key
    
    async def create_new_key(self, total_limit: int = 50, notes: str = "") -> str:
        """إنشاء مفتاح جديد"""
        key = self.generate_unique_key()
        license_key = LicenseKey(
            key=key,
            created_date=datetime.now(),
            total_limit=total_limit,
            notes=notes
        )
        self.license_keys[key] = license_key
        await self.save_keys()
        return key
    
    async def load_keys(self):
        """تحميل المفاتيح من الملف"""
        try:
            async with aiofiles.open(self.keys_file, 'r', encoding='utf-8') as f:
                data = json.loads(await f.read())
                
                for key_data in data.get('keys', []):
                    key = LicenseKey(
                        key=key_data['key'],
                        created_date=datetime.fromisoformat(key_data['created_date']),
                        total_limit=key_data.get('total_limit', 50),  # تحديث للنظام الجديد
                        used_total=key_data.get('used_total', 0),
                        is_active=key_data.get('is_active', True),
                        user_id=key_data.get('user_id'),
                        username=key_data.get('username'),
                        notes=key_data.get('notes', '')
                    )
                    self.license_keys[key.key] = key
                
                print(f"{emoji('check')} تم تحميل {len(self.license_keys)} مفتاح")
                
        except FileNotFoundError:
            print(f"{emoji('magnifier')} ملف المفاتيح غير موجود، سيتم إنشاؤه")
            self.license_keys = {}
        except Exception as e:
            print(f"{emoji('cross')} خطأ في تحميل المفاتيح: {e}")
            self.license_keys = {}
    
    async def save_keys(self):
        """حفظ المفاتيح في الملف"""
        try:
            data = {
                'keys': [
                    {
                        'key': key.key,
                        'created_date': key.created_date.isoformat(),
                        'total_limit': key.total_limit,
                        'used_total': key.used_total,
                        'is_active': key.is_active,
                        'user_id': key.user_id,
                        'username': key.username,
                        'notes': key.notes
                    }
                    for key in self.license_keys.values()
                ]
            }
            
            async with aiofiles.open(self.keys_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
                
        except Exception as e:
            print(f"{emoji('cross')} خطأ في حفظ المفاتيح: {e}")
    
    async def validate_key(self, key: str, user_id: int) -> Tuple[bool, str]:
        """فحص صحة المفتاح - نظام 50 سؤال"""
        if key not in self.license_keys:
            return False, f"{emoji('cross')} مفتاح التفعيل غير صالح"
        
        license_key = self.license_keys[key]
        
        if not license_key.is_active:
            return False, f"{emoji('cross')} مفتاح التفعيل معطل"
        
        if license_key.user_id and license_key.user_id != user_id:
            return False, f"{emoji('cross')} مفتاح التفعيل مستخدم من قبل مستخدم آخر"
        
        if license_key.used_total >= license_key.total_limit:
            return False, f"{emoji('cross')} انتهت صلاحية المفتاح\n{emoji('info')} تم استنفاد الـ {license_key.total_limit} أسئلة\n{emoji('phone')} للحصول على مفتاح جديد: @Odai_xau"
        
        return True, f"{emoji('check')} مفتاح صالح"
    
    async def use_key(self, key: str, user_id: int, username: str = None, request_type: str = "analysis") -> Tuple[bool, str]:
        """استخدام المفتاح - نظام 50 سؤال"""
        is_valid, message = await self.validate_key(key, user_id)
        
        if not is_valid:
            return False, message
        
        license_key = self.license_keys[key]
        
        if not license_key.user_id:
            license_key.user_id = user_id
            license_key.username = username
        
        license_key.used_total += 1
        
        await self.save_keys()
        
        remaining = license_key.total_limit - license_key.used_total
        
        if remaining == 0:
            return True, f"{emoji('check')} تم استخدام المفتاح بنجاح\n{emoji('warning')} هذا آخر سؤال! انتهت صلاحية المفتاح\n{emoji('phone')} للحصول على مفتاح جديد: @Odai_xau"
        elif remaining <= 5:
            return True, f"{emoji('check')} تم استخدام المفتاح بنجاح\n{emoji('warning')} تبقى {remaining} أسئلة فقط!"
        else:
            return True, f"{emoji('check')} تم استخدام المفتاح بنجاح\n{emoji('chart')} الأسئلة المتبقية: {remaining} من {license_key.total_limit}"
    
    async def get_key_info(self, key: str) -> Optional[Dict]:
        """الحصول على معلومات المفتاح"""
        if key not in self.license_keys:
            return None
        
        license_key = self.license_keys[key]
        
        return {
            'key': key,
            'is_active': license_key.is_active,
            'total_limit': license_key.total_limit,
            'used_total': license_key.used_total,
            'remaining_total': license_key.total_limit - license_key.used_total,
            'user_id': license_key.user_id,
            'username': license_key.username,
            'created_date': license_key.created_date.strftime('%Y-%m-%d'),
            'notes': license_key.notes
        }
    
    async def get_all_keys_stats(self) -> Dict:
        """إحصائيات جميع المفاتيح"""
        total_keys = len(self.license_keys)
        active_keys = sum(1 for key in self.license_keys.values() if key.is_active)
        used_keys = sum(1 for key in self.license_keys.values() if key.user_id is not None)
        expired_keys = sum(1 for key in self.license_keys.values() if key.used_total >= key.total_limit)
        
        total_usage = sum(key.used_total for key in self.license_keys.values())
        total_available = sum(key.total_limit - key.used_total for key in self.license_keys.values() if key.used_total < key.total_limit)
        
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
    
    async def delete_user_by_key(self, key: str) -> Tuple[bool, str]:
        """حذف مستخدم من المفتاح وإعادة تعيين الاستخدام"""
        if key not in self.license_keys:
            return False, f"{emoji('cross')} المفتاح غير موجود"
        
        license_key = self.license_keys[key]
        if not license_key.user_id:
            return False, f"{emoji('cross')} المفتاح غير مرتبط بمستخدم"
        
        old_user_id = license_key.user_id
        old_username = license_key.username
        
        license_key.user_id = None
        license_key.username = None
        license_key.used_total = 0  # إعادة تعيين العداد
        
        await self.save_keys()
        
        return True, f"{emoji('check')} تم حذف المستخدم {old_username or old_user_id} من المفتاح {key}\n{emoji('refresh')} تم إعادة تعيين العداد إلى 0"

# ==================== Database Manager ====================
class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.users: Dict[int, User] = {}
        self.analyses: List[Analysis] = []
        
    async def load_data(self):
        """تحميل البيانات"""
        try:
            if os.path.exists(self.db_path):
                async with aiofiles.open(self.db_path, 'rb') as f:
                    data = pickle.loads(await f.read())
                    self.users = data.get('users', {})
                    self.analyses = data.get('analyses', [])
                    logger.info(f"Loaded {len(self.users)} users and {len(self.analyses)} analyses")
        except Exception as e:
            logger.error(f"Error loading database: {e}")
    
    async def save_data(self):
        """حفظ البيانات"""
        try:
            data = {
                'users': self.users,
                'analyses': self.analyses
            }
            async with aiofiles.open(self.db_path, 'wb') as f:
                await f.write(pickle.dumps(data))
        except Exception as e:
            logger.error(f"Error saving database: {e}")
    
    async def add_user(self, user: User):
        """إضافة مستخدم"""
        self.users[user.user_id] = user
        await self.save_data()
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """جلب مستخدم"""
        return self.users.get(user_id)
    
    async def add_analysis(self, analysis: Analysis):
        """إضافة تحليل"""
        self.analyses.append(analysis)
        await self.save_data()
    
    async def get_user_analyses(self, user_id: int, limit: int = 10) -> List[Analysis]:
        """جلب تحليلات المستخدم"""
        user_analyses = [a for a in self.analyses if a.user_id == user_id]
        return user_analyses[-limit:]
    
    async def get_stats(self) -> Dict[str, Any]:
        """إحصائيات البوت"""
        total_users = len(self.users)
        active_users = len([u for u in self.users.values() if u.is_activated])
        total_analyses = len(self.analyses)
        
        last_24h = datetime.now() - timedelta(hours=24)
        recent_analyses = [a for a in self.analyses if a.timestamp > last_24h]
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_analyses': total_analyses,
            'analyses_24h': len(recent_analyses),
            'activation_rate': f"{(active_users/total_users*100):.1f}%" if total_users > 0 else "0%"
        }

# ==================== Cache System ====================
class CacheManager:
    def __init__(self):
        self.price_cache: Optional[Tuple[GoldPrice, datetime]] = None
        self.analysis_cache: Dict[str, Tuple[str, datetime]] = {}
    
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

# ==================== Gold Price Manager ====================
class GoldPriceManager:
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """جلب جلسة HTTP"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def get_gold_price(self) -> Optional[GoldPrice]:
        """جلب سعر الذهب"""
        cached_price = self.cache.get_price()
        if cached_price:
            return cached_price
        
        price = await self._fetch_from_goldapi()
        if price:
            self.cache.set_price(price)
            return price
        
        # استخدام سعر افتراضي في حالة فشل الـ API
        logger.warning("Using fallback gold price")
        return GoldPrice(
            price=2650.0,
            timestamp=datetime.now(),
            change_24h=2.5,
            change_percentage=0.1,
            high_24h=2655.0,
            low_24h=2645.0,
            source="fallback"
        )
    
    async def _fetch_from_goldapi(self) -> Optional[GoldPrice]:
        """جلب السعر من GoldAPI"""
        try:
            session = await self.get_session()
            headers = {
                "x-access-token": Config.GOLD_API_TOKEN,
                "Content-Type": "application/json"
            }
            
            async with session.get(Config.GOLD_API_URL, headers=headers, timeout=10) as response:
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

# ==================== Image Processor ====================
class ImageProcessor:
    @staticmethod
    def process_image(image_data: bytes) -> Optional[str]:
        """معالجة الصور"""
        try:
            if len(image_data) > Config.MAX_IMAGE_SIZE:
                raise ValueError(f"Image too large: {len(image_data)} bytes")
            
            image = Image.open(io.BytesIO(image_data))
            
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image, mask=image.split()[-1])
                image = background
            elif image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            if max(image.size) > Config.MAX_IMAGE_DIMENSION:
                ratio = Config.MAX_IMAGE_DIMENSION / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=92, optimize=True)
            
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            logger.info(f"Processed image: {image.size}, {len(buffer.getvalue())} bytes")
            return image_base64
            
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            return None

# ==================== Claude AI Manager ====================
class ClaudeAIManager:
    def __init__(self, cache_manager: CacheManager):
        self.client = anthropic.Anthropic(api_key=Config.CLAUDE_API_KEY)
        self.cache = cache_manager
        
    async def analyze_gold(self, 
                          prompt: str, 
                          gold_price: GoldPrice,
                          image_base64: Optional[str] = None,
                          analysis_type: AnalysisType = AnalysisType.DETAILED,
                          user_settings: Dict[str, Any] = None) -> str:
        """تحليل الذهب مع Claude المحسن"""
        
        # التحقق من التحليل الخاص السري (بدون إظهار للمستخدم)
        is_nightmare_analysis = Config.NIGHTMARE_TRIGGER in prompt
        
        if is_nightmare_analysis:
            analysis_type = AnalysisType.NIGHTMARE
        
        system_prompt = self._build_system_prompt(analysis_type, gold_price, user_settings)
        user_prompt = self._build_user_prompt(prompt, gold_price, analysis_type)
        
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
            
            message = await asyncio.to_thread(
                self.client.messages.create,
                model=Config.CLAUDE_MODEL,
                max_tokens=Config.CLAUDE_MAX_TOKENS,
                temperature=Config.CLAUDE_TEMPERATURE,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": content
                }]
            )
            
            result = message.content[0].text
            return result

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return f"{emoji('cross')} خطأ في التحليل: {str(e)}"
    
    def _build_system_prompt(self, analysis_type: AnalysisType, 
                            gold_price: GoldPrice,
                            user_settings: Dict[str, Any] = None) -> str:
        """بناء بروبت النظام المحسن مع تنسيقات متقدمة"""
        
        base_prompt = f"""أنت خبير عالمي في أسواق المعادن الثمينة والذهب مع خبرة +25 سنة في:
• التحليل الفني والكمي المتقدم متعدد الأطر الزمنية
• اكتشاف النماذج الفنية والإشارات المتقدمة
• إدارة المخاطر والمحافظ الاستثمارية المتخصصة
• تحليل نقاط الانعكاس ومستويات الدعم والمقاومة
• تطبيقات الذكاء الاصطناعي والتداول الخوارزمي المتقدم
• تحليل مناطق العرض والطلب والسيولة المؤسسية

{emoji('trophy')} الانتماء المؤسسي: Gold Nightmare Academy - أكاديمية التحليل المتقدم

البيانات الحية المعتمدة:
{emoji('gold')} السعر: ${gold_price.price} USD/oz
{emoji('chart')} التغيير 24h: {gold_price.change_24h:+.2f} ({gold_price.change_percentage:+.2f}%)
{emoji('up_arrow')} المدى: ${gold_price.low_24h} - ${gold_price.high_24h}
{emoji('clock')} الوقت: {gold_price.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
{emoji('signal')} المصدر: {gold_price.source}
"""
        
        # تخصيص حسب نوع التحليل مع تنسيقات متقدمة
        if analysis_type == AnalysisType.QUICK:
            base_prompt += f"""

{emoji('zap')} **التحليل السريع - أقصى 150 كلمة:**

{emoji('folder')} **التنسيق المطلوب:**
```
{emoji('target')} **التوصية:** [BUY/SELL/HOLD]
{emoji('up_arrow')} **السعر الحالي:** $[السعر]
{emoji('red_dot')} **السبب:** [سبب واحد قوي]

{emoji('chart')} **الأهداف:**
{emoji('trophy')} الهدف الأول: $[السعر]
{emoji('red_dot')} وقف الخسارة: $[السعر]

{emoji('clock')} **الإطار الزمني:** [المدة المتوقعة]
{emoji('fire')} **مستوى الثقة:** [نسبة مئوية]%
```

{emoji('star')} **متطلبات:**
- توصية واضحة ومباشرة فقط
- سبب رئيسي واحد مقنع
- هدف واحد ووقف خسارة واحد
- بدون مقدمات أو تفاصيل زائدة
- تنسيق منظم ومختصر"""

        elif analysis_type == AnalysisType.NIGHTMARE:
            base_prompt += f"""

{emoji('fire')}{emoji('fire')}{emoji('fire')} **التحليل الشامل المتقدم** {emoji('fire')}{emoji('fire')}{emoji('fire')}
هذا التحليل المتقدم يشمل جميع الجوانب التالية:

╔════════════════════════════════════════════════════════════════════╗
║                    {emoji('target')} **التحليل الشامل المطلوب**                    ║
╚════════════════════════════════════════════════════════════════════╝

{emoji('chart')} **1. تحليل الأطر الزمنية المتعددة:**
• تحليل M5, M15, H1, H4, D1 مع نسب الثقة
• إجماع الأطر الزمنية والتوصية الموحدة
• أفضل إطار زمني للدخول

{emoji('target')} **2. مناطق الدخول والخروج:**
• نقاط الدخول الدقيقة بالسنت الواحد
• مستويات الخروج المتدرجة
• نقاط إضافة الصفقات

{emoji('shield')} **3. مستويات الدعم والمقاومة:**
• الدعوم والمقاومات الأساسية
• المستويات النفسية المهمة
• قوة كل مستوى (ضعيف/متوسط/قوي)

{emoji('refresh')} **4. نقاط الارتداد المحتملة:**
• مناطق الارتداد عالية الاحتمال
• إشارات التأكيد المطلوبة
• نسب نجاح الارتداد

{emoji('scales')} **5. مناطق العرض والطلب:**
• مناطق العرض المؤسسية
• مناطق الطلب القوية
• تحليل السيولة والحجم

{emoji('zap')} **6. استراتيجيات السكالبينج:**
• فرص السكالبينج (1-15 دقيقة)
• نقاط الدخول السريعة
• أهداف محققة بسرعة

{emoji('up_arrow')} **7. استراتيجيات السوينج:**
• فرص التداول متوسط المدى (أيام-أسابيع)
• نقاط الدخول الاستراتيجية
• أهداف طويلة المدى

{emoji('refresh')} **8. تحليل الانعكاس:**
• نقاط الانعكاس المحتملة
• مؤشرات تأكيد الانعكاس
• قوة الانعكاس المتوقعة

{emoji('chart')} **9. نسب الثقة المبررة:**
• نسبة ثقة لكل تحليل مع المبررات
• درجة المخاطرة لكل استراتيجية
• احتمالية نجاح كل سيناريو

{emoji('info')} **10. توصيات إدارة المخاطر:**
• حجم الصفقة المناسب
• وقف الخسارة المثالي
• نسبة المخاطر/العوائد

{emoji('target')} **متطلبات التنسيق:**
• استخدام جداول منسقة وواضحة
• تقسيم المعلومات إلى أقسام مرتبة
• استخدام رموز تعبيرية مناسبة
• عرض النتائج بطريقة جميلة وسهلة القراءة
• تضمين نصيحة احترافية في كل قسم

{emoji('target')} **مع تنسيق جميل وجداول منظمة ونصائح احترافية!**

{emoji('warning')} ملاحظة: هذا تحليل تعليمي وليس نصيحة استثمارية شخصية"""

        # إضافة المتطلبات العامة
        base_prompt += f"""

{emoji('target')} **متطلبات التنسيق العامة:**
1. استخدام جداول وترتيبات جميلة
2. تقسيم المعلومات إلى أقسام واضحة
3. استخدام رموز تعبيرية مناسبة
4. تنسيق النتائج بطريقة احترافية
5. تقديم نصيحة عملية في كل تحليل
6. نسب ثقة مبررة إحصائياً
7. تحليل احترافي باللغة العربية مع مصطلحات فنية دقيقة

{emoji('warning')} ملاحظة: هذا تحليل تعليمي وليس نصيحة استثمارية شخصية"""
        
        return base_prompt

    def _build_user_prompt(self, prompt: str, gold_price: GoldPrice, analysis_type: AnalysisType) -> str:
        """بناء prompt المستخدم"""
        
        context = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{emoji('gold')} **البيانات الأساسية:**
• السعر الحالي: ${gold_price.price}
• التغيير: {gold_price.change_24h:+.2f} USD ({gold_price.change_percentage:+.2f}%)
• المدى اليومي: ${gold_price.low_24h} - ${gold_price.high_24h}
• التوقيت: {gold_price.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{emoji('target')} **طلب المستخدم:** {prompt}

{emoji('folder')} **نوع التحليل المطلوب:** {analysis_type.value}

"""
        
        if analysis_type == AnalysisType.NIGHTMARE:
            context += f"""{emoji('fire')} **التحليل الشامل المطلوب:**

المطلوب تحليل شامل ومفصل يشمل جميع النقاط التالية بتنسيق جميل:

{emoji('chart')} **1. تحليل الأطر الزمنية المتعددة**
{emoji('target')} **2. مناطق الدخول والخروج الدقيقة**
{emoji('shield')} **3. مستويات الدعم والمقاومة**
{emoji('refresh')} **4. نقاط الارتداد المحتملة**
{emoji('scales')} **5. مناطق العرض والطلب**
{emoji('zap')} **6. استراتيجيات السكالبينج**
{emoji('up_arrow')} **7. استراتيجيات السوينج**
{emoji('refresh')} **8. تحليل الانعكاس**
{emoji('chart')} **9. نسب الثقة المبررة**
{emoji('info')} **10. توصيات إدارة المخاطر**

{emoji('target')} **مع تنسيق جميل وجداول منظمة ونصائح احترافية!**"""
        
        elif analysis_type == AnalysisType.QUICK:
            context += f"\n{emoji('zap')} **المطلوب:** إجابة سريعة ومباشرة ومنسقة في 150 كلمة فقط"
        else:
            context += f"\n{emoji('chart')} **المطلوب:** تحليل مفصل ومنسق بجداول جميلة"
            
        return context

# ==================== Rate Limiter ====================
class RateLimiter:
    def __init__(self):
        self.requests: Dict[int, List[datetime]] = defaultdict(list)
    
    def is_allowed(self, user_id: int, user: User) -> Tuple[bool, Optional[str]]:
        """فحص الحد المسموح"""
        now = datetime.now()
        
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < timedelta(seconds=Config.RATE_LIMIT_WINDOW)
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

# ==================== Security Manager ====================
class SecurityManager:
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

# ==================== Telegram Utilities ====================
async def send_long_message(update: Update, text: str, parse_mode: str = None):
    """إرسال رسائل طويلة مع معالجة أخطاء Markdown"""
    max_length = 4000
    
    # تنظيف النص إذا كان Markdown
    if parse_mode == ParseMode.MARKDOWN:
        text = clean_markdown_text(text)
        parse_mode = None  # إلغاء markdown بعد التنظيف
    
    if len(text) <= max_length:
        try:
            await update.message.reply_text(text, parse_mode=parse_mode)
        except Exception as e:
            # في حالة فشل parsing، إرسال بدون formatting
            logger.error(f"Markdown parsing error: {e}")
            clean_text = clean_markdown_text(text)
            await update.message.reply_text(clean_text)
        return
    
    parts = []
    current_part = ""
    
    for line in text.split('\n'):
        if len(current_part) + len(line) + 1 > max_length:
            parts.append(current_part)
            current_part = line
        else:
            current_part += '\n' + line if current_part else line
    
    if current_part:
        parts.append(current_part)
    
    for i, part in enumerate(parts):
        try:
            await update.message.reply_text(
                part + (f"\n\n{emoji('refresh')} الجزء {i+1}/{len(parts)}" if len(parts) > 1 else ""),
                parse_mode=parse_mode
            )
        except Exception as e:
            # في حالة فشل parsing، إرسال بدون formatting
            logger.error(f"Markdown parsing error in part {i+1}: {e}")
            clean_part = clean_markdown_text(part)
            await update.message.reply_text(
                clean_part + (f"\n\n{emoji('refresh')} الجزء {i+1}/{len(parts)}" if len(parts) > 1 else "")
            )
        await asyncio.sleep(0.5)

def create_main_keyboard(user: User) -> InlineKeyboardMarkup:
    """إنشاء لوحة المفاتيح الرئيسية المحسنة"""
    
    is_activated = (user.license_key and user.is_activated) or user.user_id == Config.MASTER_USER_ID
    
    if not is_activated:
        # للمستخدمين غير المفعلين
        keyboard = [
            [
                InlineKeyboardButton(f"{emoji('gold')} سعر الذهب المباشر", callback_data="price_now")
            ],
            [
                InlineKeyboardButton(f"{emoji('target')} تجربة تحليل مجاني", callback_data="demo_analysis"),
            ],
            [
                InlineKeyboardButton(f"{emoji('key')} كيف أحصل على مفتاح؟", callback_data="how_to_get_license")
            ],
            [
                InlineKeyboardButton(f"{emoji('phone')} تواصل مع Odai", url="https://t.me/Odai_xau")
            ]
        ]
    else:
        # للمستخدمين المفعلين - قائمة متخصصة
        keyboard = [
            # الصف الأول - التحليلات الأساسية
            [
                InlineKeyboardButton(f"{emoji('zap')} سريع (30 ثانية)", callback_data="analysis_quick"),
                InlineKeyboardButton(f"{emoji('chart')} شامل متقدم", callback_data="analysis_detailed")
            ],
            # الصف الثاني - تحليلات متخصصة
            [
                InlineKeyboardButton(f"{emoji('target')} سكالب (1-15د)", callback_data="analysis_scalping"),
                InlineKeyboardButton(f"{emoji('up_arrow')} سوينج (أيام/أسابيع)", callback_data="analysis_swing")
            ],
            # الصف الثالث - توقعات وانعكاسات
            [
                InlineKeyboardButton(f"{emoji('crystal_ball')} توقعات ذكية", callback_data="analysis_forecast"),
                InlineKeyboardButton(f"{emoji('refresh')} نقاط الانعكاس", callback_data="analysis_reversal")
            ],
            # الصف الرابع - أدوات إضافية
            [
                InlineKeyboardButton(f"{emoji('gold')} سعر مباشر", callback_data="price_now"),
                InlineKeyboardButton(f"{emoji('news')} تأثير الأخبار", callback_data="analysis_news")
            ],
            # الصف الخامس - المعلومات الشخصية
            [
                InlineKeyboardButton(f"{emoji('key')} معلومات المفتاح", callback_data="key_info"),
                InlineKeyboardButton(f"{emoji('gear')} إعدادات", callback_data="settings")
            ]
        ]
        
        # إضافة لوحة الإدارة للمشرف فقط
        if user.user_id == Config.MASTER_USER_ID:
            keyboard.append([
                InlineKeyboardButton(f"{emoji('admin')} لوحة الإدارة", callback_data="admin_panel")
            ])
        
        # إضافة زر التحليل الشامل المتقدم
        keyboard.append([
            InlineKeyboardButton(f"{emoji('fire')} التحليل الشامل المتقدم {emoji('fire')}", callback_data="nightmare_analysis")
        ])
    
    return InlineKeyboardMarkup(keyboard)

def create_admin_keyboard() -> InlineKeyboardMarkup:
    """لوحة الإدارة المحسنة"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{emoji('chart')} إحصائيات عامة", callback_data="admin_stats"),
            InlineKeyboardButton(f"{emoji('key')} إدارة المفاتيح", callback_data="admin_keys")
        ],
        [
            InlineKeyboardButton(f"{emoji('users')} إدارة المستخدمين", callback_data="admin_users"),
            InlineKeyboardButton(f"{emoji('up_arrow')} تقارير التحليل", callback_data="admin_analyses")
        ],
        [
            InlineKeyboardButton(f"{emoji('backup')} نسخة احتياطية", callback_data="create_backup"),
            InlineKeyboardButton(f"{emoji('logs')} سجل الأخطاء", callback_data="view_logs")
        ],
        [
            InlineKeyboardButton(f"{emoji('gear')} إعدادات النظام", callback_data="system_settings"),
            InlineKeyboardButton(f"{emoji('refresh')} إعادة تشغيل", callback_data="restart_bot")
        ],
        [
            InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")
        ]
    ])

def create_keys_management_keyboard() -> InlineKeyboardMarkup:
    """لوحة إدارة المفاتيح"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{emoji('folder')} عرض كل المفاتيح", callback_data="keys_show_all"),
            InlineKeyboardButton(f"{emoji('prohibited')} المفاتيح المتاحة", callback_data="keys_show_unused")
        ],
        [
            InlineKeyboardButton(f"{emoji('plus')} إنشاء مفاتيح جديدة", callback_data="keys_create_prompt"),
            InlineKeyboardButton(f"{emoji('chart')} إحصائيات المفاتيح", callback_data="keys_stats")
        ],
        [
            InlineKeyboardButton(f"{emoji('cross')} حذف مستخدم", callback_data="keys_delete_user"),
            InlineKeyboardButton(f"{emoji('back')} رجوع للإدارة", callback_data="admin_panel")
        ]
    ])

# ==================== Decorators ====================
def require_activation_with_key_usage(analysis_type="general"):
    """Decorator لفحص التفعيل واستخدام المفتاح"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            
            # فحص الحظر
            if context.bot_data['security'].is_blocked(user_id):
                await update.message.reply_text(f"{emoji('cross')} حسابك محظور. تواصل مع الدعم.")
                return
            
            # جلب المستخدم
            user = await context.bot_data['db'].get_user(user_id)
            if not user:
                user = User(
                    user_id=user_id,
                    username=update.effective_user.username,
                    first_name=update.effective_user.first_name
                )
                await context.bot_data['db'].add_user(user)
            
            # فحص التفعيل
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

# ==================== Command Handlers ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية المحسن مع إصلاح Markdown"""
    user_id = update.effective_user.id
    
    user = await context.bot_data['db'].get_user(user_id)
    if not user:
        user = User(
            user_id=user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name
        )
        await context.bot_data['db'].add_user(user)
    
    # الحصول على سعر الذهب الحالي للعرض
    try:
        gold_price = await context.bot_data['gold_price_manager'].get_gold_price()
        price_display = f"{emoji('gold')} السعر الحالي: ${gold_price.price}\n{emoji('chart')} التغيير: {gold_price.change_24h:+.2f} ({gold_price.change_percentage:+.2f}%)"
    except:
        price_display = f"{emoji('gold')} السعر: يتم التحديث..."

    is_activated = (user.license_key and user.is_activated) or user_id == Config.MASTER_USER_ID
    
    if is_activated:
        # للمستخدمين المفعلين
        key_info = await context.bot_data['license_manager'].get_key_info(user.license_key) if user.license_key else None
        remaining_msgs = key_info['remaining_total'] if key_info else "∞"

        welcome_message = f"""╔══════════════════════════════════════╗
║     {emoji('fire')} <b>مرحباً في عالم النخبة</b> {emoji('fire')}     ║
╚══════════════════════════════════════╝

{emoji('wave')} أهلاً وسهلاً <b>{update.effective_user.first_name}</b>!

{price_display}

┌─────────────────────────────────────┐
│  {emoji('check')} <b>حسابك مُفعَّل ومجهز للعمل</b>   │
│  {emoji('target')} الأسئلة المتبقية: <b>{remaining_msgs}</b>        │
│  {emoji('info')} المفتاح ينتهي بعد استنفاد الأسئلة   │
└─────────────────────────────────────┘

{emoji('target')} <b>اختر نوع التحليل المطلوب:</b>"""
    else:
        # للمستخدمين غير المفعلين
        welcome_message = f"""╔══════════════════════════════════════╗
║   {emoji('diamond')} <b>Gold Nightmare Academy</b> {emoji('diamond')}   ║
║     أقوى منصة تحليل الذهب بالعالم     ║
╚══════════════════════════════════════╝

{emoji('wave')} مرحباً <b>{update.effective_user.first_name}</b>!

{price_display}

┌─────────── {emoji('trophy')} <b>لماذا نحن الأفضل؟</b> ───────────┐
│                                               │
│ {emoji('brain')} <b>ذكاء اصطناعي متطور</b> - Claude 4 Sonnet   │
│ {emoji('chart')} <b>تحليل متعدد الأطر الزمنية</b> بدقة 95%+     │
│ {emoji('target')} <b>نقاط دخول وخروج</b> بالسنت الواحد          │
│ {emoji('shield')} <b>إدارة مخاطر احترافية</b> مؤسسية           │
│ {emoji('up_arrow')} <b>توقعات مستقبلية</b> مع نسب ثقة دقيقة        │
│ {emoji('fire')} <b>تحليل شامل متقدم</b> للمحترفين              │
│                                               │
└───────────────────────────────────────────────┘

{emoji('gift')} <b>عرض محدود - مفاتيح متاحة الآن!</b>

{emoji('key')} كل مفتاح يعطيك:
   {emoji('zap')} 50 تحليل احترافي كامل
   {emoji('brain')} تحليل بالذكاء الاصطناعي المتقدم
   {emoji('chart')} تحليل متعدد الأطر الزمنية
   {emoji('target')} وصول للتحليل الشامل المتقدم
   {emoji('phone')} دعم فني مباشر
   {emoji('info')} المفتاح ينتهي بعد 50 سؤال

{emoji('info')} <b>للحصول على مفتاح التفعيل:</b>
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

async def license_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر تفعيل المفتاح"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            f"{emoji('key')} تفعيل مفتاح الترخيص\n\n"
            "الاستخدام: /license مفتاح_التفعيل\n\n"
            "مثال: /license GOLD-ABC1-DEF2-GHI3"
        )
        return
    
    license_key = context.args[0].upper().strip()
    license_manager = context.bot_data['license_manager']
    
    is_valid, message = await license_manager.validate_key(license_key, user_id)
    
    if not is_valid:
        await update.message.reply_text(f"{emoji('cross')} فشل التفعيل\n\n{message}")
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
{emoji('info')} المفتاح ينتهي بعد استنفاد الأسئلة

{emoji('star')} يمكنك الآن استخدام البوت والحصول على التحليلات المتقدمة!"""

    await update.message.reply_text(
        success_message,
        reply_markup=create_main_keyboard(user)
    )
    
    # حذف الرسالة لحماية المفتاح
    try:
        await update.message.delete()
    except:
        pass

@admin_only
async def create_keys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء مفاتيح جديدة"""
    count = 1
    total_limit = 50
    
    if context.args:
        try:
            count = int(context.args[0])
            if len(context.args) > 1:
                total_limit = int(context.args[1])
        except ValueError:
            await update.message.reply_text(f"{emoji('cross')} استخدم: /createkeys [عدد] [حد_إجمالي]\nمثال: /createkeys 10 50")
            return
    
    if count > 50:
        await update.message.reply_text(f"{emoji('cross')} لا يمكن إنشاء أكثر من 50 مفتاح")
        return
    
    license_manager = context.bot_data['license_manager']
    
    status_msg = await update.message.reply_text(f"{emoji('clock')} جاري إنشاء {count} مفتاح...")
    
    created_keys = []
    for i in range(count):
        key = await license_manager.create_new_key(
            total_limit=total_limit,
            notes=f"مفتاح مُنشأ بواسطة المشرف - {datetime.now().strftime('%Y-%m-%d')}"
        )
        created_keys.append(key)
    
    keys_text = "\n".join([f"{i+1}. {key}" for i, key in enumerate(created_keys)])
    
    result_message = f"""{emoji('check')} تم إنشاء {count} مفتاح بنجاح!

{emoji('chart')} الحد الإجمالي: {total_limit} أسئلة لكل مفتاح
{emoji('info')} المفتاح ينتهي بعد استنفاد الأسئلة

{emoji('key')} المفاتيح:
{keys_text}

{emoji('info')} تعليمات للمستخدمين:
• كل مفتاح يعطي {total_limit} سؤال إجمالي
• استخدام: /license GOLD-XXXX-XXXX-XXXX"""
    
    await status_msg.edit_text(result_message)

@admin_only
async def keys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع المفاتيح للمشرف"""
    license_manager = context.bot_data['license_manager']
    
    if not license_manager.license_keys:
        await update.message.reply_text(f"{emoji('cross')} لا توجد مفاتيح")
        return
    
    # إعداد الرسالة
    message = f"{emoji('key')} جميع مفاتيح التفعيل:\n\n"
    
    # إحصائيات عامة
    stats = await license_manager.get_all_keys_stats()
    message += f"{emoji('chart')} الإحصائيات:\n"
    message += f"• إجمالي المفاتيح: {stats['total_keys']}\n"
    message += f"• المفاتيح المستخدمة: {stats['used_keys']}\n"
    message += f"• المفاتيح الفارغة: {stats['unused_keys']}\n"
    message += f"• المفاتيح المنتهية: {stats['expired_keys']}\n"
    message += f"• الاستخدام الإجمالي: {stats['total_usage']}\n"
    message += f"• المتاح الإجمالي: {stats['total_available']}\n\n"
    
    # عرض أول 10 مفاتيح مع تفاصيل كاملة
    count = 0
    for key, license_key in license_manager.license_keys.items():
        if count >= 10:  # عرض أول 10 فقط
            break
        count += 1
        
        status = f"{emoji('green_dot')} نشط" if license_key.is_active else f"{emoji('red_dot')} معطل"
        user_info = f"{emoji('users')} {license_key.username or 'لا يوجد'} (ID: {license_key.user_id})" if license_key.user_id else f"{emoji('prohibited')} غير مستخدم"
        usage = f"{license_key.used_total}/{license_key.total_limit}"
        
        message += f"{count:2d}. {key}\n"
        message += f"   {status} | {user_info}\n"
        message += f"   {emoji('chart')} الاستخدام: {usage}\n"
        message += f"   {emoji('calendar')} إنشاء: {license_key.created_date.strftime('%Y-%m-%d')}\n\n"
    
    if len(license_manager.license_keys) > 10:
        message += f"... و {len(license_manager.license_keys) - 10} مفاتيح أخرى\n\n"
    
    message += f"{emoji('info')} استخدم /unusedkeys للمفاتيح المتاحة فقط"
    
    await send_long_message(update, message)

@admin_only
async def unused_keys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المفاتيح غير المستخدمة فقط"""
    license_manager = context.bot_data['license_manager']
    
    unused_keys = [key for key, license_key in license_manager.license_keys.items() 
                   if not license_key.user_id and license_key.is_active]
    
    if not unused_keys:
        await update.message.reply_text(f"{emoji('cross')} لا توجد مفاتيح متاحة")
        return
    
    message = f"{emoji('prohibited')} المفاتيح المتاحة ({len(unused_keys)} مفتاح):\n\n"
    
    for i, key in enumerate(unused_keys, 1):
        license_key = license_manager.license_keys[key]
        message += f"{i:2d}. {key}\n"
        message += f"    {emoji('chart')} الحد الإجمالي: {license_key.total_limit} أسئلة\n"
        message += f"    {emoji('calendar')} تاريخ الإنشاء: {license_key.created_date.strftime('%Y-%m-%d')}\n\n"
    
    message += f"""{emoji('info')} تعليمات إعطاء المفاتيح:
انسخ مفتاح وأرسله للمستخدم مع التعليمات:

```
{emoji('key')} مفتاح التفعيل الخاص بك:
GOLD-XXXX-XXXX-XXXX

{emoji('folder')} كيفية الاستخدام:
/license GOLD-XXXX-XXXX-XXXX

{emoji('warning')} ملاحظات مهمة:
• لديك 50 سؤال إجمالي
• {emoji('info')} المفتاح ينتهي بعد استنفاد الأسئلة
```"""
    
    await send_long_message(update, message)

@admin_only
async def delete_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف مستخدم من مفتاح"""
    if not context.args:
        await update.message.reply_text(
            f"{emoji('cross')} حذف مستخدم من مفتاح\n\n"
            "الاستخدام: /deleteuser مفتاح_التفعيل\n\n"
            "مثال: /deleteuser GOLD-ABC1-DEF2-GHI3"
        )
        return
    
    license_key = context.args[0].upper().strip()
    license_manager = context.bot_data['license_manager']
    
    success, message = await license_manager.delete_user_by_key(license_key)
    
    await update.message.reply_text(message)

@admin_only
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء نسخة احتياطية"""
    try:
        db_manager = context.bot_data['db']
        license_manager = context.bot_data['license_manager']
        
        # إنشاء النسخة الاحتياطية
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'users': {str(k): {
                'user_id': v.user_id,
                'username': v.username,
                'first_name': v.first_name,
                'is_activated': v.is_activated,
                'activation_date': v.activation_date.isoformat() if v.activation_date else None,
                'total_requests': v.total_requests,
                'total_analyses': v.total_analyses,
                'license_key': v.license_key
            } for k, v in db_manager.users.items()},
            'license_keys': {k: {
                'key': v.key,
                'created_date': v.created_date.isoformat(),
                'total_limit': v.total_limit,
                'used_total': v.used_total,
                'user_id': v.user_id,
                'username': v.username,
                'is_active': v.is_active
            } for k, v in license_manager.license_keys.items()},
            'analyses_count': len(db_manager.analyses)
        }
        
        # حفظ في ملف
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        async with aiofiles.open(backup_filename, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(backup_data, ensure_ascii=False, indent=2))
        
        await update.message.reply_text(
            f"{emoji('check')} **تم إنشاء النسخة الاحتياطية**\n\n"
            f"{emoji('folder')} الملف: `{backup_filename}`\n"
            f"{emoji('users')} المستخدمين: {len(backup_data['users'])}\n"
            f"{emoji('key')} المفاتيح: {len(backup_data['license_keys'])}\n"
            f"{emoji('up_arrow')} التحليلات: {backup_data['analyses_count']}"
        )
        
    except Exception as e:
        logger.error(f"Backup error: {e}")
        await update.message.reply_text(f"{emoji('cross')} خطأ في إنشاء النسخة الاحتياطية: {str(e)}")

@admin_only 
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات سريعة للأدمن"""
    try:
        db_manager = context.bot_data['db']
        license_manager = context.bot_data['license_manager']
        
        # إحصائيات أساسية
        total_users = len(db_manager.users)
        active_users = len([u for u in db_manager.users.values() if u.is_activated])
        total_keys = len(license_manager.license_keys)
        used_keys = len([k for k in license_manager.license_keys.values() if k.user_id])
        
        # آخر 24 ساعة
        last_24h = datetime.now() - timedelta(hours=24)
        recent_analyses = [a for a in db_manager.analyses if a.timestamp > last_24h]
        nightmare_analyses = [a for a in recent_analyses if a.analysis_type == "NIGHTMARE"]
        
        # استخدام إجمالي
        total_usage = sum(k.used_total for k in license_manager.license_keys.values())
        
        stats_text = f"""{emoji('chart')} **إحصائيات سريعة**

{emoji('users')} **المستخدمين:**
• الإجمالي: {total_users}
• المفعلين: {active_users}
• النسبة: {active_users/total_users*100:.1f}%

{emoji('key')} **المفاتيح:**
• الإجمالي: {total_keys}
• المستخدمة: {used_keys}
• المتاحة: {total_keys - used_keys}

{emoji('progress')} **آخر 24 ساعة:**
• التحليلات: {len(recent_analyses)}
• التحليلات الخاصة: {len(nightmare_analyses)}
• الاستخدام الإجمالي: {total_usage}

{emoji('clock')} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        await update.message.reply_text(stats_text)
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        await update.message.reply_text(f"{emoji('cross')} خطأ في الإحصائيات: {str(e)}")

# ==================== Enhanced Handler Functions ====================
async def handle_demo_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج التحليل التجريبي - مرة واحدة فقط"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # التحقق من الاستخدام السابق - مرة واحدة فقط
    demo_usage = context.user_data.get('demo_usage', 0)
    
    if demo_usage >= 1:  # مرة واحدة فقط!
        await query.edit_message_text(
            f"""{emoji('stop')} انتهت الفرصة التجريبية

لقد استخدمت التحليل التجريبي المجاني مسبقاً (مرة واحدة فقط).

{emoji('fire')} للحصول على تحليلات لا محدودة:
احصل على مفتاح تفعيل من المطور

{emoji('diamond')} مع المفتاح ستحصل على:
• 50 تحليل احترافي كامل
• تحليل بالذكاء الاصطناعي المتقدم
• جميع أنواع التحليل (سريع، شامل، سكالب، سوينج)
• التحليل الشامل المتقدم للمحترفين
• دعم فني مباشر

{emoji('admin')} تواصل مع المطور: @Odai_xau""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('phone')} تواصل مع Odai", url="https://t.me/Odai_xau")],
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")]
            ])
        )
        return
    
    # رسالة التحضير
    await query.edit_message_text(
        f"""{emoji('target')} تحليل تجريبي مجاني - الفرصة الوحيدة

{emoji('zap')} جاري تحضير تحليل احترافي للذهب...
{emoji('star')} هذه فرصتك الوحيدة للتجربة المجانية

{emoji('clock')} يرجى الانتظار..."""
    )
    
    try:
        # الحصول على السعر
        price = await context.bot_data['gold_price_manager'].get_gold_price()
        if not price:
            await query.edit_message_text(f"{emoji('cross')} لا يمكن الحصول على السعر حالياً.")
            return
        
        # تحليل تجريبي مبسط
        demo_prompt = """قدم تحليل سريع احترافي للذهب الآن مع:
        - توصية واضحة (Buy/Sell/Hold)
        - سبب قوي واحد
        - هدف واحد ووقف خسارة
        - نسبة ثقة
        - تنسيق جميل ومنظم"""
        
        result = await context.bot_data['claude_manager'].analyze_gold(
            prompt=demo_prompt,
            gold_price=price,
            analysis_type=AnalysisType.QUICK
        )
        
        # رسالة تسويقية قوية
        demo_result = f"""{emoji('target')} تحليل تجريبي مجاني - Gold Nightmare

{result}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{emoji('fire')} هذا مجرد طعم من قوة تحليلاتنا الكاملة!

{emoji('diamond')} مع مفتاح التفعيل ستحصل على:
{emoji('zap')} 50 تحليل احترافي كامل
{emoji('chart')} تحليل شامل لجميع الأطر الزمنية  
{emoji('target')} نقاط دخول وخروج بالسنت الواحد
{emoji('shield')} إدارة مخاطر احترافية
{emoji('crystal_ball')} توقعات ذكية مع احتماليات
{emoji('news')} تحليل تأثير الأخبار
{emoji('refresh')} اكتشاف نقاط الانعكاس
{emoji('fire')} التحليل الشامل المتقدم

{emoji('warning')} هذه كانت فرصتك الوحيدة للتجربة المجانية

{emoji('rocket')} انضم لمجتمع النخبة الآن!"""

        await query.edit_message_text(
            demo_result,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('key')} احصل على مفتاح", callback_data="how_to_get_license")],
                [InlineKeyboardButton(f"{emoji('phone')} تواصل مع Odai", url="https://t.me/Odai_xau")],
                [InlineKeyboardButton(f"{emoji('back')} رجوع للقائمة", callback_data="back_main")]
            ])
        )
        
        # تسجيل الاستخدام
        context.user_data['demo_usage'] = 1
        
    except Exception as e:
        logger.error(f"Error in demo analysis: {e}")
        await query.edit_message_text(
            f"""{emoji('cross')} حدث خطأ في التحليل التجريبي.

{emoji('refresh')} يمكنك المحاولة مرة أخرى أو التواصل مع الدعم.""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('refresh')} محاولة أخرى", callback_data="demo_analysis")],
                [InlineKeyboardButton(f"{emoji('phone')} الدعم", url="https://t.me/Odai_xau")],
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")]
            ])
        )

async def handle_nightmare_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج التحليل الشامل المتقدم"""
    query = update.callback_query
    user = context.user_data.get('user')
    
    if not user or not user.is_activated:
        await query.answer(f"{emoji('lock')} يتطلب مفتاح تفعيل", show_alert=True)
        return
    
    # فحص واستخدام المفتاح
    license_manager = context.bot_data['license_manager']
    success, message = await license_manager.use_key(
        user.license_key, 
        user.user_id,
        user.username,
        "nightmare_analysis"
    )
    
    if not success:
        await query.edit_message_text(message)
        return
    
    # رسالة تحضير خاصة للتحليل الشامل
    await query.edit_message_text(
        f"{emoji('fire')}{emoji('fire')}{emoji('fire')} **التحليل الشامل المتقدم** {emoji('fire')}{emoji('fire')}{emoji('fire')}\n\n"
        f"{emoji('zap')} تحضير التحليل الشامل المتقدم...\n"
        f"{emoji('magnifier')} تحليل جميع الأطر الزمنية...\n"
        f"{emoji('chart')} حساب مستويات الدعم والمقاومة...\n"
        f"{emoji('target')} تحديد نقاط الدخول الدقيقة...\n"
        f"{emoji('shield')} إعداد استراتيجيات إدارة المخاطر...\n"
        f"{emoji('crystal_ball')} حساب التوقعات والاحتماليات...\n\n"
        f"{emoji('clock')} هذا التحليل يستغرق وقتاً أطول لضمان الدقة..."
    )
    
    try:
        price = await context.bot_data['gold_price_manager'].get_gold_price()
        if not price:
            await query.edit_message_text(f"{emoji('cross')} لا يمكن الحصول على السعر حالياً.")
            return
        
        # التحليل الشامل المتقدم
        nightmare_prompt = f"""أريد التحليل الشامل المتقدم للذهب - التحليل الأكثر تقدماً وتفصيلاً مع:

        1. تحليل شامل لجميع الأطر الزمنية (M5, M15, H1, H4, D1) مع نسب ثقة دقيقة
        2. مستويات دعم ومقاومة متعددة مع قوة كل مستوى
        3. نقاط دخول وخروج بالسنت الواحد مع أسباب كل نقطة
        4. سيناريوهات متعددة (صاعد، هابط، عرضي) مع احتماليات
        5. استراتيجيات سكالبينج وسوينج
        6. تحليل نقاط الانعكاس المحتملة
        7. مناطق العرض والطلب المؤسسية
        8. توقعات قصيرة ومتوسطة المدى
        9. إدارة مخاطر تفصيلية
        10. جداول منظمة وتنسيق احترافي

        {Config.NIGHTMARE_TRIGGER}
        
        اجعله التحليل الأقوى والأشمل على الإطلاق!"""
        
        result = await context.bot_data['claude_manager'].analyze_gold(
            prompt=nightmare_prompt,
            gold_price=price,
            analysis_type=AnalysisType.NIGHTMARE,
            user_settings=user.settings
        )
        
        # إضافة توقيع خاص للتحليل الشامل
        nightmare_result = f"""{result}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{emoji('fire')} **تم بواسطة Gold Nightmare Academy** {emoji('fire')}
{emoji('diamond')} **التحليل الشامل المتقدم - للمحترفين فقط**
{emoji('zap')} **تحليل متقدم بالذكاء الاصطناعي Claude 4**
{emoji('target')} **دقة التحليل: 95%+ - مضمون الجودة**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{emoji('warning')} **تنبيه هام:** هذا تحليل تعليمي متقدم وليس نصيحة استثمارية
{emoji('info')} **استخدم إدارة المخاطر دائماً ولا تستثمر أكثر مما تستطيع خسارته**"""

        await query.edit_message_text(nightmare_result)
        
    except Exception as e:
        logger.error(f"Error in nightmare analysis: {e}")
        await query.edit_message_text(f"{emoji('cross')} حدث خطأ في التحليل الشامل.")

async def handle_enhanced_price_display(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج عرض السعر المحسن"""
    query = update.callback_query
    
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
        
        # إنشاء رسالة السعر المتقدمة
        price_message = f"""╔══════════════════════════════════════╗
║       {emoji('gold')} **سعر الذهب المباشر** {emoji('gold')}       ║
╚══════════════════════════════════════╝

{emoji('diamond')} **السعر الحالي:** ${price.price:.2f}
{trend_color} **الاتجاه:** {trend_text} {trend_emoji}
{emoji('chart')} **التغيير 24س:** {price.change_24h:+.2f} ({price.change_percentage:+.2f}%)

{emoji('top')} **أعلى سعر:** ${price.high_24h:.2f}
{emoji('bottom')} **أدنى سعر:** ${price.low_24h:.2f}
{emoji('clock')} **التحديث:** {price.timestamp.strftime('%H:%M:%S')}

{emoji('info')} **للحصول على تحليل متقدم استخدم الأزرار أدناه**"""
        
        # أزرار تفاعلية للسعر
        price_keyboard = [
            [
                InlineKeyboardButton(f"{emoji('refresh')} تحديث السعر", callback_data="price_now"),
                InlineKeyboardButton(f"{emoji('zap')} تحليل سريع", callback_data="analysis_quick")
            ],
            [
                InlineKeyboardButton(f"{emoji('chart')} تحليل شامل", callback_data="analysis_detailed")
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

async def handle_enhanced_key_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج معلومات المفتاح - نظام 50 سؤال"""
    query = update.callback_query
    user = context.user_data.get('user')
    
    if not user or not user.license_key:
        await query.edit_message_text(
            f"""{emoji('cross')} لا يوجد مفتاح مفعل

للحصول على مفتاح تفعيل تواصل مع المطور""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('phone')} تواصل مع Odai", url="https://t.me/Odai_xau")],
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")]
            ])
        )
        return
    
    try:
        key_info = await context.bot_data['license_manager'].get_key_info(user.license_key)
        if not key_info:
            await query.edit_message_text(f"{emoji('cross')} لا يمكن جلب معلومات المفتاح")
            return
        
        # حساب النسبة المئوية
        usage_percentage = (key_info['used_total'] / key_info['total_limit']) * 100
        
        key_info_message = f"""╔══════════════════════════════════════╗
║        {emoji('key')} معلومات مفتاح التفعيل {emoji('key')}        ║
╚══════════════════════════════════════╝

{emoji('users')} المعرف: {key_info['username'] or 'غير محدد'}
{emoji('key')} المفتاح: {key_info['key'][:8]}***
{emoji('calendar')} تاريخ التفعيل: {key_info['created_date']}

{emoji('chart')} الاستخدام: {key_info['used_total']}/{key_info['total_limit']} أسئلة
{emoji('up_arrow')} المتبقي: {key_info['remaining_total']} أسئلة
{emoji('percentage')} نسبة الاستخدام: {usage_percentage:.1f}%

{emoji('diamond')} Gold Nightmare Academy - عضوية نشطة
{emoji('rocket')} أنت جزء من مجتمع النخبة في تحليل الذهب!"""
        
        await query.edit_message_text(
            key_info_message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('refresh')} تحديث المعلومات", callback_data="key_info")],
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in enhanced key info: {e}")
        await query.edit_message_text(f"{emoji('cross')} خطأ في جلب معلومات المفتاح")

# ==================== Admin Handler Functions ====================
async def handle_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج إحصائيات الإدارة"""
    query = update.callback_query
    
    try:
        db_manager = context.bot_data['db']
        license_manager = context.bot_data['license_manager']
        
        # الحصول على الإحصائيات
        db_stats = await db_manager.get_stats()
        keys_stats = await license_manager.get_all_keys_stats()
        
        # آخر 24 ساعة
        last_24h = datetime.now() - timedelta(hours=24)
        recent_analyses = [a for a in db_manager.analyses if a.timestamp > last_24h]
        
        stats_message = f"""{emoji('chart')} **إحصائيات شاملة للبوت**

{emoji('users')} **المستخدمين:**
• إجمالي المستخدمين: {db_stats['total_users']}
• المستخدمين النشطين: {db_stats['active_users']}
• معدل التفعيل: {db_stats['activation_rate']}

{emoji('key')} **المفاتيح:**
• إجمالي المفاتيح: {keys_stats['total_keys']}
• المفاتيح المستخدمة: {keys_stats['used_keys']}
• المفاتيح المتاحة: {keys_stats['unused_keys']}
• المفاتيح المنتهية: {keys_stats['expired_keys']}

{emoji('chart')} **الاستخدام:**
• الاستخدام الإجمالي: {keys_stats['total_usage']}
• المتاح الإجمالي: {keys_stats['total_available']}
• متوسط الاستخدام: {keys_stats['avg_usage_per_key']:.1f}

{emoji('up_arrow')} **التحليلات:**
• إجمالي التحليلات: {db_stats['total_analyses']}
• تحليلات آخر 24 ساعة: {len(recent_analyses)}

{emoji('clock')} آخر تحديث: {datetime.now().strftime('%H:%M:%S')}"""
        
        await query.edit_message_text(
            stats_message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('refresh')} تحديث الإحصائيات", callback_data="admin_stats")],
                [InlineKeyboardButton(f"{emoji('back')} رجوع للإدارة", callback_data="admin_panel")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in admin stats: {e}")
        await query.edit_message_text(
            f"{emoji('cross')} خطأ في جلب الإحصائيات: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_panel")]
            ])
        )

async def handle_admin_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج إدارة المفاتيح"""
    query = update.callback_query
    
    await query.edit_message_text(
        f"{emoji('key')} إدارة المفاتيح\n\nاختر العملية المطلوبة:",
        reply_markup=create_keys_management_keyboard()
    )

async def handle_keys_show_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع المفاتيح"""
    query = update.callback_query
    license_manager = context.bot_data['license_manager']
    
    if not license_manager.license_keys:
        await query.edit_message_text(
            f"{emoji('cross')} لا توجد مفاتيح",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_keys")]
            ])
        )
        return
    
    # عرض أول 5 مفاتيح
    message = f"{emoji('key')} أول 5 مفاتيح:\n\n"
    
    count = 0
    for key, license_key in license_manager.license_keys.items():
        if count >= 5:
            break
        count += 1
        
        status = f"{emoji('green_dot')}" if license_key.is_active else f"{emoji('red_dot')}"
        user_info = f"({license_key.username})" if license_key.username else "(غير مستخدم)"
        
        message += f"{count}. {key[:15]}...\n"
        message += f"   {status} {user_info}\n"
        message += f"   {license_key.used_total}/{license_key.total_limit}\n\n"
    
    if len(license_manager.license_keys) > 5:
        message += f"... و {len(license_manager.license_keys) - 5} مفاتيح أخرى"
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_keys")]
        ])
    )

async def handle_keys_show_unused(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المفاتيح المتاحة"""
    query = update.callback_query
    license_manager = context.bot_data['license_manager']
    
    unused_keys = [key for key, license_key in license_manager.license_keys.items() 
                   if not license_key.user_id and license_key.is_active]
    
    if not unused_keys:
        await query.edit_message_text(
            f"{emoji('cross')} لا توجد مفاتيح متاحة",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_keys")]
            ])
        )
        return
    
    message = f"{emoji('prohibited')} المفاتيح المتاحة ({len(unused_keys)}):\n\n"
    
    for i, key in enumerate(unused_keys[:10], 1):  # أول 10
        license_key = license_manager.license_keys[key]
        message += f"{i}. {key}\n"
        message += f"   {emoji('chart')} {license_key.total_limit} أسئلة\n\n"
    
    if len(unused_keys) > 10:
        message += f"... و {len(unused_keys) - 10} مفاتيح أخرى"
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_keys")]
        ])
    )

async def handle_keys_create_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """واجهة إنشاء مفاتيح جديدة"""
    query = update.callback_query
    
    await query.edit_message_text(
        f"""{emoji('key')} إنشاء مفاتيح جديدة

لإنشاء مفاتيح جديدة، استخدم الأمر:
`/createkeys [العدد] [الحد_الإجمالي]`

مثال:
`/createkeys 10 50`

هذا سينشئ 10 مفاتيح، كل مفتاح يعطي 50 سؤال إجمالي""",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_keys")]
        ])
    )

async def handle_keys_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات المفاتيح"""
    query = update.callback_query
    license_manager = context.bot_data['license_manager']
    
    try:
        stats = await license_manager.get_all_keys_stats()
        
        stats_message = f"""{emoji('chart')} إحصائيات المفاتيح

{emoji('key')} **المفاتيح:**
• الإجمالي: {stats['total_keys']}
• النشطة: {stats['active_keys']}
• المستخدمة: {stats['used_keys']}
• المتاحة: {stats['unused_keys']}
• المنتهية: {stats['expired_keys']}

{emoji('chart')} **الاستخدام:**
• الإجمالي: {stats['total_usage']}
• المتاح: {stats['total_available']}
• المتوسط: {stats['avg_usage_per_key']:.1f}

{emoji('percentage')} **النسب:**
• نسبة الاستخدام: {(stats['used_keys']/stats['total_keys']*100):.1f}%
• نسبة المنتهية: {(stats['expired_keys']/stats['total_keys']*100):.1f}%"""
        
        await query.edit_message_text(
            stats_message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('refresh')} تحديث", callback_data="keys_stats")],
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_keys")]
            ])
        )
        
    except Exception as e:
        await query.edit_message_text(
            f"{emoji('cross')} خطأ في جلب إحصائيات المفاتيح: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_keys")]
            ])
        )

async def handle_keys_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """واجهة حذف مستخدم من مفتاح"""
    query = update.callback_query
    
    await query.edit_message_text(
        f"""{emoji('cross')} حذف مستخدم من مفتاح

لحذف مستخدم وإعادة تعيين مفتاحه، استخدم:
`/deleteuser GOLD-XXXX-XXXX-XXXX`

{emoji('warning')} تحذير:
• سيتم حذف المستخدم من المفتاح
• سيتم إعادة تعيين عداد الاستخدام إلى 0
• المفتاح سيصبح متاحاً لمستخدم جديد""",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_keys")]
        ])
    )

async def handle_create_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء نسخة احتياطية من واجهة الإدارة"""
    query = update.callback_query
    
    await query.edit_message_text(
        f"{emoji('backup')} جاري إنشاء النسخة الاحتياطية...",
    )
    
    try:
        db_manager = context.bot_data['db']
        license_manager = context.bot_data['license_manager']
        
        # إنشاء النسخة الاحتياطية
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'users': {str(k): {
                'user_id': v.user_id,
                'username': v.username,
                'first_name': v.first_name,
                'is_activated': v.is_activated,
                'activation_date': v.activation_date.isoformat() if v.activation_date else None,
                'total_requests': v.total_requests,
                'total_analyses': v.total_analyses,
                'license_key': v.license_key
            } for k, v in db_manager.users.items()},
            'license_keys': {k: {
                'key': v.key,
                'created_date': v.created_date.isoformat(),
                'total_limit': v.total_limit,
                'used_total': v.used_total,
                'user_id': v.user_id,
                'username': v.username,
                'is_active': v.is_active,
                'notes': v.notes
            } for k, v in license_manager.license_keys.items()},
            'analyses_count': len(db_manager.analyses)
        }
        
        # حفظ في ملف
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        async with aiofiles.open(backup_filename, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(backup_data, ensure_ascii=False, indent=2))
        
        await query.edit_message_text(
            f"""{emoji('check')} تم إنشاء النسخة الاحتياطية

{emoji('folder')} الملف: {backup_filename}
{emoji('users')} المستخدمين: {len(backup_data['users'])}
{emoji('key')} المفاتيح: {len(backup_data['license_keys'])}
{emoji('up_arrow')} التحليلات: {backup_data['analyses_count']}
{emoji('clock')} الوقت: {datetime.now().strftime('%H:%M:%S')}""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('back')} رجوع للإدارة", callback_data="admin_panel")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Backup error: {e}")
        await query.edit_message_text(
            f"{emoji('cross')} خطأ في إنشاء النسخة الاحتياطية: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_panel")]
            ])
        )

# ==================== Message Handlers ====================
@require_activation_with_key_usage("text_analysis")
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية"""
    user = context.user_data['user']
    
    # فحص الحد المسموح
    allowed, message = context.bot_data['rate_limiter'].is_allowed(user.user_id, user)
    if not allowed:
        await update.message.reply_text(message)
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # فحص التحليل السري (بدون إظهار للمستخدم)
    is_nightmare = Config.NIGHTMARE_TRIGGER in update.message.text
    
    if is_nightmare:
        processing_msg = await update.message.reply_text(
            f"{emoji('fire')}{emoji('fire')}{emoji('fire')} تحضير التحليل الشامل المتقدم {emoji('fire')}{emoji('fire')}{emoji('fire')}\n\n"
            f"{emoji('zap')} جمع البيانات من جميع الأطر الزمنية...\n"
            f"{emoji('chart')} تحليل المستويات والنماذج الفنية...\n"
            f"{emoji('target')} حساب نقاط الدخول والخروج الدقيقة...\n\n"
            f"{emoji('clock')} التحليل الشامل يحتاج وقت أطول للدقة القصوى..."
        )
    else:
        processing_msg = await update.message.reply_text(f"{emoji('brain')} جاري التحليل الاحترافي...")
    
    try:
        price = await context.bot_data['gold_price_manager'].get_gold_price()
        if not price:
            await processing_msg.edit_text(f"{emoji('cross')} لا يمكن الحصول على السعر حالياً.")
            return
        
        # تحديد نوع التحليل من الكلمات المفتاحية
        text_lower = update.message.text.lower()
        analysis_type = AnalysisType.DETAILED  # افتراضي
        
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
        
        await send_long_message(update, result)
        
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

@require_activation_with_key_usage("image_analysis")
async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الصور"""
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
            f"{emoji('magnifier')} تحليل النماذج الفنية والمستويات..."
        )
    else:
        processing_msg = await update.message.reply_text(f"{emoji('camera')} جاري تحليل الشارت بالذكاء الاصطناعي...")
    
    try:
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        image_data = await photo_file.download_as_bytearray()
        
        image_base64 = ImageProcessor.process_image(image_data)
        if not image_base64:
            await processing_msg.edit_text(f"{emoji('cross')} لا يمكن معالجة الصورة.")
            return
        
        price = await context.bot_data['gold_price_manager'].get_gold_price()
        if not price:
            await processing_msg.edit_text(f"{emoji('cross')} لا يمكن الحصول على السعر حالياً.")
            return
        
        caption = caption or "حلل هذا الشارت بالتفصيل الاحترافي"
        
        # تحديد نوع التحليل
        analysis_type = AnalysisType.CHART
        if Config.NIGHTMARE_TRIGGER in caption:
            analysis_type = AnalysisType.NIGHTMARE
        
        result = await context.bot_data['claude_manager'].analyze_gold(
            prompt=caption,
            gold_price=price,
            image_base64=image_base64,
            analysis_type=analysis_type,
            user_settings=user.settings
        )
        
        await processing_msg.delete()
        
        await send_long_message(update, result)
        
        # حفظ التحليل
        analysis = Analysis(
            id=f"{user.user_id}_{datetime.now().timestamp()}",
            user_id=user.user_id,
            timestamp=datetime.now(),
            analysis_type="image",
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
        await processing_msg.edit_text(f"{emoji('cross')} حدث خطأ أثناء تحليل الصورة.")

# ==================== Callback Query Handler ====================
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأزرار"""
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
    allowed_without_license = ["price_now", "how_to_get_license", "back_main", "demo_analysis"]
    
    # فحص التفعيل للأوامر المحمية
    if (user_id != Config.MASTER_USER_ID and 
        (not user.license_key or not user.is_activated) and 
        data not in allowed_without_license):
        
        not_activated_message = f"""{emoji('key')} يتطلب مفتاح تفعيل

لاستخدام هذه الميزة، يجب إدخال مفتاح تفعيل صالح.
استخدم: /license مفتاح_التفعيل

{emoji('info')} للحصول على مفتاح تواصل مع:
{emoji('admin')} Odai - @Odai_xau

{emoji('fire')} مع كل مفتاح ستحصل على تحليلات متقدمة احترافية!"""
        
        await query.edit_message_text(
            not_activated_message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('key')} كيف أحصل على مفتاح؟", callback_data="how_to_get_license")],
                [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")]
            ])
        )
        return
    
    # فحص استخدام المفتاح للعمليات المتقدمة
    advanced_operations = [
        "analysis_quick", "analysis_scalping", "analysis_detailed",
        "analysis_forecast", "analysis_news", "analysis_swing", "analysis_reversal"
    ]
    
    if user_id != Config.MASTER_USER_ID and data in advanced_operations and user.license_key:
        license_manager = context.bot_data['license_manager']
        success, use_message = await license_manager.use_key(
            user.license_key, 
            user_id,
            user.username,
            f"callback_{data}"
        )
        
        if not success:
            await query.edit_message_text(use_message)
            return
    
    try:
        if data == "demo_analysis":
            await handle_demo_analysis(update, context)

        elif data == "nightmare_analysis": 
            await handle_nightmare_analysis(update, context)

        elif data == "price_now":
            await handle_enhanced_price_display(update, context)
            
        elif data == "how_to_get_license":
            help_text = f"""{emoji('key')} كيفية الحصول على مفتاح التفعيل

{emoji('diamond')} Gold Nightmare Bot يقدم تحليلات الذهب الأكثر دقة في العالم!

{emoji('phone')} للحصول على مفتاح تفعيل:

{emoji('admin')} تواصل مع Odai:
- Telegram: @Odai_xau
- Channel: @odai_xauusdt  
- Group: @odai_xau_usd

{emoji('gift')} ماذا تحصل عليه:
- {emoji('zap')} 50 تحليل احترافي إجمالي
- {emoji('brain')} تحليل بالذكاء الاصطناعي المتقدم
- {emoji('chart')} تحليل متعدد الأطر الزمنية
- {emoji('magnifier')} اكتشاف النماذج الفنية
- {emoji('target')} نقاط دخول وخروج دقيقة
- {emoji('shield')} إدارة مخاطر احترافية
- {emoji('fire')} التحليل الشامل المتقدم

{emoji('gold')} سعر خاص ومحدود!
{emoji('info')} المفتاح ينتهي بعد استنفاد 50 سؤال

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
            await handle_enhanced_key_info(update, context)
                        
        elif data == "back_main":
            main_message = f"""{emoji('trophy')} Gold Nightmare Bot

اختر الخدمة المطلوبة:"""
            
            await query.edit_message_text(
                main_message,
                reply_markup=create_main_keyboard(user)
            )
        
        elif data.startswith("analysis_"):
            analysis_type_map = {
                "analysis_quick": (AnalysisType.QUICK, f"{emoji('zap')} تحليل سريع"),
                "analysis_scalping": (AnalysisType.SCALPING, f"{emoji('target')} سكالبينج"),
                "analysis_detailed": (AnalysisType.DETAILED, f"{emoji('chart')} تحليل مفصل"),
                "analysis_swing": (AnalysisType.SWING, f"{emoji('up_arrow')} سوينج"),
                "analysis_forecast": (AnalysisType.FORECAST, f"{emoji('crystal_ball')} توقعات"),
                "analysis_reversal": (AnalysisType.REVERSAL, f"{emoji('refresh')} مناطق انعكاس"),
                "analysis_news": (AnalysisType.NEWS, f"{emoji('news')} تحليل الأخبار")
            }
            
            if data in analysis_type_map:
                analysis_type, type_name = analysis_type_map[data]
                
                processing_msg = await query.edit_message_text(
                    f"{emoji('brain')} جاري إعداد {type_name}...\n\n{emoji('clock')} يرجى الانتظار..."
                )
                
                price = await context.bot_data['gold_price_manager'].get_gold_price()
                if not price:
                    await processing_msg.edit_text(f"{emoji('cross')} لا يمكن الحصول على السعر حالياً.")
                    return
                
                # إنشاء prompt مناسب لنوع التحليل
                if analysis_type == AnalysisType.QUICK:
                    prompt = "تحليل سريع للذهب الآن مع توصية واضحة"
                elif analysis_type == AnalysisType.SCALPING:
                    prompt = "تحليل سكالبينج للذهب للـ 15 دقيقة القادمة مع نقاط دخول وخروج دقيقة"
                elif analysis_type == AnalysisType.SWING:
                    prompt = "تحليل سوينج للذهب للأيام والأسابيع القادمة"
                elif analysis_type == AnalysisType.FORECAST:
                    prompt = "توقعات الذهب لليوم والأسبوع القادم مع احتماليات"
                elif analysis_type == AnalysisType.REVERSAL:
                    prompt = "تحليل نقاط الانعكاس المحتملة للذهب مع مستويات الدعم والمقاومة"
                elif analysis_type == AnalysisType.NEWS:
                    prompt = "تحليل تأثير الأخبار الحالية على الذهب"
                else:
                    prompt = "تحليل شامل ومفصل للذهب مع جداول منظمة"
                
                result = await context.bot_data['claude_manager'].analyze_gold(
                    prompt=prompt,
                    gold_price=price,
                    analysis_type=analysis_type,
                    user_settings=user.settings
                )
                
                await processing_msg.edit_text(result)
                
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
                
                # إضافة زر رجوع
                keyboard = [[InlineKeyboardButton(f"{emoji('back')} رجوع للقائمة", callback_data="back_main")]]
                await query.edit_message_reply_markup(
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        
        elif data == "admin_panel" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(
                f"{emoji('admin')} لوحة الإدارة\n\nاختر العملية المطلوبة:",
                reply_markup=create_admin_keyboard()
            )
        
        # معالجات الإدارة
        elif data == "admin_stats" and user_id == Config.MASTER_USER_ID:
            await handle_admin_stats(update, context)
        
        elif data == "admin_keys" and user_id == Config.MASTER_USER_ID:
            await handle_admin_keys(update, context)
        
        elif data == "keys_show_all" and user_id == Config.MASTER_USER_ID:
            await handle_keys_show_all(update, context)
        
        elif data == "keys_show_unused" and user_id == Config.MASTER_USER_ID:
            await handle_keys_show_unused(update, context)
        
        elif data == "keys_create_prompt" and user_id == Config.MASTER_USER_ID:
            await handle_keys_create_prompt(update, context)
        
        elif data == "keys_stats" and user_id == Config.MASTER_USER_ID:
            await handle_keys_stats(update, context)
        
        elif data == "keys_delete_user" and user_id == Config.MASTER_USER_ID:
            await handle_keys_delete_user(update, context)
        
        elif data == "create_backup" and user_id == Config.MASTER_USER_ID:
            await handle_create_backup(update, context)
        
        # معالجات إدارية أخرى (يمكن تطويرها لاحقاً)
        elif data == "admin_users" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(
                f"{emoji('users')} إدارة المستخدمين\n\n{emoji('construction')} هذه الميزة قيد التطوير",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_panel")]
                ])
            )
        
        elif data == "admin_analyses" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(
                f"{emoji('up_arrow')} تقارير التحليل\n\n{emoji('construction')} هذه الميزة قيد التطوير",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_panel")]
                ])
            )
        
        elif data == "view_logs" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(
                f"{emoji('logs')} سجل الأخطاء\n\n{emoji('construction')} هذه الميزة قيد التطوير",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_panel")]
                ])
            )
        
        elif data == "system_settings" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(
                f"{emoji('gear')} إعدادات النظام\n\n{emoji('construction')} هذه الميزة قيد التطوير",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="admin_panel")]
                ])
            )
        
        elif data == "restart_bot" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(
                f"{emoji('refresh')} إعادة تشغيل البوت\n\n{emoji('warning')} هذه العملية ستوقف البوت مؤقتاً",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{emoji('check')} تأكيد إعادة التشغيل", callback_data="confirm_restart")],
                    [InlineKeyboardButton(f"{emoji('cross')} إلغاء", callback_data="admin_panel")]
                ])
            )
        
        elif data == "confirm_restart" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(f"{emoji('refresh')} جاري إعادة تشغيل البوت...")
            # هنا يمكن إضافة منطق إعادة التشغيل الفعلي
            
        elif data == "settings":
            await query.edit_message_text(
                f"{emoji('gear')} الإعدادات\n\n{emoji('construction')} هذه الميزة قيد التطوير",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{emoji('back')} رجوع", callback_data="back_main")]
                ])
            )
    
    except Exception as e:
        logger.error(f"Error in callback query handler: {e}")
        await query.edit_message_text(
            f"{emoji('cross')} حدث خطأ غير متوقع",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji('back')} رجوع للقائمة", callback_data="back_main")]
            ])
        )

# ==================== Admin Message Handler ====================
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج رسائل الأدمن للعمليات الخاصة"""
    user_id = update.effective_user.id
    
    # فقط للمشرف
    if user_id != Config.MASTER_USER_ID:
        return
    
    admin_action = context.user_data.get('admin_action')
    
    if admin_action == 'broadcast':
        # إرسال رسالة جماعية
        broadcast_text = update.message.text
        
        if broadcast_text.lower() == '/cancel':
            context.user_data.pop('admin_action', None)
            await update.message.reply_text(f"{emoji('cross')} تم إلغاء الرسالة الجماعية.")
            return
        
        db_manager = context.bot_data['db']
        active_users = [u for u in db_manager.users.values() if u.is_activated]
        
        status_msg = await update.message.reply_text(f"{emoji('envelope')} جاري الإرسال لـ {len(active_users)} مستخدم...")
        
        success_count = 0
        failed_count = 0
        
        broadcast_message = f"""{emoji('bell')} **رسالة من إدارة Gold Nightmare**

{broadcast_text}

━━━━━━━━━━━━━━━━━━━━━━━━━
{emoji('diamond')} Gold Nightmare Academy"""
        
        for user in active_users:
            try:
                await context.bot.send_message(
                    chat_id=user.user_id,
                    text=broadcast_message
                )
                success_count += 1
                await asyncio.sleep(0.1)  # تجنب spam limits
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to send broadcast to {user.user_id}: {e}")
        
        await status_msg.edit_text(
            f"{emoji('check')} **اكتملت الرسالة الجماعية**\n\n"
            f"{emoji('envelope')} تم الإرسال لـ: {success_count} مستخدم\n"
            f"{emoji('cross')} فشل الإرسال لـ: {failed_count} مستخدم\n\n"
            f"{emoji('chart')} معدل النجاح: {success_count/(success_count+failed_count)*100:.1f}%"
        )
        
        context.user_data.pop('admin_action', None)

# ==================== Error Handler ====================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأخطاء المحسن"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # إذا كان الخطأ في parsing، حاول إرسال رسالة بديلة
    if "Can't parse entities" in str(context.error):
        try:
            if update and hasattr(update, 'message') and update.message:
                await update.message.reply_text(
                    f"{emoji('cross')} حدث خطأ في تنسيق الرسالة. تم إرسال النص بدون تنسيق.\n"
                    "استخدم /start للمتابعة."
                )
        except:
            pass  # تجنب إرسال أخطاء إضافية

# ==================== Main Function for Render Webhook ====================
async def setup_webhook():
    """إعداد webhook وحذف أي polling سابق"""
    try:
        # حذف أي webhook سابق
        await application.bot.delete_webhook(drop_pending_updates=True)
        
        # تعيين webhook الجديد
        webhook_url = f"{Config.WEBHOOK_URL}/webhook"
        await application.bot.set_webhook(webhook_url)
        
        print(f"{emoji('check')} تم تعيين Webhook: {webhook_url}")
        
    except Exception as e:
        print(f"{emoji('cross')} خطأ في إعداد Webhook: {e}")

def main():
    """الدالة الرئيسية لـ Render Webhook"""
    
    # التحقق من متغيرات البيئة
    if not Config.TELEGRAM_BOT_TOKEN:
        print(f"{emoji('cross')} خطأ: TELEGRAM_BOT_TOKEN غير موجود")
        return
    
    if not Config.CLAUDE_API_KEY:
        print(f"{emoji('cross')} خطأ: CLAUDE_API_KEY غير موجود")
        return
    
    print(f"{emoji('rocket')} تشغيل Gold Nightmare Bot على Render...")
    print(f"{emoji('link')} إعداد Webhook للعمل على Render")
    
    # إنشاء التطبيق
    global application
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    # إنشاء المكونات
    cache_manager = CacheManager()
    db_manager = DatabaseManager(Config.DB_PATH)
    license_manager = LicenseManager(Config.KEYS_FILE)
    gold_price_manager = GoldPriceManager(cache_manager)
    claude_manager = ClaudeAIManager(cache_manager)
    rate_limiter = RateLimiter()
    security_manager = SecurityManager()
    
    # تحميل البيانات
    async def initialize_data():
        await db_manager.load_data()
        await license_manager.initialize()
    
    # تشغيل تحميل البيانات
    asyncio.get_event_loop().run_until_complete(initialize_data())
    
    # حفظ في bot_data
    application.bot_data.update({
        'db': db_manager,
        'license_manager': license_manager,
        'gold_price_manager': gold_price_manager,
        'claude_manager': claude_manager,
        'rate_limiter': rate_limiter,
        'security': security_manager,
        'cache': cache_manager
    })
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("license", license_command))
    application.add_handler(CommandHandler("createkeys", create_keys_command))
    application.add_handler(CommandHandler("keys", keys_command))
    application.add_handler(CommandHandler("unusedkeys", unused_keys_command))
    application.add_handler(CommandHandler("deleteuser", delete_user_command))
    application.add_handler(CommandHandler("backup", backup_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # معالجات الرسائل
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(Config.MASTER_USER_ID), handle_admin_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    
    # معالج الأزرار
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # معالج الأخطاء
    application.add_error_handler(error_handler)
    
    print(f"{emoji('check')} جاهز للعمل!")
    print(f"{emoji('chart')} تم تحميل {len(license_manager.license_keys)} مفتاح تفعيل")
    print(f"{emoji('users')} تم تحميل {len(db_manager.users)} مستخدم")
    print("="*50)
    print(f"{emoji('globe')} البوت يعمل على Render مع Webhook...")
    
    # إعداد webhook
    asyncio.get_event_loop().run_until_complete(setup_webhook())
    
    # تشغيل webhook على Render
    port = int(os.getenv("PORT", "10000"))
    webhook_url = Config.WEBHOOK_URL or "https://your-app-name.onrender.com"
    
    print(f"{emoji('link')} Webhook URL: {webhook_url}/webhook")
    print(f"{emoji('rocket')} استمع على المنفذ: {port}")
    
    try:
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="webhook",
            webhook_url=f"{webhook_url}/webhook",
            drop_pending_updates=True  # حذف الرسائل المعلقة
        )
    except Exception as e:
        print(f"{emoji('cross')} خطأ في تشغيل Webhook: {e}")
        logger.error(f"Webhook error: {e}")

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    {emoji('fire')} Gold Nightmare Bot {emoji('fire')}                    ║
║                    Render Webhook Version                    ║
║                     Version 6.0 Professional Enhanced        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  {emoji('globe')} تشغيل على Render مع Webhook                             ║
║  {emoji('zap')} لا يحتاج polling - webhook فقط                          ║
║  {emoji('link')} متوافق مع بيئة Render                                   ║
║  {emoji('signal')} استقبال فوري للرسائل                                    ║
║                                                              ║
║  {emoji('rocket')} المميزات:                                               ║
║  • 40 مفتاح تفعيل أولي (50 سؤال/مفتاح)                     ║
║  • نظام إنتهاء المفتاح بعد استنفاد الأسئلة                   ║
║  • أزرار تفاعلية للمفعلين فقط                               ║
║  • لوحة إدارة شاملة ومتطورة                                 ║
║  • تحليل شامل متقدم سري للمحترفين                          ║
║  • تنسيقات جميلة وتحليلات احترافية                          ║
║  • تحليل بـ 8000 توكن للدقة القصوى                         ║
║                                                              ║
║  {emoji('admin')} أوامر الإدارة:                                          ║
║  /stats - إحصائيات سريعة                                   ║
║  /backup - نسخة احتياطية                                   ║
║  /keys - عرض كل المفاتيح                                    ║
║  /unusedkeys - المفاتيح المتاحة                              ║
║  /createkeys [عدد] [حد] - إنشاء مفاتيح                      ║
║  /deleteuser [مفتاح] - حذف مستخدم                          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    main()
