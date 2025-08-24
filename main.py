#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gold Nightmare Bot - Complete Advanced Analysis & Risk Management System
بوت تحليل الذهب الاحترافي مع نظام مفاتيح التفعيل المتقدم
Version: 6.0 Professional Enhanced Edition
Author: Adi - Gold Nightmare School
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
import os
from flask import Flask

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

# ==================== Configuration ====================
class Config:
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
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
    
    # Special Analysis Trigger
    NIGHTMARE_TRIGGER = "كابو"

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
    daily_limit: int = 3
    used_today: int = 0
    last_reset_date: date = field(default_factory=date.today)
    is_active: bool = True
    total_uses: int = 0
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
            
        await self.reset_daily_usage()
    
    async def generate_initial_keys(self, count: int = 40):
        """إنشاء المفاتيح الأولية"""
        print(f"🔑 إنشاء {count} مفتاح تفعيل...")
        
        for i in range(count):
            key = self.generate_unique_key()
            license_key = LicenseKey(
                key=key,
                created_date=datetime.now(),
                daily_limit=3,
                notes=f"مفتاح أولي رقم {i+1}"
            )
            self.license_keys[key] = license_key
        
        print(f"✅ تم إنشاء {count} مفتاح بنجاح!")
        print("\n" + "="*70)
        print("🔑 مفاتيح التفعيل المُنشأة (احفظها في مكان آمن):")
        print("="*70)
        for i, (key, _) in enumerate(self.license_keys.items(), 1):
            print(f"{i:2d}. {key}")
        print("="*70)
        print("💡 كل مفتاح يعطي 3 رسائل يومياً ويتجدد تلقائياً كل 24 ساعة بالضبط")
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
    
    async def create_new_key(self, daily_limit: int = 3, notes: str = "") -> str:
        """إنشاء مفتاح جديد"""
        key = self.generate_unique_key()
        license_key = LicenseKey(
            key=key,
            created_date=datetime.now(),
            daily_limit=daily_limit,
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
                        daily_limit=key_data.get('daily_limit', 3),
                        used_today=key_data.get('used_today', 0),
                        last_reset_date=date.fromisoformat(key_data.get('last_reset_date', str(date.today()))),
                        is_active=key_data.get('is_active', True),
                        total_uses=key_data.get('total_uses', 0),
                        user_id=key_data.get('user_id'),
                        username=key_data.get('username'),
                        notes=key_data.get('notes', '')
                    )
                    self.license_keys[key.key] = key
                
                print(f"✅ تم تحميل {len(self.license_keys)} مفتاح")
                
        except FileNotFoundError:
            print("🔍 ملف المفاتيح غير موجود، سيتم إنشاؤه")
            self.license_keys = {}
        except Exception as e:
            print(f"❌ خطأ في تحميل المفاتيح: {e}")
            self.license_keys = {}
    
    async def save_keys(self):
        """حفظ المفاتيح في الملف"""
        try:
            data = {
                'keys': [
                    {
                        'key': key.key,
                        'created_date': key.created_date.isoformat(),
                        'daily_limit': key.daily_limit,
                        'used_today': key.used_today,
                        'last_reset_date': key.last_reset_date.isoformat(),
                        'is_active': key.is_active,
                        'total_uses': key.total_uses,
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
            print(f"❌ خطأ في حفظ المفاتيح: {e}")
    
    async def reset_daily_usage(self):
        """إعادة تعيين الاستخدام اليومي"""
        now = datetime.now()
        today = now.date()
        reset_count = 0
        
        for key in self.license_keys.values():
            if key.last_reset_date < today:
                last_reset_datetime = datetime.combine(key.last_reset_date, datetime.min.time())
                if (now - last_reset_datetime).total_seconds() >= 86400:
                    key.used_today = 0
                    key.last_reset_date = today
                    reset_count += 1
        
        if reset_count > 0:
            print(f"🔄 تم تجديد {reset_count} مفتاح للاستخدام اليومي")
            await self.save_keys()
    
    async def validate_key(self, key: str, user_id: int) -> Tuple[bool, str]:
        """فحص صحة المفتاح"""
        await self.reset_daily_usage()
        
        if key not in self.license_keys:
            return False, "❌ مفتاح التفعيل غير صالح"
        
        license_key = self.license_keys[key]
        
        if not license_key.is_active:
            return False, "❌ مفتاح التفعيل معطل"
        
        if license_key.user_id and license_key.user_id != user_id:
            return False, "❌ مفتاح التفعيل مستخدم من قبل مستخدم آخر"
        
        if license_key.used_today >= license_key.daily_limit:
            time_until_reset = self._get_time_until_reset()
            return False, f"❌ تم استنفاد الحد اليومي ({license_key.daily_limit} رسائل)\n⏰ سيتم التجديد خلال {time_until_reset}\n\n💡 كل مفتاح له 3 رسائل فقط يومياً"
        
        return True, "✅ مفتاح صالح"
    
    async def use_key(self, key: str, user_id: int, username: str = None, request_type: str = "analysis") -> Tuple[bool, str]:
        """استخدام المفتاح"""
        is_valid, message = await self.validate_key(key, user_id)
        
        if not is_valid:
            return False, message
        
        license_key = self.license_keys[key]
        
        if not license_key.user_id:
            license_key.user_id = user_id
            license_key.username = username
        
        license_key.used_today += 1
        license_key.total_uses += 1
        
        await self.save_keys()
        
        remaining = license_key.daily_limit - license_key.used_today
        
        if remaining == 0:
            return True, f"✅ تم استخدام المفتاح بنجاح\n⚠️ هذه آخر رسالة اليوم!\n⏰ سيتم التجديد خلال {self._get_time_until_reset()}"
        elif remaining == 1:
            return True, f"✅ تم استخدام المفتاح بنجاح\n⚠️ تبقت رسالة واحدة فقط اليوم!"
        else:
            return True, f"✅ تم استخدام المفتاح بنجاح\n📊 الرسائل المتبقية اليوم: {remaining}"
    
    def _get_time_until_reset(self) -> str:
        """حساب الوقت حتى التجديد"""
        now = datetime.now()
        tomorrow = datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
        time_left = tomorrow - now
        
        hours = time_left.seconds // 3600
        minutes = (time_left.seconds % 3600) // 60
        
        return f"{hours} ساعة و {minutes} دقيقة"
    
    async def get_key_info(self, key: str) -> Optional[Dict]:
        """الحصول على معلومات المفتاح"""
        if key not in self.license_keys:
            return None
        
        license_key = self.license_keys[key]
        
        return {
            'key': key,
            'is_active': license_key.is_active,
            'daily_limit': license_key.daily_limit,
            'used_today': license_key.used_today,
            'remaining_today': license_key.daily_limit - license_key.used_today,
            'total_uses': license_key.total_uses,
            'user_id': license_key.user_id,
            'username': license_key.username,
            'created_date': license_key.created_date.strftime('%Y-%m-%d'),
            'last_reset': license_key.last_reset_date.strftime('%Y-%m-%d'),
            'notes': license_key.notes
        }
    
    async def get_all_keys_stats(self) -> Dict:
        """إحصائيات جميع المفاتيح"""
        total_keys = len(self.license_keys)
        active_keys = sum(1 for key in self.license_keys.values() if key.is_active)
        used_keys = sum(1 for key in self.license_keys.values() if key.user_id is not None)
        
        today_usage = sum(key.used_today for key in self.license_keys.values())
        total_usage = sum(key.total_uses for key in self.license_keys.values())
        
        return {
            'total_keys': total_keys,
            'active_keys': active_keys,
            'used_keys': used_keys,
            'unused_keys': total_keys - used_keys,
            'today_usage': today_usage,
            'total_usage': total_usage,
            'avg_usage_per_key': total_usage / total_keys if total_keys > 0 else 0
        }
    
    async def delete_user_by_key(self, key: str) -> Tuple[bool, str]:
        """حذف مستخدم من المفتاح"""
        if key not in self.license_keys:
            return False, "❌ المفتاح غير موجود"
        
        license_key = self.license_keys[key]
        if not license_key.user_id:
            return False, "❌ المفتاح غير مرتبط بمستخدم"
        
        old_user_id = license_key.user_id
        old_username = license_key.username
        
        license_key.user_id = None
        license_key.username = None
        license_key.used_today = 0
        
        await self.save_keys()
        
        return True, f"✅ تم حذف المستخدم {old_username or old_user_id} من المفتاح {key}"

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
        
        # التحقق من التحليل الخاص "كابو"
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
            return f"❌ خطأ في التحليل: {str(e)}"
    
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

🏆 الانتماء المؤسسي: Gold Nightmare Academy - أكاديمية التحليل المتقدم

البيانات الحية المعتمدة:
💰 السعر: ${gold_price.price} USD/oz
📊 التغيير 24h: {gold_price.change_24h:+.2f} ({gold_price.change_percentage:+.2f}%)
📈 المدى: ${gold_price.low_24h} - ${gold_price.high_24h}
⏰ الوقت: {gold_price.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
📡 المصدر: {gold_price.source}
"""
        
        # تخصيص حسب نوع التحليل مع تنسيقات متقدمة
        if analysis_type == AnalysisType.QUICK:
            base_prompt += """

⚡ **التحليل السريع - أقصى 150 كلمة:**

📋 **التنسيق المطلوب:**
```
🎯 **التوصية:** [BUY/SELL/HOLD]
📈 **السعر الحالي:** $[السعر]
🔴 **السبب:** [سبب واحد قوي]

📊 **الأهداف:**
🥇 الهدف الأول: $[السعر]
🔴 وقف الخسارة: $[السعر]

⏰ **الإطار الزمني:** [المدة المتوقعة]
🔥 **مستوى الثقة:** [نسبة مئوية]%
```

✨ **متطلبات:**
- توصية واضحة ومباشرة فقط
- سبب رئيسي واحد مقنع
- هدف واحد ووقف خسارة واحد
- بدون مقدمات أو تفاصيل زائدة
- تنسيق منظم ومختصر"""

        elif analysis_type == AnalysisType.SCALPING:
            base_prompt += """

🎯 **تحليل السكالبينج - التداول السريع (1-15 دقيقة):**

📋 **التنسيق المطلوب:**
```
⚡ **توصية السكالب:** [BUY/SELL]
💰 **السعر الحالي:** $[السعر]

🎯 **نقاط الدخول الدقيقة:**
🔵 دخول أول: $[السعر] 
🔵 دخول ثاني: $[السعر] (إضافة)

📈 **الأهداف السريعة:**
🥇 هدف أول (5-10 نقاط): $[السعر]
🥈 هدف ثاني (10-15 نقطة): $[السعر]

🛑 **إدارة المخاطر:**
🔴 وقف الخسارة: $[السعر] (3-8 نقاط)
⚖️ نسبة المخاطر/العوائد: 1:[نسبة]

⏱️ **التوقيت:**
📅 مدة التداول: 5-15 دقيقة
⚡ نوع التنفيذ: سريع/فوري

🔥 **مؤشرات التأكيد:**
• [مؤشر 1]: [حالة]
• [مؤشر 2]: [حالة]
```

🎯 **التركيز على:**
- نقاط دخول وخروج دقيقة جداً
- أهداف صغيرة (5-15 نقطة)
- وقف خسارة ضيق (3-8 نقاط)
- سرعة التنفيذ والخروج
- مؤشرات قصيرة المدى"""

        elif analysis_type == AnalysisType.SWING:
            base_prompt += """

📈 **تحليل السوينج - التداول متوسط المدى:**

📋 **التنسيق المطلوب:**
```
🎯 **استراتيجية السوينج:** [اتجاه التداول]
💰 **السعر الحالي:** $[السعر]

📊 **تحليل الاتجاه العام:**
🔵 الاتجاه الرئيسي: [صاعد/هابط/عرضي]
📈 قوة الاتجاه: [ضعيف/متوسط/قوي]

🎯 **نقاط الدخول الاستراتيجية:**
🔵 منطقة دخول أولى: $[من] - $[إلى]
🔵 منطقة دخول ثانية: $[من] - $[إلى]

📈 **أهداف متوسطة المدى:**
🥇 هدف أسبوعي: $[السعر]
🥈 هدف شهري: $[السعر] 
🥉 هدف فصلي: $[السعر]

🛡️ **إدارة المخاطر:**
🔴 وقف الخسارة: $[السعر]
📊 حجم الصفقة المقترح: [نسبة]% من المحفظة
⚖️ نسبة المخاطر/العوائد: 1:[نسبة]

⏰ **الإطار الزمني:**
📅 مدة متوقعة: [أيام/أسابيع]
🔄 نقاط إعادة تقييم: [مستويات]
```

🎯 **التركيز على:**
- الاتجاهات متوسطة وطويلة المدى
- نقاط دخول استراتيجية صبورة
- أهداف أسبوعية وشهرية
- إدارة مخاطر للاحتفاظ الطويل"""

        elif analysis_type == AnalysisType.DETAILED:
            base_prompt += """

📊 **التحليل الشامل المتقدم:**

📋 **التنسيق المطلوب:**
```
══════════════════════════════════════
    🎯 **تحليل الذهب الشامل**
══════════════════════════════════════

💰 **الوضع الحالي:**
📊 السعر: $[السعر] | التغيير: [التغيير]
📈 الاتجاه: [الوصف] | القوة: [النسبة]%

🔍 **تحليل الأطر الزمنية:**
┌─────────────────────────────────────┐
│ الإطار  │ الاتجاه │ القوة │ الثقة │
├─────────────────────────────────────┤
│ M5      │ [↑/↓]   │ [%]   │ [%]   │
│ M15     │ [↑/↓]   │ [%]   │ [%]   │
│ H1      │ [↑/↓]   │ [%]   │ [%]   │
│ H4      │ [↑/↓]   │ [%]   │ [%]   │
│ D1      │ [↑/↓]   │ [%]   │ [%]   │
└─────────────────────────────────────┘

🛡️ **مستويات الدعم والمقاومة:**
┌─────────────────────────────────────┐
│ المستوى    │ السعر     │ القوة    │
├─────────────────────────────────────┤
│ مقاومة قوية │ $[سعر]   │ قوي     │
│ مقاومة متوسط│ $[سعر]   │ متوسط   │
│ السعر الحالي│ $[سعر]   │ ---     │
│ دعم متوسط   │ $[سعر]   │ متوسط   │
│ دعم قوي     │ $[سعر]   │ قوي     │
└─────────────────────────────────────┘

🎯 **السيناريوهات المحتملة:**

🟢 **السيناريو الصاعد** (احتمالية [%]%)
• نقطة الدخول: $[سعر]
• الهدف الأول: $[سعر]
• الهدف الثاني: $[سعر]
• وقف الخسارة: $[سعر]

🔴 **السيناريو الهابط** (احتمالية [%]%)
• نقطة الدخول: $[سعر]
• الهدف الأول: $[سعر]
• الهدف الثاني: $[سعر]
• وقف الخسارة: $[سعر]

📊 **مؤشرات فنية:**
• RSI: [قيمة] - [تفسير]
• MACD: [حالة] - [إشارة]
• Moving Averages: [وضع]
• Volume: [مستوى] - [دلالة]

💡 **توصيات إدارة المخاطر:**
• حجم الصفقة: [نسبة]% من المحفظة
• نسبة المخاطر/العوائد: 1:[نسبة]
• نقاط إعادة التقييم: [مستويات]
```"""

        elif analysis_type == AnalysisType.NIGHTMARE:
            base_prompt += f"""

🔥🔥🔥 **التحليل الخاص - كابوس الذهب** 🔥🔥🔥
هذا التحليل المتقدم مخصص للمحترفين فقط ويشمل:

╔════════════════════════════════════════════════════════════════════╗
║                    🎯 **التحليل الشامل المطلوب**                    ║
╚════════════════════════════════════════════════════════════════════╝

📊 **1. تحليل الأطر الزمنية المتعددة:**
• تحليل M5, M15, H1, H4, D1 مع نسب الثقة
• إجماع الأطر الزمنية والتوصية الموحدة
• أفضل إطار زمني للدخول

🎯 **2. مناطق الدخول والخروج:**
• نقاط الدخول الدقيقة بالسنت الواحد
• مستويات الخروج المتدرجة
• نقاط إضافة الصفقات

🛡️ **3. مستويات الدعم والمقاومة:**
• الدعوم والمقاومات الأساسية
• المستويات النفسية المهمة
• قوة كل مستوى (ضعيف/متوسط/قوي)

🔄 **4. نقاط الارتداد المحتملة:**
• مناطق الارتداد عالية الاحتمال
• إشارات التأكيد المطلوبة
• نسب نجاح الارتداد

⚖️ **5. مناطق العرض والطلب:**
• مناطق العرض المؤسسية
• مناطق الطلب القوية
• تحليل السيولة والحجم

⚡ **6. استراتيجيات السكالبينج:**
• فرص السكالبينج (1-15 دقيقة)
• نقاط الدخول السريعة
• أهداف محققة بسرعة

📈 **7. استراتيجيات السوينج:**
• فرص التداول متوسط المدى (أيام-أسابيع)
• نقاط الدخول الاستراتيجية
• أهداف طويلة المدى

🔄 **8. تحليل الانعكاس:**
• نقاط الانعكاس المحتملة
• مؤشرات تأكيد الانعكاس
• قوة الانعكاس المتوقعة

📊 **9. نسب الثقة المبررة:**
• نسبة ثقة لكل تحليل مع المبررات
• درجة المخاطرة لكل استراتيجية
• احتمالية نجاح كل سيناريو

💡 **10. توصيات إدارة المخاطر:**
• حجم الصفقة المناسب
• وقف الخسارة المثالي
• نسبة المخاطر/العوائد

🎯 **متطلبات التنسيق:**
• استخدام جداول منسقة وواضحة
• تقسيم المعلومات إلى أقسام مرتبة
• استخدام رموز تعبيرية مناسبة
• عرض النتائج بطريقة جميلة وسهلة القراءة
• تضمين نصيحة احترافية في كل قسم

🎯 **مع تنسيق جميل وجداول منظمة ونصائح احترافية!**

⚠️ ملاحظة: هذا تحليل تعليمي وليس نصيحة استثمارية شخصية"""

        elif analysis_type == AnalysisType.FORECAST:
            base_prompt += """

🔮 **التوقعات المستقبلية الذكية:**

📋 **التنسيق المطلوب:**
```
══════════════════════════════════════
    🔮 **توقعات الذهب الذكية**
══════════════════════════════════════

📊 **الوضع الحالي:**
💰 السعر: $[السعر] | الاتجاه: [اتجاه]

🎯 **توقعات قصيرة المدى (24-48 ساعة):**
┌─────────────────────────────────────┐
│ السيناريو     │ الاحتمالية │ الهدف   │
├─────────────────────────────────────┤
│ 🟢 صعود قوي   │ [%]%      │ $[سعر] │
│ 🔵 صعود معتدل │ [%]%      │ $[سعر] │
│ 🟡 استقرار    │ [%]%      │ $[سعر] │
│ 🟠 هبوط معتدل │ [%]%      │ $[سعر] │
│ 🔴 هبوط قوي   │ [%]%      │ $[سعر] │
└─────────────────────────────────────┘

📅 **توقعات أسبوعية:**
• المدى المتوقع: $[من] - $[إلى]
• السيناريو الأقوى: [وصف] ([%]%)
• نقاط مراقبة: $[سعر1], $[سعر2]

📈 **العوامل المؤثرة:**
🏦 العوامل الاقتصادية:
  • [عامل 1]: تأثير [إيجابي/سلبي/محايد]
  • [عامل 2]: تأثير [إيجابي/سلبي/محايد]

📊 العوامل الفنية:
  • [عامل فني 1]: [الوصف]
  • [عامل فني 2]: [الوصف]

🌍 العوامل الخارجية:
  • [عامل 1]: [التأثير]
  • [عامل 2]: [التأثير]

⚠️ **المخاطر المحتملة:**
• [مخاطر عالية]: [الوصف]
• [مخاطر متوسطة]: [الوصف]

🎯 **التوصية الذكية:**
[توصية مفصلة مع نسبة الثقة]
```"""

        elif analysis_type == AnalysisType.REVERSAL:
            base_prompt += """

🔄 **تحليل نقاط الانعكاس:**

📋 **التنسيق المطلوب:**
```
══════════════════════════════════════
    🔄 **نقاط الانعكاس المحتملة**
══════════════════════════════════════

💰 **الوضع الحالي:**
📊 السعر: $[السعر] | اتجاه السوق: [الاتجاه]

🎯 **نقاط الانعكاس الرئيسية:**
┌─────────────────────────────────────┐
│ المستوى    │ السعر    │ النوع │ القوة │
├─────────────────────────────────────┤
│ انعكاس علوي│ $[سعر]  │ مقاومة│ [%]  │
│ انعكاس علوي│ $[سعر]  │ مقاومة│ [%]  │
│ السعر الحالي│ $[سعر] │ ---   │ ---  │
│ انعكاس سفلي│ $[سعر]  │ دعم   │ [%]  │
│ انعكاس سفلي│ $[سعر]  │ دعم   │ [%]  │
└─────────────────────────────────────┘

🔍 **إشارات تأكيد الانعكاس:**

🟢 **للانعكاس الصاعد:**
✅ إشارة 1: [الوصف] - قوة [%]%
✅ إشارة 2: [الوصف] - قوة [%]%
✅ إشارة 3: [الوصف] - قوة [%]%

🔴 **للانعكاس الهابط:**
❌ إشارة 1: [الوصف] - قوة [%]%
❌ إشارة 2: [الوصف] - قوة [%]%
❌ إشارة 3: [الوصف] - قوة [%]%

📊 **احتماليات الانعكاس:**
🎯 انعكاس صاعد: [%]% احتمالية
🎯 انعكاس هابط: [%]% احتمالية
🎯 استمرار الاتجاه: [%]% احتمالية

💡 **استراتيجية التداول:**
• انتظار تأكيد الانعكاس عند: $[سعر]
• دخول بعد كسر: $[سعر]
• هدف الانعكاس: $[سعر]
• وقف الخسارة: $[سعر]
```"""

        elif analysis_type == AnalysisType.NEWS:
            base_prompt += """

📰 **تحليل تأثير الأخبار:**

📋 **التنسيق المطلوب:**
```
══════════════════════════════════════
    📰 **تحليل الأخبار وتأثيرها**
══════════════════════════════════════

💰 **الوضع قبل الأخبار:**
📊 السعر: $[السعر] | الاتجاه: [الاتجاه]

📅 **الأخبار والأحداث المؤثرة:**

🏦 **الأخبار الاقتصادية:**
┌─────────────────────────────────────┐
│ الخبر          │ التوقيت │ التأثير   │
├─────────────────────────────────────┤
│ [خبر 1]        │ [وقت]   │ [إيج/سلب] │
│ [خبر 2]        │ [وقت]   │ [إيج/سلب] │
│ [خبر 3]        │ [وقت]   │ [إيج/سلب] │
└─────────────────────────────────────┘

🌍 **الأحداث الجيوسياسية:**
• [حدث 1]: التأثير [مرتفع/متوسط/منخفض]
• [حدث 2]: التأثير [مرتفع/متوسط/منخفض]

📊 **توقعات ردود الفعل:**

🟢 **السيناريو الإيجابي** ([%]% احتمالية)
• سبب الارتفاع: [السبب]
• الهدف المتوقع: $[سعر]
• مدة التأثير: [المدة]

🔴 **السيناريو السلبي** ([%]% احتمالية)
• سبب الانخفاض: [السبب]
• الهدف المتوقع: $[سعر]
• مدة التأثير: [المدة]

⚡ **استراتيجية التداول:**
• انتظار الخبر عند: [الوقت]
• ردة الفعل المتوقعة: [الوصف]
• نقطة الدخول: $[سعر]
• إدارة المخاطر: [الاستراتيجية]

🎯 **توصيات خاصة:**
• [توصية 1]
• [توصية 2]
```"""

        # إضافة المتطلبات العامة
        base_prompt += """

🎯 **متطلبات التنسيق العامة:**
1. استخدام جداول وترتيبات جميلة
2. تقسيم المعلومات إلى أقسام واضحة
3. استخدام رموز تعبيرية مناسبة
4. تنسيق النتائج بطريقة احترافية
5. تقديم نصيحة عملية في كل تحليل
6. نسب ثقة مبررة إحصائياً
7. تحليل احترافي باللغة العربية مع مصطلحات فنية دقيقة

⚠️ ملاحظة: هذا تحليل تعليمي وليس نصيحة استثمارية شخصية"""
        
        return base_prompt

    def _build_user_prompt(self, prompt: str, gold_price: GoldPrice, analysis_type: AnalysisType) -> str:
        """بناء prompt المستخدم"""
        
        context = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 **البيانات الأساسية:**
• السعر الحالي: ${gold_price.price}
• التغيير: {gold_price.change_24h:+.2f} USD ({gold_price.change_percentage:+.2f}%)
• المدى اليومي: ${gold_price.low_24h} - ${gold_price.high_24h}
• التوقيت: {gold_price.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **طلب المستخدم:** {prompt}

📋 **نوع التحليل المطلوب:** {analysis_type.value}

"""
        
        if analysis_type == AnalysisType.NIGHTMARE:
            context += f"""🔥 **التحليل الخاص المطلوب:**

المطلوب تحليل شامل ومفصل يشمل جميع النقاط التالية بتنسيق جميل:

📊 **1. تحليل الأطر الزمنية المتعددة**
📍 **2. مناطق الدخول والخروج الدقيقة**
🛡️ **3. مستويات الدعم والمقاومة**
🔄 **4. نقاط الارتداد المحتملة**
⚖️ **5. مناطق العرض والطلب**
⚡ **6. استراتيجيات السكالبينج**
📈 **7. استراتيجيات السوينج**
🔄 **8. تحليل الانعكاس**
📊 **9. نسب الثقة المبررة**
💡 **10. توصيات إدارة المخاطر**

🎯 **مع تنسيق جميل وجداول منظمة ونصائح احترافية!**"""
        
        elif analysis_type == AnalysisType.QUICK:
            context += "\n⚡ **المطلوب:** إجابة سريعة ومباشرة ومنسقة في 150 كلمة فقط"
        elif analysis_type == AnalysisType.SCALPING:
            context += "\n⚡ **المطلوب:** تحليل سكالبينغ سريع ومنسق في 200 كلمة"
        else:
            context += "\n📊 **المطلوب:** تحليل مفصل ومنسق بجداول جميلة"
            
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
            return False, f"⚠️ تجاوزت الحد المسموح. انتظر {wait_time} ثانية."
        
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
    """إرسال رسائل طويلة"""
    max_length = 4000
    
    if len(text) <= max_length:
        await update.message.reply_text(text, parse_mode=parse_mode)
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
        await update.message.reply_text(
            part + (f"\n\n🔄 الجزء {i+1}/{len(parts)}" if len(parts) > 1 else ""),
            parse_mode=parse_mode
        )
        await asyncio.sleep(0.5)

def create_main_keyboard(user: User) -> InlineKeyboardMarkup:
    """إنشاء لوحة المفاتيح الرئيسية المحسنة"""
    
    is_activated = (user.license_key and user.is_activated) or user.user_id == Config.MASTER_USER_ID
    
    if not is_activated:
        # للمستخدمين غير المفعلين
        keyboard = [
            [
                InlineKeyboardButton("💰 سعر الذهب المباشر", callback_data="price_now")
            ],
            [
                InlineKeyboardButton("🎯 تجربة تحليل مجاني", callback_data="demo_analysis"),
            ],
            [
                InlineKeyboardButton("🔑 كيف أحصل على مفتاح؟", callback_data="how_to_get_license")
            ],
            [
                InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odai_xau")
            ]
        ]
    else:
        # للمستخدمين المفعلين - قائمة متخصصة
        keyboard = [
            # الصف الأول - التحليلات الأساسية
            [
                InlineKeyboardButton("⚡ سريع (30 ثانية)", callback_data="analysis_quick"),
                InlineKeyboardButton("📊 شامل متقدم", callback_data="analysis_detailed")
            ],
            # الصف الثاني - تحليلات متخصصة
            [
                InlineKeyboardButton("🎯 سكالب (1-15د)", callback_data="analysis_scalping"),
                InlineKeyboardButton("📈 سوينج (أيام/أسابيع)", callback_data="analysis_swing")
            ],
            # الصف الثالث - توقعات وانعكاسات
            [
                InlineKeyboardButton("🔮 توقعات ذكية", callback_data="analysis_forecast"),
                InlineKeyboardButton("🔄 نقاط الانعكاس", callback_data="analysis_reversal")
            ],
            # الصف الرابع - أدوات إضافية
            [
                InlineKeyboardButton("💰 سعر مباشر", callback_data="price_now"),
                InlineKeyboardButton("📰 تأثير الأخبار", callback_data="analysis_news")
            ],
            # الصف الخامس - المعلومات الشخصية
            [
                InlineKeyboardButton("🔑 معلومات المفتاح", callback_data="key_info"),
                InlineKeyboardButton("⚙️ إعدادات", callback_data="settings")
            ]
        ]
        
        # إضافة لوحة الإدارة للمشرف فقط
        if user.user_id == Config.MASTER_USER_ID:
            keyboard.append([
                InlineKeyboardButton("👨‍💼 لوحة الإدارة", callback_data="admin_panel")
            ])
        
        # إضافة زر التحليل الخاص في الأسفل
        keyboard.append([
            InlineKeyboardButton(f"🔥 التحليل الخاص الشامل 🔥", callback_data="nightmare_analysis")
        ])
    
    return InlineKeyboardMarkup(keyboard)

def create_admin_keyboard() -> InlineKeyboardMarkup:
    """لوحة الإدارة"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 إحصائيات عامة", callback_data="admin_stats"),
            InlineKeyboardButton("🔑 إدارة المفاتيح", callback_data="admin_keys")
        ],
        [
            InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users"),
            InlineKeyboardButton("📈 تقارير التحليل", callback_data="admin_analyses")
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        ]
    ])

def create_keys_management_keyboard() -> InlineKeyboardMarkup:
    """لوحة إدارة المفاتيح"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 عرض كل المفاتيح", callback_data="keys_show_all"),
            InlineKeyboardButton("⭕ المفاتيح المتاحة", callback_data="keys_show_unused")
        ],
        [
            InlineKeyboardButton("➕ إنشاء مفاتيح جديدة", callback_data="keys_create_prompt"),
            InlineKeyboardButton("📊 إحصائيات المفاتيح", callback_data="keys_stats")
        ],
        [
            InlineKeyboardButton("🗑️ حذف مستخدم", callback_data="keys_delete_user"),
            InlineKeyboardButton("🔙 رجوع للإدارة", callback_data="admin_panel")
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
                await update.message.reply_text("❌ حسابك محظور. تواصل مع الدعم.")
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
                    "🔑 يتطلب تفعيل الحساب\n\n"
                    "للاستخدام، يجب تفعيل حسابك أولاً.\n"
                    "استخدم: /license مفتاح_التفعيل\n\n"
                    "💬 للتواصل: @Odai_xau"
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
            await update.message.reply_text("❌ هذا الأمر للمسؤول فقط.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==================== Command Handlers ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية المحسن مع واجهة أفضل"""
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
        price_display = f"💰 السعر الحالي: **${gold_price.price}**\n📊 التغيير: **{gold_price.change_24h:+.2f} ({gold_price.change_percentage:+.2f}%)**"
    except:
        price_display = "💰 السعر: يتم التحديث..."

    is_activated = (user.license_key and user.is_activated) or user_id == Config.MASTER_USER_ID
    
    if is_activated:
        # للمستخدمين المفعلين - ترحيب خاص
        key_info = await context.bot_data['license_manager'].get_key_info(user.license_key) if user.license_key else None
        remaining_msgs = key_info['remaining_today'] if key_info else "∞"
        
        welcome_message = f"""
╔══════════════════════════════════════╗
║     🔥 **مرحباً في عالم النخبة** 🔥     ║
╚══════════════════════════════════════╝

👋 أهلاً وسهلاً **{update.effective_user.first_name}**!

{price_display}

┌─────────────────────────────────────┐
│  ✅ **حسابك مُفعَّل ومجهز للعمل**   │
│  🎯 الرسائل المتبقية اليوم: **{remaining_msgs}**  │
│  🔄 يتجدد العداد كل 24 ساعة بالضبط    │
└─────────────────────────────────────┘

🎭 **للحصول على التحليل الخاص الشامل:**
اكتب: **"{Config.NIGHTMARE_TRIGGER}"** في أي رسالة

🎯 **اختر نوع التحليل المطلوب:**"""

        await update.message.reply_text(
            welcome_message,
            reply_markup=create_main_keyboard(user),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    else:
        # للمستخدمين غير المفعلين
        welcome_message = f"""
╔══════════════════════════════════════╗
║   💎 **Gold Nightmare Academy** 💎   ║
║     أقوى منصة تحليل الذهب بالعالم     ║
╚══════════════════════════════════════╝

👋 مرحباً **{update.effective_user.first_name}**!

{price_display}

┌─────────── 🏆 **لماذا نحن الأفضل؟** ───────────┐
│                                               │
│ 🧠 **ذكاء اصطناعي متطور** - Claude 4 Sonnet   │
│ 📊 **تحليل متعدد الأطر الزمنية** بدقة 95%+     │
│ 🎯 **نقاط دخول وخروج** بالسنت الواحد          │
│ 🛡️ **إدارة مخاطر احترافية** مؤسسية           │
│ 📈 **توقعات مستقبلية** مع نسب ثقة دقيقة        │
│ 🔥 **التحليل الخاص الشامل**: "{Config.NIGHTMARE_TRIGGER}"    │
│                                               │
└───────────────────────────────────────────────┘

🎁 **عرض محدود - مفاتيح متاحة الآن!**

🔑 كل مفتاح يعطيك:
   ⚡ 3 تحليلات احترافية يومياً
   🔄 تجديد تلقائي كل 24 ساعة
   🎯 وصول للتحليل الخاص الشامل
   📱 دعم فني مباشر

💡 **للحصول على مفتاح التفعيل:**
تواصل مع المطور المختص"""

        keyboard = [
            [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odai_xau")],
            [InlineKeyboardButton("📈 قناة التوصيات", url="https://t.me/odai_xauusdt")],
            [InlineKeyboardButton("💰 سعر الذهب الآن", callback_data="price_now")],
            [InlineKeyboardButton("❓ كيف أحصل على مفتاح؟", callback_data="how_to_get_license")]
        ]
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

async def license_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر تفعيل المفتاح"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "🔑 تفعيل مفتاح الترخيص\n\n"
            "الاستخدام: /license مفتاح_التفعيل\n\n"
            "مثال: /license GOLD-ABC1-DEF2-GHI3"
        )
        return
    
    license_key = context.args[0].upper().strip()
    license_manager = context.bot_data['license_manager']
    
    is_valid, message = await license_manager.validate_key(license_key, user_id)
    
    if not is_valid:
        await update.message.reply_text(f"❌ فشل التفعيل\n\n{message}")
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
    
    success_message = f"""✅ تم التفعيل بنجاح!

🔑 المفتاح: {license_key}
📊 الحد اليومي: {key_info['daily_limit']} رسائل
📈 المتبقي اليوم: {key_info['remaining_today']} رسائل
⏰ يتجدد العداد كل 24 ساعة تلقائياً بالضبط

🔥 **كابوس الذهب** "{Config.NIGHTMARE_TRIGGER}"

🎉 يمكنك الآن استخدام البوت!"""
    
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
    daily_limit = 3
    
    if context.args:
        try:
            count = int(context.args[0])
            if len(context.args) > 1:
                daily_limit = int(context.args[1])
        except ValueError:
            await update.message.reply_text("❌ استخدم: /createkeys [عدد] [حد_يومي]\nمثال: /createkeys 10 3")
            return
    
    if count > 50:
        await update.message.reply_text("❌ لا يمكن إنشاء أكثر من 50 مفتاح")
        return
    
    license_manager = context.bot_data['license_manager']
    
    status_msg = await update.message.reply_text(f"⏳ جاري إنشاء {count} مفتاح...")
    
    created_keys = []
    for i in range(count):
        key = await license_manager.create_new_key(
            daily_limit=daily_limit,
            notes=f"مفتاح مُنشأ بواسطة المشرف - {datetime.now().strftime('%Y-%m-%d')}"
        )
        created_keys.append(key)
    
    keys_text = "\n".join([f"{i+1}. {key}" for i, key in enumerate(created_keys)])
    
    result_message = f"""✅ تم إنشاء {count} مفتاح بنجاح!

📊 الحد اليومي: {daily_limit} رسائل لكل مفتاح
⏰ يتجدد كل 24 ساعة بالضبط

🔑 المفاتيح:
{keys_text}

💡 تعليمات للمستخدمين:
• كل مفتاح يعطي {daily_limit} رسائل فقط يومياً
• استخدام: /license GOLD-XXXX-XXXX-XXXX
• للتحليل الخاص: "{Config.NIGHTMARE_TRIGGER}\""""
    
    await status_msg.edit_text(result_message)

@admin_only
async def keys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع المفاتيح للمشرف"""
    license_manager = context.bot_data['license_manager']
    
    if not license_manager.license_keys:
        await update.message.reply_text("❌ لا توجد مفاتيح")
        return
    
    # إعداد الرسالة
    message = "🔑 جميع مفاتيح التفعيل:\n\n"
    
    # إحصائيات عامة
    stats = await license_manager.get_all_keys_stats()
    message += f"📊 الإحصائيات:\n"
    message += f"• إجمالي المفاتيح: {stats['total_keys']}\n"
    message += f"• المفاتيح المستخدمة: {stats['used_keys']}\n"
    message += f"• المفاتيح الفارغة: {stats['unused_keys']}\n"
    message += f"• الاستخدام اليوم: {stats['today_usage']}\n"
    message += f"• الاستخدام الإجمالي: {stats['total_usage']}\n\n"
    
    # عرض أول 10 مفاتيح مع تفاصيل كاملة
    count = 0
    for key, license_key in license_manager.license_keys.items():
        if count >= 10:  # عرض أول 10 فقط
            break
        count += 1
        
        status = "🟢 نشط" if license_key.is_active else "🔴 معطل"
        user_info = f"👤 {license_key.username or 'لا يوجد'} (ID: {license_key.user_id})" if license_key.user_id else "⭕ غير مستخدم"
        usage = f"{license_key.used_today}/{license_key.daily_limit}"
        
        message += f"{count:2d}. {key}\n"
        message += f"   {status} | {user_info}\n"
        message += f"   📊 الاستخدام: {usage} | إجمالي: {license_key.total_uses}\n"
        message += f"   📅 إنشاء: {license_key.created_date.strftime('%Y-%m-%d')}\n\n"
    
    if len(license_manager.license_keys) > 10:
        message += f"... و {len(license_manager.license_keys) - 10} مفاتيح أخرى\n\n"
    
    message += "💡 استخدم /unusedkeys للمفاتيح المتاحة فقط"
    
    await send_long_message(update, message)

@admin_only
async def unused_keys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المفاتيح غير المستخدمة فقط"""
    license_manager = context.bot_data['license_manager']
    
    unused_keys = [key for key, license_key in license_manager.license_keys.items() 
                   if not license_key.user_id and license_key.is_active]
    
    if not unused_keys:
        await update.message.reply_text("❌ لا توجد مفاتيح متاحة")
        return
    
    message = f"⭕ المفاتيح المتاحة ({len(unused_keys)} مفتاح):\n\n"
    
    for i, key in enumerate(unused_keys, 1):
        license_key = license_manager.license_keys[key]
        message += f"{i:2d}. {key}\n"
        message += f"    📊 الحد اليومي: {license_key.daily_limit} رسائل\n"
        message += f"    📅 تاريخ الإنشاء: {license_key.created_date.strftime('%Y-%m-%d')}\n\n"
    
    message += f"""💡 تعليمات إعطاء المفاتيح:
انسخ مفتاح وأرسله للمستخدم مع التعليمات:

```
🔑 مفتاح التفعيل الخاص بك:
GOLD-XXXX-XXXX-XXXX

📝 كيفية الاستخدام:
/license GOLD-XXXX-XXXX-XXXX

⚠️ ملاحظات مهمة:
• لديك 3 رسائل فقط يومياً
• يتجدد العداد كل 24 ساعة بالضبط
• للتحليل الخاص اكتب: {Config.NIGHTMARE_TRIGGER}
```"""
    
    await send_long_message(update, message)

@admin_only
async def delete_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف مستخدم من مفتاح"""
    if not context.args:
        await update.message.reply_text(
            "🗑️ حذف مستخدم من مفتاح\n\n"
            "الاستخدام: /deleteuser مفتاح_التفعيل\n\n"
            "مثال: /deleteuser GOLD-ABC1-DEF2-GHI3"
        )
        return
    
    license_key = context.args[0].upper().strip()
    license_manager = context.bot_data['license_manager']
    
    success, message = await license_manager.delete_user_by_key(license_key)
    
    await update.message.reply_text(message)

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
    
    # التحليل الخاص "كابو"
    is_nightmare = Config.NIGHTMARE_TRIGGER in update.message.text
    
    if is_nightmare:
        processing_msg = await update.message.reply_text(
            "🔥🔥🔥 كابوس الذهب 🔥🔥🔥\n\n"
            "⚡ تحضير التحليل المتقدم الشامل...\n"
            "📊 جمع البيانات من جميع الأطر الزمنية...\n"
            "🎯 حساب نقاط الدخول والخروج الدقيقة..."
        )
    else:
        processing_msg = await update.message.reply_text("🧠 جاري التحليل الاحترافي...")
    
    try:
        price = await context.bot_data['gold_price_manager'].get_gold_price()
        if not price:
            await processing_msg.edit_text("❌ لا يمكن الحصول على السعر حالياً.")
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
        await processing_msg.edit_text("❌ حدث خطأ أثناء التحليل.")

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
    
    # فحص إذا كان التحليل الخاص في التعليق
    caption = update.message.caption or ""
    is_nightmare = Config.NIGHTMARE_TRIGGER in caption
    
    if is_nightmare:
        processing_msg = await update.message.reply_text(
            "🔥🔥🔥 تحليل شارت - كابوس الذهب 🔥🔥🔥\n\n"
            "📸 معالجة الصورة بالذكاء الاصطناعي المتقدم...\n"
            "🔍 تحليل النماذج الفنية والمستويات..."
        )
    else:
        processing_msg = await update.message.reply_text("📸 جاري تحليل الشارت بالذكاء الاصطناعي...")
    
    try:
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        image_data = await photo_file.download_as_bytearray()
        
        image_base64 = ImageProcessor.process_image(image_data)
        if not image_base64:
            await processing_msg.edit_text("❌ لا يمكن معالجة الصورة.")
            return
        
        price = await context.bot_data['gold_price_manager'].get_gold_price()
        if not price:
            await processing_msg.edit_text("❌ لا يمكن الحصول على السعر حالياً.")
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
        await processing_msg.edit_text("❌ حدث خطأ أثناء تحليل الصورة.")

# ==================== Enhanced Handler Functions ====================

async def handle_demo_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج التحليل التجريبي للمستخدمين غير المفعلين"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # التحقق من عدد مرات استخدام التجربة (3 مرات كحد أقصى)
    demo_usage = context.user_data.get('demo_usage', 0)
    
    if demo_usage >= 3:
        await query.edit_message_text(
            "🚫 **انتهت المحاولات التجريبية**\n\n"
            "لقد استخدمت الحد الأقصى من التحليلات التجريبية (3 مرات).\n\n"
            "🔥 **للاستمتاع بتحليلات لا محدودة:**\n"
            "احصل على مفتاح تفعيل من المطور\n\n"
            "💎 **مع المفتاح ستحصل على:**\n"
            "• 3 تحليلات احترافية يومياً\n"
            "• تجديد تلقائي كل 24 ساعة\n"
            f"• التحليل الخاص الشامل: '{Config.NIGHTMARE_TRIGGER}'\n"
            "• دعم فني مباشر\n\n"
            "👨‍💼 **تواصل مع المطور:** @Odai_xau",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odai_xau")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ])
        )
        return
    
    # رسالة التحضير
    remaining_demos = 3 - demo_usage
    await query.edit_message_text(
        f"🎯 **تحليل تجريبي مجاني**\n\n"
        f"⚡ جاري تحضير تحليل احترافي للذهب...\n"
        f"📊 المحاولات المتبقية: **{remaining_demos - 1}** من 3\n\n"
        f"⏳ يرجى الانتظار..."
    )
    
    try:
        # الحصول على السعر
        price = await context.bot_data['gold_price_manager'].get_gold_price()
        if not price:
            await query.edit_message_text("❌ لا يمكن الحصول على السعر حالياً.")
            return
        
        # إنشاء تحليل تجريبي مبسط
        demo_prompt = """قدم تحليل سريع احترافي للذهب الآن مع:
        - توصية واضحة (Buy/Sell/Hold)
        - سبب قوي واحد
        - هدف واحد ووقف خسارة
        - نسبة ثقة
        - تنسيق جميل ومنظم
        
        اجعله مثيراً ومحترفاً ليشجع المستخدم على الحصول على المفتاح للتحليلات المتقدمة"""
        
        result = await context.bot_data['claude_manager'].analyze_gold(
            prompt=demo_prompt,
            gold_price=price,
            analysis_type=AnalysisType.QUICK
        )
        
        # إضافة رسالة تسويقية للتحليل التجريبي
        demo_result = f"""🎯 **تحليل تجريبي مجاني - Gold Nightmare**

{result}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 **هذا مجرد طعم من قوة التحليلات الكاملة!**

💎 **مع مفتاح التفعيل ستحصل على:**
⚡ تحليلات متعددة الأنواع (سكالب، سوينج، توقعات)
📊 تحليل شامل لجميع الأطر الزمنية
🎯 نقاط دخول وخروج بالسنت الواحد
🛡️ إدارة مخاطر احترافية
🔮 توقعات ذكية مع احتماليات
📰 تحليل تأثير الأخبار
🔄 اكتشاف نقاط الانعكاس
🔥 التحليل الخاص الشامل: "{Config.NIGHTMARE_TRIGGER}"

📊 **المتبقي من المحاولات التجريبية:** {remaining_demos - 1} من 3

🚀 **انضم لمجتمع النخبة الآن!**"""

        await query.edit_message_text(
            demo_result,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 احصل على مفتاح", callback_data="how_to_get_license")],
                [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odai_xau")],
                [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_main")]
            ])
        )
        
        # تحديث عداد الاستخدام التجريبي
        context.user_data['demo_usage'] = demo_usage + 1
        
    except Exception as e:
        logger.error(f"Error in demo analysis: {e}")
        await query.edit_message_text(
            "❌ حدث خطأ في التحليل التجريبي.\n\n"
            "🔄 يمكنك المحاولة مرة أخرى أو التواصل مع الدعم.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 محاولة أخرى", callback_data="demo_analysis")],
                [InlineKeyboardButton("📞 الدعم", url="https://t.me/Odai_xau")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ])
        )

async def handle_nightmare_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج التحليل الخاص الشامل"""
    query = update.callback_query
    user = context.user_data.get('user')
    
    if not user or not user.is_activated:
        await query.answer("🔒 يتطلب مفتاح تفعيل", show_alert=True)
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
        "🔥🔥🔥 **كابوس الذهب - التحليل الخاص** 🔥🔥🔥\n\n"
        "⚡ تحضير التحليل الشامل المتقدم...\n"
        "🔬 تحليل جميع الأطر الزمنية...\n"
        "📊 حساب مستويات الدعم والمقاومة...\n"
        "🎯 تحديد نقاط الدخول الدقيقة...\n"
        "🛡️ إعداد استراتيجيات إدارة المخاطر...\n"
        "🔮 حساب التوقعات والاحتماليات...\n\n"
        "⏳ هذا التحليل يستغرق وقتاً أطول لضمان الدقة..."
    )
    
    try:
        price = await context.bot_data['gold_price_manager'].get_gold_price()
        if not price:
            await query.edit_message_text("❌ لا يمكن الحصول على السعر حالياً.")
            return
        
        # التحليل الخاص الشامل
        nightmare_prompt = f"""أريد التحليل الخاص الشامل للذهب "كابوس الذهب" - التحليل الأكثر تقدماً وتفصيلاً مع:

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

        "{Config.NIGHTMARE_TRIGGER}"
        
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
🔥 **تم بواسطة Gold Nightmare Academy** 🔥
💎 **التحليل الخاص الشامل - للمحترفين فقط**
⚡ **تحليل متقدم بالذكاء الاصطناعي Claude 4**
🎯 **دقة التحليل: 95%+ - مضمون الجودة**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **تنبيه هام:** هذا تحليل تعليمي متقدم وليس نصيحة استثمارية
💡 **استخدم إدارة المخاطر دائماً ولا تستثمر أكثر مما تستطيع خسارته**"""

        await query.edit_message_text(nightmare_result)
        
    except Exception as e:
        logger.error(f"Error in nightmare analysis: {e}")
        await query.edit_message_text("❌ حدث خطأ في التحليل الخاص.")

async def handle_enhanced_price_display(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج عرض السعر المحسن"""
    query = update.callback_query
    
    try:
        price = await context.bot_data['gold_price_manager'].get_gold_price()
        if not price:
            await query.edit_message_text("❌ لا يمكن الحصول على السعر حالياً.")
            return
        
        # تحديد اتجاه السعر
        if price.change_24h > 0:
            trend_emoji = "📈"
            trend_color = "🟢"
            trend_text = "صاعد"
        elif price.change_24h < 0:
            trend_emoji = "📉"
            trend_color = "🔴"
            trend_text = "هابط"
        else:
            trend_emoji = "➡️"
            trend_color = "🟡"
            trend_text = "مستقر"
        
        # إنشاء رسالة السعر المتقدمة
        price_message = f"""╔══════════════════════════════════════╗
║       💰 **سعر الذهب المباشر** 💰       ║
╚══════════════════════════════════════╝

💎 **السعر الحالي:** ${price.price:.2f}
{trend_color} **الاتجاه:** {trend_text} {trend_emoji}
📊 **التغيير 24س:** {price.change_24h:+.2f} ({price.change_percentage:+.2f}%)

🔝 **أعلى سعر:** ${price.high_24h:.2f}
🔻 **أدنى سعر:** ${price.low_24h:.2f}
⏰ **التحديث:** {price.timestamp.strftime('%H:%M:%S')}

🔥 **اكتب "{Config.NIGHTMARE_TRIGGER}" للحصول على التحليل الخاص الشامل!**"""
        
        # أزرار تفاعلية للسعر
        price_keyboard = [
            [
                InlineKeyboardButton("🔄 تحديث السعر", callback_data="price_now"),
                InlineKeyboardButton("⚡ تحليل سريع", callback_data="analysis_quick")
            ],
            [
                InlineKeyboardButton("📊 تحليل شامل", callback_data="analysis_detailed")
            ],
            [
                InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_main")
            ]
        ]
        
        await query.edit_message_text(
            price_message,
            reply_markup=InlineKeyboardMarkup(price_keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in price display: {e}")
        await query.edit_message_text("❌ خطأ في جلب بيانات السعر")

async def handle_enhanced_key_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج معلومات المفتاح المحسن"""
    query = update.callback_query
    user = context.user_data.get('user')
    
    if not user or not user.license_key:
        await query.edit_message_text(
            "❌ لا يوجد مفتاح مفعل\n\n"
            "للحصول على مفتاح تفعيل تواصل مع المطور",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odai_xau")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ])
        )
        return
    
    try:
        key_info = await context.bot_data['license_manager'].get_key_info(user.license_key)
        if not key_info:
            await query.edit_message_text("❌ لا يمكن جلب معلومات المفتاح")
            return
        
        key_info_message = f"""╔══════════════════════════════════════╗
║        🔑 **معلومات مفتاح التفعيل** 🔑        ║
╚══════════════════════════════════════╝

🆔 **المعرف:** {key_info['username'] or 'غير محدد'}
🏷️ **المفتاح:** `{key_info['key'][:8]}***`
📅 **تاريخ التفعيل:** {key_info['created_date']}

📈 **الاستخدام:** {key_info['used_today']}/{key_info['daily_limit']} رسائل
📉 **المتبقي:** {key_info['remaining_today']} رسائل
🔢 **إجمالي الاستخدام:** {key_info['total_uses']} رسالة

🔥 **التحليل الخاص:** "{Config.NIGHTMARE_TRIGGER}"

💎 **Gold Nightmare Academy - عضوية نشطة**
🚀 **أنت جزء من مجتمع النخبة في تحليل الذهب!**"""
        
        await query.edit_message_text(
            key_info_message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث المعلومات", callback_data="key_info")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in enhanced key info: {e}")
        await query.edit_message_text("❌ خطأ في جلب معلومات المفتاح")

# ==================== Callback Query Handler ====================
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأزرار"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # فحص الحظر
    if context.bot_data['security'].is_blocked(user_id):
        await query.edit_message_text("❌ حسابك محظور.")
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
        
        not_activated_message = f"""🔑 يتطلب مفتاح تفعيل

لاستخدام هذه الميزة، يجب إدخال مفتاح تفعيل صالح.
استخدم: /license مفتاح_التفعيل

💡 للحصول على مفتاح تواصل مع:
👨‍💼 Odai - @Odai_xau

🔥 مع كل مفتاح ستحصل على التحليل الخاص:
"{Config.NIGHTMARE_TRIGGER}" """
        
        await query.edit_message_text(
            not_activated_message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 كيف أحصل على مفتاح؟", callback_data="how_to_get_license")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
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
            help_text = f"""🔑 كيفية الحصول على مفتاح التفعيل

💎 Gold Nightmare Bot يقدم تحليلات الذهب الأكثر دقة في العالم!

📞 للحصول على مفتاح تفعيل:

👨‍💼 تواصل مع Odai:
- Telegram: @Odai_xau
- Channel: @odai_xauusdt  
- Group: @odai_xau_usd

🎁 ماذا تحصل عليه:
- ⚡ 3 تحليلات احترافية يومياً
- 🧠 تحليل بالذكاء الاصطناعي المتقدم
- 📊 تحليل متعدد الأطر الزمنية
- 🔍 اكتشاف النماذج الفنية
- 🎯 نقاط دخول وخروج دقيقة
- 🛡️ إدارة مخاطر احترافية
- 🔥 التحليل الخاص: "{Config.NIGHTMARE_TRIGGER}"

💰 سعر خاص ومحدود!
🔄 تجديد تلقائي كل 24 ساعة بالضبط

🌟 انضم لمجتمع النخبة الآن!"""

            keyboard = [
                [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odai_xau")],
                [InlineKeyboardButton("📈 قناة التوصيات", url="https://t.me/odai_xauusdt")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ]
            
            await query.edit_message_text(
                help_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data == "key_info":
            await handle_enhanced_key_info(update, context)
                        
        elif data == "back_main":
            main_message = f"""🏆 Gold Nightmare Bot

🔥 للتحليل الخاص: "{Config.NIGHTMARE_TRIGGER}"

اختر الخدمة المطلوبة:"""
            
            await query.edit_message_text(
                main_message,
                reply_markup=create_main_keyboard(user)
            )
        
        elif data.startswith("analysis_"):
            analysis_type_map = {
                "analysis_quick": (AnalysisType.QUICK, "⚡ تحليل سريع"),
                "analysis_scalping": (AnalysisType.SCALPING, "🎯 سكالبينج"),
                "analysis_detailed": (AnalysisType.DETAILED, "📊 تحليل مفصل"),
                "analysis_swing": (AnalysisType.SWING, "📈 سوينج"),
                "analysis_forecast": (AnalysisType.FORECAST, "🔮 توقعات"),
                "analysis_reversal": (AnalysisType.REVERSAL, "🔄 مناطق انعكاس"),
                "analysis_news": (AnalysisType.NEWS, "📰 تحليل الأخبار")
            }
            
            if data in analysis_type_map:
                analysis_type, type_name = analysis_type_map[data]
                
                processing_msg = await query.edit_message_text(
                    f"🧠 جاري إعداد {type_name}...\n\n⏳ يرجى الانتظار..."
                )
                
                price = await context.bot_data['gold_price_manager'].get_gold_price()
                if not price:
                    await processing_msg.edit_text("❌ لا يمكن الحصول على السعر حالياً.")
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
                keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_main")]]
                await query.edit_message_reply_markup(
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        
        elif data == "admin_panel" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(
                "👨‍💼 **لوحة الإدارة**\n\nاختر العملية المطلوبة:",
                reply_markup=create_admin_keyboard()
            )
        
        elif data == "admin_stats" and user_id == Config.MASTER_USER_ID:
            try:
                db_stats = await context.bot_data['db'].get_stats()
                license_stats = await context.bot_data['license_manager'].get_all_keys_stats()
                
                stats_text = f"""📊 **إحصائيات النظام الشاملة**

🔑 **إحصائيات المفاتيح:**
• إجمالي المفاتيح: {license_stats['total_keys']}
• المفاتيح النشطة: {license_stats['active_keys']}
• المفاتيح المستخدمة: {license_stats['used_keys']}
• المفاتيح المتاحة: {license_stats['unused_keys']}
• الاستخدام اليوم: {license_stats['today_usage']} رسالة
• الاستخدام الإجمالي: {license_stats['total_usage']} رسالة

👥 **إحصائيات المستخدمين:**
• إجمالي المستخدمين: {db_stats['total_users']}
• المستخدمين النشطين: {db_stats['active_users']}
• معدل التفعيل: {db_stats['activation_rate']}

📈 **إحصائيات التحليل:**
• إجمالي التحليلات: {db_stats['total_analyses']}
• التحليلات خلال 24 ساعة: {db_stats['analyses_24h']}

🔥 **الكلمة السحرية:** "{Config.NIGHTMARE_TRIGGER}"

⏰ **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

                keyboard = [[InlineKeyboardButton("🔙 رجوع للإدارة", callback_data="admin_panel")]]
                await query.edit_message_text(
                    stats_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                logger.error(f"Error in admin_stats: {e}")
                await query.edit_message_text(
                    f"❌ خطأ في تحميل الإحصائيات: {str(e)}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]])
                )
        
        elif data == "admin_keys" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(
                "🔑 **إدارة مفاتيح التفعيل**\n\nاختر العملية المطلوبة:",
                reply_markup=create_keys_management_keyboard()
            )
        
        elif data == "admin_users" and user_id == Config.MASTER_USER_ID:
            db_manager = context.bot_data['db']
            license_manager = context.bot_data['license_manager']
            
            # المستخدمين النشطين
            active_users = [u for u in db_manager.users.values() if u.is_activated]
            recent_users = sorted(active_users, key=lambda x: x.last_activity, reverse=True)[:5]
            
            message = f"""👥 **إدارة المستخدمين**

📊 **إحصائيات عامة:**
• إجمالي المستخدمين: {len(db_manager.users)}
• المستخدمين النشطين: {len(active_users)}

👤 **أحدث المستخدمين النشطين:**"""

            for i, user in enumerate(recent_users, 1):
                # البحث عن معلومات المفتاح
                user_key_info = None
                for key, license_key in license_manager.license_keys.items():
                    if license_key.user_id == user.user_id:
                        user_key_info = license_key
                        break
                
                remaining = user_key_info.daily_limit - user_key_info.used_today if user_key_info else 0
                
                message += f"\n{i}. **{user.first_name}** (@{user.username or 'N/A'})"
                message += f"\n   ID: {user.user_id} | طلبات: {user.total_requests}"
                message += f"\n   متبقي اليوم: {remaining} رسائل"
                message += f"\n   آخر نشاط: {user.last_activity.strftime('%Y-%m-%d %H:%M')}"
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع للإدارة", callback_data="admin_panel")]]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "keys_show_all" and user_id == Config.MASTER_USER_ID:
            license_manager = context.bot_data['license_manager']
            
            if not license_manager.license_keys:
                message = "❌ لا توجد مفاتيح"
            else:
                message = f"🔑 **جميع المفاتيح ({len(license_manager.license_keys)} مفتاح):**\n\n"
                
                count = 0
                for key, license_key in license_manager.license_keys.items():
                    if count >= 15:  # عرض أول 15 فقط
                        break
                    count += 1
                    
                    status = "🟢" if license_key.is_active else "🔴"
                    user_status = f"{license_key.username or 'N/A'}" if license_key.user_id else "متاح"
                    usage = f"{license_key.used_today}/{license_key.daily_limit}"
                    
                    message += f"{count}. `{key[:12]}***`\n"
                    message += f"   {status} {user_status} | {usage}\n\n"
                
                if len(license_manager.license_keys) > 15:
                    message += f"... و {len(license_manager.license_keys) - 15} مفاتيح أخرى\n\n"
                
                message += "💡 استخدم `/keys` للقائمة الكاملة"
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع لإدارة المفاتيح", callback_data="admin_keys")]]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "keys_show_unused" and user_id == Config.MASTER_USER_ID:
            license_manager = context.bot_data['license_manager']
            
            unused_keys = [key for key, license_key in license_manager.license_keys.items() 
                          if not license_key.user_id and license_key.is_active]
            
            if not unused_keys:
                message = "❌ لا توجد مفاتيح متاحة"
            else:
                message = f"⭕ **المفاتيح المتاحة ({len(unused_keys)} مفتاح):**\n\n"
                
                for i, key in enumerate(unused_keys[:10], 1):  # أول 10 فقط
                    message += f"{i}. `{key}`\n"
                
                if len(unused_keys) > 10:
                    message += f"\n... و {len(unused_keys) - 10} مفاتيح أخرى\n"
                
                message += "\n💡 استخدم `/unusedkeys` للقائمة الكاملة"
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع لإدارة المفاتيح", callback_data="admin_keys")]]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "keys_create_prompt" and user_id == Config.MASTER_USER_ID:
            message = """➕ **إنشاء مفاتيح جديدة**

استخدم الأوامر التالية:

🔹 `/createkeys 5` - إنشاء 5 مفاتيح (3 رسائل/يوم)
🔹 `/createkeys 10 5` - إنشاء 10 مفاتيح (5 رسائل/يوم)
🔹 `/createkeys 1 10` - إنشاء مفتاح واحد (10 رسائل/يوم)

⚠️ **ملاحظات:**
• الحد الأقصى: 50 مفتاح في المرة الواحدة
• الافتراضي: 3 رسائل يومياً لكل مفتاح
• يتم التجديد تلقائياً كل 24 ساعة بالضبط"""

            keyboard = [[InlineKeyboardButton("🔙 رجوع لإدارة المفاتيح", callback_data="admin_keys")]]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "keys_stats" and user_id == Config.MASTER_USER_ID:
            license_manager = context.bot_data['license_manager']
            
            stats = await license_manager.get_all_keys_stats()
            
            # أكثر المفاتيح استخداماً
            top_keys = sorted(license_manager.license_keys.items(), 
                             key=lambda x: x[1].total_uses, reverse=True)[:5]
            
            message = f"""📊 **إحصائيات مفصلة للمفاتيح**

🔢 **الأرقام العامة:**
• إجمالي المفاتيح: {stats['total_keys']}
• المفاتيح النشطة: {stats['active_keys']}
• المفاتيح المستخدمة: {stats['used_keys']}
• المفاتيح المتاحة: {stats['unused_keys']}

📈 **الاستخدام:**
• استخدام اليوم: {stats['today_usage']} رسالة
• الاستخدام الإجمالي: {stats['total_usage']} رسالة
• متوسط الاستخدام: {stats['avg_usage_per_key']:.1f} رسالة/مفتاح

🏆 **أكثر المفاتيح استخداماً:**"""

            for i, (key, license_key) in enumerate(top_keys, 1):
                username = license_key.username or "غير محدد"
                message += f"\n{i}. {username} - {license_key.total_uses} استخدام"
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع لإدارة المفاتيح", callback_data="admin_keys")]]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "keys_delete_user" and user_id == Config.MASTER_USER_ID:
            message = """🗑️ **حذف مستخدم من مفتاح**

استخدم الأمر التالي:

📝 `/deleteuser مفتاح_التفعيل`

مثال: `/deleteuser GOLD-ABC1-DEF2-GHI3`

⚠️ **تأثير الحذف:**
• سيتم إلغاء ربط المستخدم بالمفتاح
• سيتم إعادة تعيين استخدام المفتاح إلى صفر
• سيصبح المفتاح متاحاً لمستخدم جديد
• لن يتمكن المستخدم المحذوف من استخدام البوت"""

            keyboard = [[InlineKeyboardButton("🔙 رجوع لإدارة المفاتيح", callback_data="admin_keys")]]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        else:
            await query.edit_message_text(
                "❌ خيار غير معروف. استخدم /start للعودة للقائمة الرئيسية."
            )
        
    except Exception as e:
        logger.error(f"Error in callback query '{data}': {e}")
        await query.edit_message_text(
            "❌ حدث خطأ تقني.\n\nاستخدم /start للمتابعة."
        )

# ==================== Error Handler ====================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأخطاء"""
    logger.error(f"Exception while handling an update: {context.error}")

# ==================== Health Server for Railway ====================
def create_health_server():
    """إنشاء سيرفر بسيط لـ Railway health check"""
    app = Flask(__name__)
    
    @app.route('/')
    def health_check():
        return "Gold Nightmare Bot is running! 🔥", 200
    
    @app.route('/health')
    def health():
        return {"status": "healthy", "bot": "Gold Nightmare"}, 200
    
    return app

# ==================== Cleanup Function ====================
async def cleanup_telegram_bot():
    """تنظيف البوت من أي webhook أو polling سابق"""
    try:
        # حذف الـ webhook إذا كان موجود
        delete_webhook_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/deleteWebhook"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(delete_webhook_url) as response:
                result = await response.json()
                if result.get('ok'):
                    print("✅ تم تنظيف الـ webhook بنجاح")
                else:
                    print("⚠️ لم يتم العثور على webhook للحذف")
        
        # انتظار قصير للتأكد من التنظيف
        await asyncio.sleep(2)
        
    except Exception as e:
        print(f"⚠️ خطأ في تنظيف الـ webhook: {e}")

# ==================== Main Function المحسنة ====================
async def main():
    """الدالة الرئيسية المحسنة"""
    
    # التحقق من متغيرات البيئة
    if not Config.TELEGRAM_BOT_TOKEN:
        print("❌ خطأ: TELEGRAM_BOT_TOKEN غير موجود في متغيرات البيئة")
        return
    
    if not Config.CLAUDE_API_KEY:
        print("❌ خطأ: CLAUDE_API_KEY غير موجود في متغيرات البيئة")
        return
    
    print("🚀 بدء تشغيل Gold Nightmare Bot...")
    print(f"🔥 الكلمة السحرية للتحليل الخاص: '{Config.NIGHTMARE_TRIGGER}'")
    
    # تنظيف البوت من أي webhook سابق
    await cleanup_telegram_bot()
    
    # إنشاء التطبيق مع إعدادات محسنة
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
    await db_manager.load_data()
    await license_manager.initialize()
    
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
    
    # معالجات الرسائل
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    
    # معالج الأزرار
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # معالج الأخطاء
    application.add_error_handler(error_handler)
    
    print("✅ تم تشغيل البوت بنجاح!")
    print(f"📊 تم تحميل {len(license_manager.license_keys)} مفتاح تفعيل")
    print(f"👥 تم تحميل {len(db_manager.users)} مستخدم")
    print(f"🎯 كل مفتاح يعطي 3 رسائل يومياً ويتجدد كل 24 ساعة بالضبط")
    print("="*50)
    print("🤖 البوت يعمل الآن... اضغط Ctrl+C للإيقاف")
    
    # تشغيل البوت مع معالجة محسنة للأخطاء
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            await application.initialize()
            await application.start()
            
            # بدء الـ polling مع إعدادات محسنة لتجنب الـ conflicts
            await application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,  # حذف الرسائل المعلقة
                timeout=10,                 # timeout أقل لتجنب المشاكل
                bootstrap_retries=5,        # محاولات إعادة الاتصال
                read_timeout=30,           # timeout للقراءة
                write_timeout=30,          # timeout للكتابة
                connect_timeout=60,        # timeout للاتصال
                pool_timeout=1             # timeout للـ pool
            )
            
            print("✅ تم بدء الـ polling بنجاح!")
            break  # خروج من الـ loop عند النجاح
            
        except Exception as e:
            retry_count += 1
            print(f"❌ خطأ في محاولة {retry_count}: {e}")
            
            if retry_count < max_retries:
                print(f"🔄 إعادة المحاولة خلال 5 ثوانٍ... ({retry_count}/{max_retries})")
                await asyncio.sleep(5)
                await cleanup_telegram_bot()  # تنظيف قبل إعادة المحاولة
            else:
                print("❌ فشل في بدء البوت بعد عدة محاولات")
                logger.error(f"Failed to start bot after {max_retries} attempts: {e}")
                return
    
    # انتظار إشارة الإيقاف
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 تم استلام إشارة الإيقاف...")
    except Exception as e:
        print(f"❌ خطأ أثناء تشغيل البوت: {e}")
        logger.error(f"Runtime error: {e}")
    finally:
        # تنظيف محسن للموارد
        try:
            print("🧹 جاري تنظيف الموارد...")
            
            # إيقاف الـ updater أولاً
            if hasattr(application, 'updater') and application.updater and application.updater.running:
                await application.updater.stop()
                print("✅ تم إيقاف الـ updater")
            
            # ثم إيقاف التطبيق
            if hasattr(application, 'running') and application.running:
                await application.stop()
                print("✅ تم إيقاف التطبيق")
                
            # إغلاق التطبيق
            if hasattr(application, 'shutdown'):
                await application.shutdown()
                print("✅ تم إغلاق التطبيق")
            
            # حفظ البيانات
            if 'gold_price_manager' in locals():
                await gold_price_manager.close()
            if 'db_manager' in locals():
                await db_manager.save_data()
            if 'license_manager' in locals():
                await license_manager.save_keys()
            
            print("💾 تم حفظ البيانات بنجاح")
            print("👋 تم إيقاف البوت")
            
        except Exception as cleanup_error:
            print(f"⚠️ خطأ في التنظيف: {cleanup_error}")
            logger.error(f"Cleanup error: {cleanup_error}")

def run_bot():
    """تشغيل البوت مع إدارة صحيحة لـ event loop و Railway"""
    import platform
    import threading
    
    # إصلاح مشكلة Windows مع asyncio
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # تشغيل Flask server في thread منفصل لـ Railway
    port = int(os.environ.get('PORT', 8080))
    app = create_health_server()
    
    def run_flask():
        try:
            app.run(host='0.0.0.0', port=port, debug=False)
        except Exception as e:
            print(f"⚠️ خطأ في Flask server: {e}")
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    print(f"🌐 Health server started on port {port}")
    
    # تشغيل البوت مع معالجة محسنة للأخطاء
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        
        try:
            # إنشاء event loop جديد
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            print(f"🔄 محاولة تشغيل البوت {attempt}/{max_attempts}")
            
            # تشغيل البوت
            loop.run_until_complete(main())
            break  # خروج من الـ loop عند النجاح
            
        except KeyboardInterrupt:
            print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
            break
        except Exception as e:
            print(f"❌ خطأ في محاولة {attempt}: {e}")
            logger.error(f"Critical error in run_bot attempt {attempt}: {e}")
            
            if attempt < max_attempts:
                print(f"⏳ انتظار 10 ثوانٍ قبل إعادة المحاولة...")
                import time
                time.sleep(10)
            else:
                print("❌ فشل في تشغيل البوت بعد عدة محاولات")
                
        finally:
            # إغلاق event loop بأمان
            try:
                if 'loop' in locals() and not loop.is_closed():
                    # إلغاء جميع المهام المعلقة
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        for task in pending:
                            task.cancel()
                        
                        # انتظار إنهاء المهام
                        try:
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except:
                            pass
                    
                    # إغلاق event loop
                    loop.close()
                    
            except Exception as loop_error:
                print(f"⚠️ خطأ في إغلاق event loop: {loop_error}")

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    🔥 Gold Nightmare Bot 🔥                    ║
║                  Advanced Gold Analysis System                ║
║                     Version 6.0 Professional Enhanced        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🚀 المميزات الجديدة:                                        ║
║  • 40 مفتاح تفعيل أولي (3 رسائل/يوم)                       ║
║  • تجديد دقيق كل 24 ساعة بالضبط                            ║
║  • أزرار تفاعلية للمفعلين فقط                               ║
║  • لوحة إدارة شاملة للمشرف                                  ║
║  • تحليل خاص بكلمة "{Config.NIGHTMARE_TRIGGER}"                            ║
║  • إدارة متقدمة للمستخدمين والمفاتيح                        ║
║  • تنسيقات جميلة وتحليلات احترافية                          ║
║  • تحليل بـ 8000 توكن للدقة القصوى                         ║
║  • حل مشاكل الـ Telegram Conflicts                          ║
║                                                              ║
║  🔑 الكلمة السحرية: {Config.NIGHTMARE_TRIGGER}                            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    run_bot()
