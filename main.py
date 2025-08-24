#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gold Nightmare Bot - Webhook Version with Message-Based License System
بوت تحليل الذهب الاحترافي - نسخة Webhook مع نظام المفاتيح بالرسائل
Version: 7.0 Professional Webhook Edition
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
from datetime import datetime, timedelta
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
from flask import Flask, request, jsonify
import threading

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

# Load environment variables
load_dotenv()

# ==================== Configuration ====================
class Config:
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    MASTER_USER_ID = int(os.getenv("MASTER_USER_ID", "590918137"))
    
    # Webhook Configuration for Render
    RENDER_APP_URL = os.getenv("RENDER_EXTERNAL_URL", "")
    WEBHOOK_PATH = "/webhook"
    PORT = int(os.getenv("PORT", "8080"))
    
    # Claude Configuration
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    CLAUDE_MAX_TOKENS = 4000
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
    
    # Default messages per key
    DEFAULT_MESSAGES_PER_KEY = 100

# ==================== Logging Setup ====================
def setup_logging():
    """Configure advanced logging"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Simple formatter for Render
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
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
    license_keys: List[str] = field(default_factory=list)  # قائمة المفاتيح المستخدمة

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
    total_messages: int = 100  # عدد الرسائل الكلي
    used_messages: int = 0      # عدد الرسائل المستخدمة
    remaining_messages: int = 100  # عدد الرسائل المتبقية
    is_active: bool = True
    is_exhausted: bool = False  # هل انتهت الرسائل
    user_id: Optional[int] = None
    username: Optional[str] = None
    notes: str = ""
    activated_date: Optional[datetime] = None

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

# ==================== License Manager (Message-Based) ====================
class LicenseManager:
    def __init__(self, keys_file: str = None):
        self.keys_file = keys_file or Config.KEYS_FILE
        self.license_keys: Dict[str, LicenseKey] = {}
        
    async def initialize(self):
        """تحميل المفاتيح وإنشاء المفاتيح الأولية"""
        await self.load_keys()
        
        # إنشاء مفاتيح أولية إذا لم توجد
        if len(self.license_keys) == 0:
            logger.info("Creating initial license keys...")
            await self.generate_initial_keys(10)  # 10 مفاتيح أولية
            await self.save_keys()
    
    async def generate_initial_keys(self, count: int = 10):
        """إنشاء المفاتيح الأولية"""
        logger.info(f"🔑 Creating {count} initial license keys...")
        
        for i in range(count):
            key = self.generate_unique_key()
            license_key = LicenseKey(
                key=key,
                created_date=datetime.now(),
                total_messages=Config.DEFAULT_MESSAGES_PER_KEY,
                remaining_messages=Config.DEFAULT_MESSAGES_PER_KEY,
                notes=f"مفتاح أولي رقم {i+1}"
            )
            self.license_keys[key] = license_key
        
        logger.info(f"✅ Created {count} initial keys successfully!")
        
        # طباعة المفاتيح للمسؤول
        print("\n" + "="*70)
        print("🔑 مفاتيح التفعيل المُنشأة (احفظها في مكان آمن):")
        print("="*70)
        for i, (key, _) in enumerate(self.license_keys.items(), 1):
            print(f"{i:2d}. {key}")
        print("="*70)
        print(f"💡 كل مفتاح يعطي {Config.DEFAULT_MESSAGES_PER_KEY} رسالة")
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
    
    async def create_new_key(self, total_messages: int = 100, notes: str = "") -> str:
        """إنشاء مفتاح جديد بعدد رسائل محدد"""
        key = self.generate_unique_key()
        license_key = LicenseKey(
            key=key,
            created_date=datetime.now(),
            total_messages=total_messages,
            remaining_messages=total_messages,
            notes=notes
        )
        self.license_keys[key] = license_key
        await self.save_keys()
        return key
    
    async def load_keys(self):
        """تحميل المفاتيح من الملف"""
        try:
            if os.path.exists(self.keys_file):
                async with aiofiles.open(self.keys_file, 'r', encoding='utf-8') as f:
                    data = json.loads(await f.read())
                    
                    for key_data in data.get('keys', []):
                        # التوافق مع النظام القديم والجديد
                        total_msgs = key_data.get('total_messages', 100)
                        used_msgs = key_data.get('used_messages', 0)
                        
                        key = LicenseKey(
                            key=key_data['key'],
                            created_date=datetime.fromisoformat(key_data['created_date']),
                            total_messages=total_msgs,
                            used_messages=used_msgs,
                            remaining_messages=total_msgs - used_msgs,
                            is_active=key_data.get('is_active', True),
                            is_exhausted=key_data.get('is_exhausted', False),
                            user_id=key_data.get('user_id'),
                            username=key_data.get('username'),
                            notes=key_data.get('notes', ''),
                            activated_date=datetime.fromisoformat(key_data['activated_date']) if key_data.get('activated_date') else None
                        )
                        
                        # تحديث حالة الانتهاء
                        if key.remaining_messages <= 0:
                            key.is_exhausted = True
                            key.is_active = False
                        
                        self.license_keys[key.key] = key
                    
                    logger.info(f"✅ Loaded {len(self.license_keys)} keys")
        except FileNotFoundError:
            logger.info("📝 Keys file not found, will create new one")
            self.license_keys = {}
        except Exception as e:
            logger.error(f"❌ Error loading keys: {e}")
            self.license_keys = {}
    
    async def save_keys(self):
        """حفظ المفاتيح في الملف"""
        try:
            data = {
                'keys': [
                    {
                        'key': key.key,
                        'created_date': key.created_date.isoformat(),
                        'total_messages': key.total_messages,
                        'used_messages': key.used_messages,
                        'remaining_messages': key.remaining_messages,
                        'is_active': key.is_active,
                        'is_exhausted': key.is_exhausted,
                        'user_id': key.user_id,
                        'username': key.username,
                        'notes': key.notes,
                        'activated_date': key.activated_date.isoformat() if key.activated_date else None
                    }
                    for key in self.license_keys.values()
                ]
            }
            
            async with aiofiles.open(self.keys_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
                
        except Exception as e:
            logger.error(f"❌ Error saving keys: {e}")
    
    async def validate_key(self, key: str, user_id: int) -> Tuple[bool, str]:
        """فحص صحة المفتاح"""
        if key not in self.license_keys:
            return False, "❌ مفتاح التفعيل غير صالح"
        
        license_key = self.license_keys[key]
        
        if not license_key.is_active:
            return False, "❌ مفتاح التفعيل معطل"
        
        if license_key.is_exhausted:
            return False, "❌ مفتاح التفعيل منتهي الصلاحية (نفذت جميع الرسائل)"
        
        if license_key.user_id and license_key.user_id != user_id:
            return False, "❌ مفتاح التفعيل مستخدم من قبل مستخدم آخر"
        
        if license_key.remaining_messages <= 0:
            license_key.is_exhausted = True
            license_key.is_active = False
            await self.save_keys()
            return False, "❌ نفذت جميع الرسائل في هذا المفتاح"
        
        return True, "✅ مفتاح صالح"
    
    async def use_key(self, key: str, user_id: int, username: str = None) -> Tuple[bool, str]:
        """استخدام المفتاح (خصم رسالة)"""
        is_valid, message = await self.validate_key(key, user_id)
        
        if not is_valid:
            return False, message
        
        license_key = self.license_keys[key]
        
        # ربط المفتاح بالمستخدم إذا لم يكن مربوطاً
        if not license_key.user_id:
            license_key.user_id = user_id
            license_key.username = username
            license_key.activated_date = datetime.now()
        
        # خصم رسالة
        license_key.used_messages += 1
        license_key.remaining_messages = license_key.total_messages - license_key.used_messages
        
        # تحديث حالة المفتاح
        if license_key.remaining_messages <= 0:
            license_key.is_exhausted = True
            license_key.is_active = False
        
        await self.save_keys()
        
        # إنشاء رسالة الرد
        remaining = license_key.remaining_messages
        
        if remaining == 0:
            return True, f"✅ تم استخدام المفتاح\n⚠️ انتهت جميع الرسائل! المفتاح لم يعد صالحاً."
        elif remaining <= 5:
            return True, f"✅ تم استخدام المفتاح\n⚠️ تبقى {remaining} رسائل فقط!"
        elif remaining <= 20:
            return True, f"✅ تم استخدام المفتاح\n📊 الرسائل المتبقية: {remaining}"
        else:
            return True, f"✅ تم استخدام المفتاح\n📊 متبقي: {remaining} رسالة"
    
    async def get_key_info(self, key: str) -> Optional[Dict]:
        """الحصول على معلومات المفتاح"""
        if key not in self.license_keys:
            return None
        
        license_key = self.license_keys[key]
        
        return {
            'key': key,
            'is_active': license_key.is_active,
            'is_exhausted': license_key.is_exhausted,
            'total_messages': license_key.total_messages,
            'used_messages': license_key.used_messages,
            'remaining_messages': license_key.remaining_messages,
            'user_id': license_key.user_id,
            'username': license_key.username,
            'created_date': license_key.created_date.strftime('%Y-%m-%d'),
            'activated_date': license_key.activated_date.strftime('%Y-%m-%d') if license_key.activated_date else 'غير مفعل',
            'notes': license_key.notes
        }
    
    async def get_all_keys_stats(self) -> Dict:
        """إحصائيات جميع المفاتيح"""
        total_keys = len(self.license_keys)
        active_keys = sum(1 for key in self.license_keys.values() if key.is_active)
        used_keys = sum(1 for key in self.license_keys.values() if key.user_id is not None)
        exhausted_keys = sum(1 for key in self.license_keys.values() if key.is_exhausted)
        
        total_messages = sum(key.total_messages for key in self.license_keys.values())
        used_messages = sum(key.used_messages for key in self.license_keys.values())
        remaining_messages = sum(key.remaining_messages for key in self.license_keys.values())
        
        return {
            'total_keys': total_keys,
            'active_keys': active_keys,
            'used_keys': used_keys,
            'unused_keys': total_keys - used_keys,
            'exhausted_keys': exhausted_keys,
            'total_messages': total_messages,
            'used_messages': used_messages,
            'remaining_messages': remaining_messages,
            'avg_usage_per_key': used_messages / used_keys if used_keys > 0 else 0
        }

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
        # الاحتفاظ بآخر 1000 تحليل فقط لتوفير الذاكرة
        if len(self.analyses) > 1000:
            self.analyses = self.analyses[-1000:]
        await self.save_data()
    
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
            image.save(buffer, format='JPEG', quality=85, optimize=True)
            
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
        """تحليل الذهب مع Claude"""
        
        is_nightmare_analysis = Config.NIGHTMARE_TRIGGER in prompt
        
        if is_nightmare_analysis:
            analysis_type = AnalysisType.NIGHTMARE
        
        system_prompt = self._build_system_prompt(analysis_type, gold_price)
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
    
    def _build_system_prompt(self, analysis_type: AnalysisType, gold_price: GoldPrice) -> str:
        """بناء برومبت النظام"""
        base_prompt = f"""أنت خبير عالمي في أسواق المعادن الثمينة والذهب مع خبرة +25 سنة في:
• التحليل الفني والكمي المتقدم
• اكتشاف النماذج الفنية والإشارات
• إدارة المخاطر والمحافظ الاستثمارية
• نقاط الانعكاس ومستويات الدعم والمقاومة

البيانات الحية:
💰 السعر: ${gold_price.price}
📊 التغيير 24h: {gold_price.change_24h:+.2f} ({gold_price.change_percentage:+.2f}%)
📈 المدى: ${gold_price.low_24h} - ${gold_price.high_24h}
⏰ الوقت: {gold_price.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"""
        
        if analysis_type == AnalysisType.NIGHTMARE:
            base_prompt += """

🔥🔥🔥 **التحليل الخاص - كابوس الذهب** 🔥🔥🔥
تحليل احترافي شامل يشمل:
• تحليل الأطر الزمنية المتعددة
• مناطق الدخول والخروج الدقيقة
• مستويات الدعم والمقاومة
• استراتيجيات السكالبينج والسوينج
• نسب الثقة المبررة
• توصيات إدارة المخاطر"""
        
        elif analysis_type == AnalysisType.QUICK:
            base_prompt += "\n⚡ تحليل سريع: 150 كلمة فقط، توصية واضحة"
        elif analysis_type == AnalysisType.SCALPING:
            base_prompt += "\n⚡ سكالبينج: نقاط دخول وخروج لـ 5-15 دقيقة"
        
        return base_prompt + "\n\n⚠️ ملاحظة: هذا تحليل تعليمي وليس نصيحة استثمارية"
    
    def _build_user_prompt(self, prompt: str, gold_price: GoldPrice, analysis_type: AnalysisType) -> str:
        """بناء برومبت المستخدم"""
        return f"""السعر الحالي: ${gold_price.price}
نوع التحليل: {analysis_type.value}
الطلب: {prompt}

قدم تحليلاً احترافياً منسقاً وواضحاً."""

# ==================== Security Manager ====================
class SecurityManager:
    def __init__(self):
        self.blocked_users: set = set()
        self.user_keys: Dict[int, str] = {}  # ربط المستخدم بآخر مفتاح استخدمه
    
    def is_blocked(self, user_id: int) -> bool:
        """فحص الحظر"""
        return user_id in self.blocked_users
    
    def link_user_to_key(self, user_id: int, key: str):
        """ربط المستخدم بمفتاح"""
        self.user_keys[user_id] = key

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
            part + (f"\n\n📄 الجزء {i+1}/{len(parts)}" if len(parts) > 1 else ""),
            parse_mode=parse_mode
        )
        await asyncio.sleep(0.5)

def create_main_keyboard(user: User) -> InlineKeyboardMarkup:
    """إنشاء لوحة المفاتيح الرئيسية"""
    is_activated = user.is_activated or user.user_id == Config.MASTER_USER_ID
    
    if not is_activated:
        keyboard = [
            [InlineKeyboardButton("💰 سعر الذهب الآن", callback_data="price_now")],
            [InlineKeyboardButton("🔑 كيفية الحصول على مفتاح", callback_data="how_to_get_license")],
            [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odai_xau")]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("⚡ تحليل سريع", callback_data="analysis_quick"),
                InlineKeyboardButton("📊 تحليل مفصل", callback_data="analysis_detailed")
            ],
            [
                InlineKeyboardButton("🎯 سكالبينج", callback_data="analysis_scalping"),
                InlineKeyboardButton("📈 سوينج", callback_data="analysis_swing")
            ],
            [
                InlineKeyboardButton("🔮 توقعات", callback_data="analysis_forecast"),
                InlineKeyboardButton("🔄 مناطق انعكاس", callback_data="analysis_reversal")
            ],
            [
                InlineKeyboardButton("💰 سعر الذهب", callback_data="price_now"),
                InlineKeyboardButton("📰 تحليل الأخبار", callback_data="analysis_news")
            ],
            [InlineKeyboardButton("🔑 معلومات المفتاح", callback_data="key_info")]
        ]
        
        if user.user_id == Config.MASTER_USER_ID:
            keyboard.append([InlineKeyboardButton("👨‍💼 لوحة الإدارة", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

def create_admin_keyboard() -> InlineKeyboardMarkup:
    """لوحة الإدارة"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 إحصائيات عامة", callback_data="admin_stats"),
            InlineKeyboardButton("🔑 إدارة المفاتيح", callback_data="admin_keys")
        ],
        [
            InlineKeyboardButton("➕ إنشاء مفاتيح", callback_data="admin_create_keys"),
            InlineKeyboardButton("📋 عرض المفاتيح", callback_data="admin_show_keys")
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

# ==================== Decorators ====================
def require_activation(func):
    """Decorator لفحص التفعيل"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if context.bot_data['security'].is_blocked(user_id):
            await update.message.reply_text("❌ حسابك محظور.")
            return
        
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
                "استخدم: /activate مفتاح_التفعيل\n\n"
                "💬 للتواصل: @Odai_xau"
            )
            return
        
        # فحص واستخدام المفتاح
        if user_id != Config.MASTER_USER_ID and user.license_keys:
            license_manager = context.bot_data['license_manager']
            current_key = user.license_keys[-1]  # آخر مفتاح مستخدم
            
            success, message = await license_manager.use_key(
                current_key, 
                user_id, 
                user.username
            )
            
            if not success:
                await update.message.reply_text(
                    f"{message}\n\n"
                    "🔑 تحتاج إلى مفتاح جديد\n"
                    "استخدم: /activate مفتاح_جديد"
                )
                return
        
        user.last_activity = datetime.now()
        user.total_requests += 1
        await context.bot_data['db'].add_user(user)
        context.user_data['user'] = user
        
        return await func(update, context, *args, **kwargs)
    return wrapper

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
    """أمر البداية"""
    user_id = update.effective_user.id
    
    user = await context.bot_data['db'].get_user(user_id)
    if not user:
        user = User(
            user_id=user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name
        )
        await context.bot_data['db'].add_user(user)
    
    welcome_message = f"""💎🔥 مرحباً {update.effective_user.first_name} في Gold Nightmare 🔥💎

⚡ أقوى بوت تحليل الذهب في التيليجرام ⚡
🎯 بتقنية الذكاء الاصطناعي المتقدمة

╔═══════════════════════════════════════╗
║     🆕 نظام المفاتيح الجديد 🆕      ║
╚═══════════════════════════════════════╝

📊 كل مفتاح = 100 رسالة تحليل
🔄 المفتاح ينتهي عند انتهاء الرسائل
✨ لا حاجة للتجديد اليومي!"""

    is_activated = user.is_activated or user_id == Config.MASTER_USER_ID
    
    if is_activated:
        # حساب الرسائل المتبقية
        remaining_messages = 0
        if user.license_keys and context.bot_data['license_manager']:
            last_key = user.license_keys[-1]
            key_info = await context.bot_data['license_manager'].get_key_info(last_key)
            if key_info:
                remaining_messages = key_info['remaining_messages']
        
        welcome_message += f"""

╔═══════════════════════════════════════╗
║    🌟 حسابك مُفعّل ونشط 🌟         ║
╚═══════════════════════════════════════╝

✅ يمكنك استخدام جميع الميزات
📊 الرسائل المتبقية: {remaining_messages if remaining_messages > 0 else "غير محدود"}

🔥 الكلمة السحرية: "{Config.NIGHTMARE_TRIGGER}"

اختر من القائمة أدناه:"""
    else:
        welcome_message += """

╔═══════════════════════════════════════╗
║    🔑 تحتاج إلى مفتاح تفعيل 🔑      ║
╚═══════════════════════════════════════╝

للحصول على مفتاح:
👨‍💼 تواصل مع: @Odai_xau

🎁 عرض خاص: 100 رسالة لكل مفتاح!

💡 استخدم: /activate مفتاح_التفعيل"""
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=create_main_keyboard(user)
    )

async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر تفعيل المفتاح"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "🔑 تفعيل مفتاح الترخيص\n\n"
            "الاستخدام: /activate مفتاح_التفعيل\n\n"
            "مثال: /activate GOLD-ABC1-DEF2-GHI3"
        )
        return
    
    license_key = context.args[0].upper().strip()
    license_manager = context.bot_data['license_manager']
    
    # فحص صحة المفتاح
    is_valid, message = await license_manager.validate_key(license_key, user_id)
    
    if not is_valid:
        await update.message.reply_text(f"❌ فشل التفعيل\n\n{message}")
        return
    
    # جلب أو إنشاء المستخدم
    user = await context.bot_data['db'].get_user(user_id)
    if not user:
        user = User(
            user_id=user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name
        )
    
    # تفعيل المستخدم
    if license_key not in user.license_keys:
        user.license_keys.append(license_key)
    user.is_activated = True
    user.activation_date = datetime.now()
    await context.bot_data['db'].add_user(user)
    
    # ربط المفتاح بالمستخدم
    context.bot_data['security'].link_user_to_key(user_id, license_key)
    
    # الحصول على معلومات المفتاح
    key_info = await license_manager.get_key_info(license_key)
    
    success_message = f"""✅ تم التفعيل بنجاح!

🔑 المفتاح: {license_key[:8]}***
📊 الرسائل المتاحة: {key_info['remaining_messages']} رسالة
🎯 جاهز للاستخدام!

🔥 الكلمة السحرية: "{Config.NIGHTMARE_TRIGGER}"

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
async def createkeys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء مفاتيح جديدة (للمشرف)"""
    count = 1
    messages_per_key = 100
    
    if context.args:
        try:
            count = int(context.args[0])
            if len(context.args) > 1:
                messages_per_key = int(context.args[1])
        except ValueError:
            await update.message.reply_text(
                "❌ استخدام خاطئ\n\n"
                "الصيغة: /createkeys [عدد] [رسائل]\n"
                "مثال: /createkeys 5 100"
            )
            return
    
    if count > 50:
        await update.message.reply_text("❌ لا يمكن إنشاء أكثر من 50 مفتاح")
        return
    
    license_manager = context.bot_data['license_manager']
    
    status_msg = await update.message.reply_text(f"⏳ جاري إنشاء {count} مفتاح...")
    
    created_keys = []
    for i in range(count):
        key = await license_manager.create_new_key(
            total_messages=messages_per_key,
            notes=f"مفتاح مُنشأ بواسطة المشرف - {datetime.now().strftime('%Y-%m-%d')}"
        )
        created_keys.append(key)
    
    keys_text = "\n".join([f"{i+1}. `{key}`" for i, key in enumerate(created_keys)])
    
    result_message = f"""✅ تم إنشاء {count} مفتاح بنجاح!

📊 عدد الرسائل لكل مفتاح: {messages_per_key}
🔑 المفاتيح:

{keys_text}

💡 تعليمات للمستخدمين:
• كل مفتاح يعطي {messages_per_key} رسالة
• استخدام: /activate GOLD-XXXX-XXXX-XXXX
• الكلمة السحرية: "{Config.NIGHTMARE_TRIGGER}\""""
    
    await status_msg.edit_text(result_message, parse_mode=ParseMode.MARKDOWN)

# ==================== Message Handlers ====================
@require_activation
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية"""
    user = context.user_data.get('user')
    if not user:
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    is_nightmare = Config.NIGHTMARE_TRIGGER in update.message.text
    
    if is_nightmare:
        processing_msg = await update.message.reply_text(
            "🔥🔥🔥 كابوس الذهب 🔥🔥🔥\n\n"
            "⚡ تحضير التحليل المتقدم الشامل..."
        )
    else:
        processing_msg = await update.message.reply_text("🧠 جاري التحليل الاحترافي...")
    
    try:
        price = await context.bot_data['gold_price_manager'].get_gold_price()
        if not price:
            await processing_msg.edit_text("❌ لا يمكن الحصول على السعر حالياً.")
            return
        
        text_lower = update.message.text.lower()
        analysis_type = AnalysisType.DETAILED
        
        if Config.NIGHTMARE_TRIGGER in update.message.text:
            analysis_type = AnalysisType.NIGHTMARE
        elif any(word in text_lower for word in ['سريع', 'بسرعة', 'quick']):
            analysis_type = AnalysisType.QUICK
        elif any(word in text_lower for word in ['سكالب', 'scalp']):
            analysis_type = AnalysisType.SCALPING
        
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
        
        user.total_analyses += 1
        await context.bot_data['db'].add_user(user)
        
    except Exception as e:
        logger.error(f"Error in text analysis: {e}")
        await processing_msg.edit_text("❌ حدث خطأ أثناء التحليل.")

@require_activation
async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الصور"""
    user = context.user_data.get('user')
    if not user:
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    
    caption = update.message.caption or ""
    is_nightmare = Config.NIGHTMARE_TRIGGER in caption
    
    if is_nightmare:
        processing_msg = await update.message.reply_text(
            "🔥🔥🔥 تحليل شارت - كابوس الذهب 🔥🔥🔥\n\n"
            "📸 معالجة الصورة بالذكاء الاصطناعي..."
        )
    else:
        processing_msg = await update.message.reply_text("📸 جاري تحليل الشارت...")
    
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
        
        caption = caption or "حلل هذا الشارت بالتفصيل"
        
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
        
        user.total_analyses += 1
        await context.bot_data['db'].add_user(user)
        
    except Exception as e:
        logger.error(f"Error in photo analysis: {e}")
        await processing_msg.edit_text("❌ حدث خطأ أثناء تحليل الصورة.")

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
    
    # الحصول على المستخدم
    user = await context.bot_data['db'].get_user(user_id)
    if not user:
        user = User(
            user_id=user_id,
            username=query.from_user.username,
            first_name=query.from_user.first_name
        )
        await context.bot_data['db'].add_user(user)
    
    # الأوامر المسموحة بدون تفعيل
    allowed_without_license = ["price_now", "how_to_get_license", "back_main"]
    
    # فحص التفعيل للأوامر المحمية
    if (user_id != Config.MASTER_USER_ID and 
        not user.is_activated and 
        data not in allowed_without_license):
        
        await query.edit_message_text(
            "🔑 يتطلب مفتاح تفعيل\n\n"
            "استخدم: /activate مفتاح_التفعيل\n\n"
            "💬 للحصول على مفتاح: @Odai_xau",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 كيف أحصل على مفتاح؟", callback_data="how_to_get_license")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ])
        )
        return
    
    # معالجة الأوامر
    try:
        if data == "price_now":
            price = await context.bot_data['gold_price_manager'].get_gold_price()
            if price:
                price_text = f"""💰 سعر الذهب اللحظي

🏷️ السعر: ${price.price}
📈 التغيير: {price.change_24h:.2f} ({price.change_percentage:+.2f}%)
📊 أعلى 24h: ${price.high_24h}
📉 أدنى 24h: ${price.low_24h}

⏰ التحديث: {price.timestamp.strftime('%H:%M:%S')}
📡 المصدر: {price.source}

🔥 اكتب: "{Config.NIGHTMARE_TRIGGER}" للتحليل الخاص"""
                
                keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
                await query.edit_message_text(
                    price_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text("❌ لا يمكن الحصول على السعر حالياً.")
        
        elif data == "how_to_get_license":
            help_text = """🔑 كيفية الحصول على مفتاح التفعيل

💎 Gold Nightmare Bot يقدم أدق تحليلات الذهب!

📞 للحصول على مفتاح:
👨‍💼 تواصل مع Odai:
- Telegram: @Odai_xau
- Channel: @odai_xauusdt
- Group: @odai_xau_usd

🎁 ماذا تحصل عليه:
• 100 رسالة تحليل احترافية
• تحليل بالذكاء الاصطناعي المتقدم
• تحليل متعدد الأطر الزمنية
• نقاط دخول وخروج دقيقة
• إدارة مخاطر احترافية
• الكلمة السحرية: "{Config.NIGHTMARE_TRIGGER}"

💰 سعر خاص ومحدود!

🌟 انضم لمجتمع النخبة الآن!"""

            keyboard = [
                [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odai_xau")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ]
            
            await query.edit_message_text(
                help_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "key_info":
            if user and user.license_keys:
                last_key = user.license_keys[-1]
                key_info = await context.bot_data['license_manager'].get_key_info(last_key)
                if key_info:
                    info_text = f"""🔑 معلومات المفتاح

🔐 المفتاح: {key_info['key'][:8]}***
📊 إجمالي الرسائل: {key_info['total_messages']}
📈 المستخدم: {key_info['used_messages']}
📉 المتبقي: {key_info['remaining_messages']}
📅 تاريخ الإنشاء: {key_info['created_date']}
✅ الحالة: {'نشط' if key_info['is_active'] else 'منتهي'}

🔥 "{Config.NIGHTMARE_TRIGGER}" للتحليل الخاص"""
                else:
                    info_text = "❌ لا يمكن جلب معلومات المفتاح"
            else:
                info_text = "❌ لا يوجد مفتاح مُفعّل"
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
            await query.edit_message_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "back_main":
            main_message = f"""🆕 Gold Nightmare Bot

🔥 الكلمة السحرية: "{Config.NIGHTMARE_TRIGGER}"

اختر الخدمة المطلوبة:"""
            
            await query.edit_message_text(
                main_message,
                reply_markup=create_main_keyboard(user)
            )
        
        elif data.startswith("analysis_"):
            # فحص واستخدام المفتاح للتحليلات
            if user_id != Config.MASTER_USER_ID and user.license_keys:
                license_manager = context.bot_data['license_manager']
                last_key = user.license_keys[-1]
                success, message = await license_manager.use_key(last_key, user_id, user.username)
                
                if not success:
                    await query.edit_message_text(
                        f"{message}\n\n🔑 تحتاج إلى مفتاح جديد"
                    )
                    return
            
            # معالجة التحليلات
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
                
                prompt = f"تحليل {type_name} للذهب"
                
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
            db_stats = await context.bot_data['db'].get_stats()
            license_stats = await context.bot_data['license_manager'].get_all_keys_stats()
            
            stats_text = f"""📊 **إحصائيات النظام**

🔑 **المفاتيح:**
• إجمالي: {license_stats['total_keys']}
• نشطة: {license_stats['active_keys']}
• مستخدمة: {license_stats['used_keys']}
• منتهية: {license_stats['exhausted_keys']}

📊 **الرسائل:**
• الإجمالي: {license_stats['total_messages']}
• المستخدمة: {license_stats['used_messages']}
• المتبقية: {license_stats['remaining_messages']}

👥 **المستخدمين:**
• الإجمالي: {db_stats['total_users']}
• النشطين: {db_stats['active_users']}

📈 **التحليلات:**
• الإجمالي: {db_stats['total_analyses']}
• آخر 24 ساعة: {db_stats['analyses_24h']}"""

            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
            await query.edit_message_text(
                stats_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "admin_create_keys" and user_id == Config.MASTER_USER_ID:
            await query.edit_message_text(
                "➕ **إنشاء مفاتيح جديدة**\n\n"
                "استخدم الأمر:\n"
                "`/createkeys [عدد] [رسائل]`\n\n"
                "مثال:\n"
                "`/createkeys 5 100` - 5 مفاتيح بـ 100 رسالة\n"
                "`/createkeys 10 50` - 10 مفاتيح بـ 50 رسالة",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
                ])
            )
        
        elif data == "admin_show_keys" and user_id == Config.MASTER_USER_ID:
            license_manager = context.bot_data['license_manager']
            
            if not license_manager.license_keys:
                message = "❌ لا توجد مفاتيح"
            else:
                message = f"🔑 **المفاتيح ({len(license_manager.license_keys)}):**\n\n"
                
                count = 0
                for key, license_key in license_manager.license_keys.items():
                    if count >= 10:
                        break
                    count += 1
                    
                    status = "🟢" if license_key.is_active else "🔴"
                    user_status = f"{license_key.username or 'N/A'}" if license_key.user_id else "متاح"
                    usage = f"{license_key.used_messages}/{license_key.total_messages}"
                    
                    message += f"{count}. `{key[:12]}***`\n"
                    message += f"   {status} {user_status} | {usage}\n\n"
                
                if len(license_manager.license_keys) > 10:
                    message += f"... و {len(license_manager.license_keys) - 10} مفاتيح أخرى"
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
    except Exception as e:
        logger.error(f"Error in callback query '{data}': {e}")
        await query.edit_message_text(
            "❌ حدث خطأ تقني.\n\nاستخدم /start للمتابعة."
        )

# ==================== Flask Server for Webhook ====================
def create_flask_app(application):
    """إنشاء Flask app للـ webhook"""
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "Gold Nightmare Bot is running! 🔥", 200
    
    @app.route('/health')
    def health():
        return {"status": "healthy", "bot": "Gold Nightmare", "version": "7.0"}, 200
    
    @app.route(Config.WEBHOOK_PATH, methods=['POST'])
    async def webhook():
        """استقبال webhook من Telegram"""
        try:
            json_data = request.get_json()
            update = Update.de_json(json_data, application.bot)
            
            # معالجة التحديث بشكل غير متزامن
            await application.process_update(update)
            
            return "OK", 200
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return "Error", 500
    
    return app

# ==================== Main Function ====================
async def main():
    """الدالة الرئيسية"""
    
    # التحقق من متغيرات البيئة
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found")
        return
    
    if not Config.CLAUDE_API_KEY:
        logger.error("❌ CLAUDE_API_KEY not found")
        return
    
    # تحديد URL للـ webhook
    if not Config.RENDER_APP_URL:
        Config.RENDER_APP_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'localhost')}"
    
    webhook_url = f"{Config.RENDER_APP_URL}{Config.WEBHOOK_PATH}"
    
    logger.info("🚀 Starting Gold Nightmare Bot (Webhook Version)...")
    logger.info(f"🔥 Magic word: '{Config.NIGHTMARE_TRIGGER}'")
    logger.info(f"🌐 Webhook URL: {webhook_url}")
    
    # إنشاء التطبيق
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    # إنشاء المكونات
    cache_manager = CacheManager()
    db_manager = DatabaseManager(Config.DB_PATH)
    license_manager = LicenseManager(Config.KEYS_FILE)
    gold_price_manager = GoldPriceManager(cache_manager)
    claude_manager = ClaudeAIManager(cache_manager)
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
        'security': security_manager,
        'cache': cache_manager
    })
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("activate", activate_command))
    application.add_handler(CommandHandler("createkeys", createkeys_command))
    
    # معالجات الرسائل
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    
    # معالج الأزرار
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # تهيئة التطبيق
    await application.initialize()
    
    # إعداد webhook
    try:
        await application.bot.set_webhook(
            url=webhook_url,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        logger.info(f"✅ Webhook set successfully: {webhook_url}")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")
        return
    
    # إنشاء Flask app
    flask_app = create_flask_app(application)
    
    logger.info(f"✅ Bot initialized successfully!")
    logger.info(f"📊 Loaded {len(license_manager.license_keys)} keys")
    logger.info(f"👥 Loaded {len(db_manager.users)} users")
    logger.info(f"🎯 Each key gives 100 messages by default")
    logger.info("="*50)
    logger.info(f"🌐 Server running on port {Config.PORT}")
    logger.info("🤖 Bot is ready to receive webhooks...")
    
    # تشغيل Flask serverimport threading

def run_flask():
    flask_app.run(
        host="0.0.0.0",
        port=Config.PORT,
        debug=False,
        use_reloader=False
    )

# تشغيل Flask في ثريد منفصل
try:
    # تشغيل Flask في ثريد منفصل
    threading.Thread(target=run_flask, daemon=True).start()

except Exception as e:
    logger.error(f"❌ Server error: {e}")

finally:
    # تنظيف الموارد
    await gold_price_manager.close()
    await db_manager.save_data()
    await license_manager.save_keys()
    await application.shutdown()


def run_bot():
    """تشغيل البوت"""
    import platform
    
    # إصلاح مشكلة Windows مع asyncio
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                    🔥 Gold Nightmare Bot 🔥                    ║
║                  Webhook Version for Render                   ║
║                     Version 7.0 Professional                  ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  🚀 الميزات الجديدة:                                          ║
║  • نظام مفاتيح بعدد الرسائل (100 رسالة/مفتاح)                  ║
║  • Webhook للعمل 24/7 على Render                             ║
║  • تحليل متقدم بالذكاء الاصطناعي                               ║
║  • لوحة إدارة شاملة للمشرف                                     ║
║  • الكلمة السحرية: {Config.NIGHTMARE_TRIGGER}                               ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Critical error: {e}")
        logger.error(f"Critical error in run_bot: {e}")

if __name__ == "__main__":
    run_bot()
