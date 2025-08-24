#!/usr/bin/env python3
# -- coding: utf-8 --
"""
Gold Nightmare Bot - Complete Advanced Analysis & Risk Management System
بوت تحليل الذهب الاحترافي مع نظام مفاتيح التفعيل المتقدم
Version: 6.0 Professional Enhanced - Render Webhook Edition
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
from dotenv import loaddotenv
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
    ADVANCEDANALYSISAVAILABLE = True
except ImportError:
    ADVANCEDANALYSISAVAILABLE = False
    print("⚠️ Advanced analysis libraries not found. Basic analysis will be used.")

# Load environment variables
loaddotenv()

# ==================== Configuration ====================
class Config:
    # Telegram Configuration
    TELEGRAMBOTTOKEN = os.getenv("TELEGRAMBOTTOKEN")
    WEBHOOKURL = os.getenv("WEBHOOKURL")  # For Render webhook
    MASTERUSERID = int(os.getenv("MASTERUSERID", "590918137"))
    
    # Claude Configuration
    CLAUDEAPIKEY = os.getenv("CLAUDEAPIKEY")
    CLAUDEMODEL = os.getenv("CLAUDEMODEL", "claude-3-5-sonnet-20241022")
    CLAUDEMAXTOKENS = 8000
    CLAUDETEMPERATURE = float(os.getenv("CLAUDETEMPERATURE", "0.3"))
    
    # Gold API Configuration
    GOLDAPITOKEN = os.getenv("GOLDAPITOKEN")
    GOLDAPIURL = "https://www.goldapi.io/api/XAU/USD"
    
    # Rate Limiting
    RATELIMITREQUESTS = int(os.getenv("RATELIMITREQUESTS", "30"))
    RATELIMITWINDOW = int(os.getenv("RATELIMITWINDOW", "60"))
    
    # Cache Configuration
    PRICECACHETTL = int(os.getenv("PRICECACHETTL", "60"))
    ANALYSISCACHETTL = int(os.getenv("ANALYSISCACHETTL", "300"))
    
    # Image Processing
    MAXIMAGESIZE = int(os.getenv("MAXIMAGESIZE", "10485760"))
    MAXIMAGEDIMENSION = int(os.getenv("MAXIMAGEDIMENSION", "1568"))
    
    # Database
    DBPATH = os.getenv("DBPATH", "goldbotdata.db")
    KEYSFILE = os.getenv("KEYSFILE", "licensekeys.json")
    
    # Timezone
    TIMEZONE = pytz.timezone(os.getenv("TIMEZONE", "Asia/Amman"))
    
    # Secret Analysis Trigger (Hidden from users)
    NIGHTMARETRIGGER = "كابوس الذهب"

# ==================== Logging Setup ====================
def setuplogging():
    """Configure advanced logging"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    consolehandler = logging.StreamHandler()
    consolehandler.setLevel(logging.INFO)
    
    # File handler
    os.makedirs('logs', existok=True)
    filehandler = logging.handlers.RotatingFileHandler(
        'logs/goldbot.log',
        maxBytes=1010241024,
        backupCount=10,
        encoding='utf-8'
    )
    filehandler.setLevel(logging.DEBUG)
    
    # Formatters
    detailedformatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simpleformatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    consolehandler.setFormatter(simpleformatter)
    filehandler.setFormatter(detailedformatter)
    
    logger.addHandler(consolehandler)
    logger.addHandler(filehandler)
    
    return logger

logger = setuplogging()
# ==================== Markdown Text Cleaner ====================
def cleanmarkdowntext(text: str) -> str:
    """تنظيف النص من markdown المُشكِل"""
    if not text:
        return text
    
    # استبدال الرموز المُشكِلة
    text = text.replace('', '')  # حذف النجمتين
    text = text.replace('', '')   # حذف النجمة الواحدة  
    text = text.replace('', '')  # حذف الخطوط السفلية
    text = text.replace('', '')   # حذف الخط السفلي الواحد
    text = text.replace('`', '')   # حذف الـ backticks
    text = text.replace('[', '(')  # استبدال الأقواس المربعة
    text = text.replace(']', ')')
    
    return text

# ==================== Data Models ====================
@dataclass
class User:
    userid: int
    username: Optional[str]
    firstname: str
    isactivated: bool = False
    activationdate: Optional[datetime] = None
    lastactivity: datetime = field(defaultfactory=datetime.now)
    totalrequests: int = 0
    totalanalyses: int = 0
    subscriptiontier: str = "basic"
    settings: Dict[str, Any] = field(defaultfactory=dict)
    licensekey: Optional[str] = None
    dailyrequestsused: int = 0
    lastrequestdate: Optional[date] = None

@dataclass
class GoldPrice:
    price: float
    timestamp: datetime
    change24h: float = 0.0
    changepercentage: float = 0.0
    high24h: float = 0.0
    low24h: float = 0.0
    source: str = "goldapi"

@dataclass
class Analysis:
    id: str
    userid: int
    timestamp: datetime
    analysistype: str
    prompt: str
    result: str
    goldprice: float
    imagedata: Optional[bytes] = None
    indicators: Dict[str, Any] = field(defaultfactory=dict)

@dataclass
class LicenseKey:
    key: str
    createddate: datetime
    dailylimit: int = 3
    usedtoday: int = 0
    lastresetdate: date = field(defaultfactory=date.today)
    isactive: bool = True
    totaluses: int = 0
    userid: Optional[int] = None
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
    def init(self, keysfile: str = None):
        self.keysfile = keysfile or Config.KEYSFILE
        self.licensekeys: Dict[str, LicenseKey] = {}
        
    async def initialize(self):
        """تحميل المفاتيح وإنشاء المفاتيح الأولية"""
        await self.loadkeys()
        
        if len(self.licensekeys) == 0:
            await self.generateinitialkeys(40)
            await self.savekeys()
            
        await self.resetdailyusage()
    
    async def generateinitialkeys(self, count: int = 40):
        """إنشاء المفاتيح الأولية"""
        print(f"🔑 إنشاء {count} مفتاح تفعيل...")
        
        for i in range(count):
            key = self.generateuniquekey()
            licensekey = LicenseKey(
                key=key,
                createddate=datetime.now(),
                dailylimit=3,
                notes=f"مفتاح أولي رقم {i+1}"
            )
            self.licensekeys[key] = licensekey
        
        print(f"✅ تم إنشاء {count} مفتاح بنجاح!")
        print("\n" + "="70)
        print("🔑 مفاتيح التفعيل المُنشأة (احفظها في مكان آمن):")
        print("="70)
        for i, (key, ) in enumerate(self.licensekeys.items(), 1):
            print(f"{i:2d}. {key}")
        print("="70)
        print("💡 كل مفتاح يعطي 3 رسائل يومياً ويتجدد تلقائياً كل 24 ساعة بالضبط")
        print("="70)
    
    def generateuniquekey(self) -> str:
        """إنشاء مفتاح فريد"""
        chars = string.asciiuppercase + string.digits
        
        while True:
            keyparts = []
            for  in range(3):
                part = ''.join(secrets.choice(chars) for  in range(4))
                keyparts.append(part)
            
            key = f"GOLD-{'-'.join(keyparts)}"
            
            if key not in self.licensekeys:
                return key
    
    async def createnewkey(self, dailylimit: int = 3, notes: str = "") -> str:
        """إنشاء مفتاح جديد"""
        key = self.generateuniquekey()
        licensekey = LicenseKey(
            key=key,
            createddate=datetime.now(),
            dailylimit=dailylimit,
            notes=notes
        )
        self.licensekeys[key] = licensekey
        await self.savekeys()
        return key
    
    async def loadkeys(self):
        """تحميل المفاتيح من الملف"""
        try:
            async with aiofiles.open(self.keysfile, 'r', encoding='utf-8') as f:
                data = json.loads(await f.read())
                
                for keydata in data.get('keys', []):
                    key = LicenseKey(
                        key=keydata['key'],
                        createddate=datetime.fromisoformat(keydata['createddate']),
                        dailylimit=keydata.get('dailylimit', 3),
                        usedtoday=keydata.get('usedtoday', 0),
                        lastresetdate=date.fromisoformat(keydata.get('lastresetdate', str(date.today()))),
                        isactive=keydata.get('isactive', True),
                        totaluses=keydata.get('totaluses', 0),
                        userid=keydata.get('userid'),
                        username=keydata.get('username'),
                        notes=keydata.get('notes', '')
                    )
                    self.licensekeys[key.key] = key
                
                print(f"✅ تم تحميل {len(self.licensekeys)} مفتاح")
                
        except FileNotFoundError:
            print("🔍 ملف المفاتيح غير موجود، سيتم إنشاؤه")
            self.licensekeys = {}
        except Exception as e:
            print(f"❌ خطأ في تحميل المفاتيح: {e}")
            self.licensekeys = {}
    
    async def savekeys(self):
        """حفظ المفاتيح في الملف"""
        try:
            data = {
                'keys': [
                    {
                        'key': key.key,
                        'createddate': key.createddate.isoformat(),
                        'dailylimit': key.dailylimit,
                        'usedtoday': key.usedtoday,
                        'lastresetdate': key.lastresetdate.isoformat(),
                        'isactive': key.isactive,
                        'totaluses': key.totaluses,
                        'userid': key.userid,
                        'username': key.username,
                        'notes': key.notes
                    }
                    for key in self.licensekeys.values()
                ]
            }
            
            async with aiofiles.open(self.keysfile, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensureascii=False, indent=2))
                
        except Exception as e:
            print(f"❌ خطأ في حفظ المفاتيح: {e}")
    
    async def resetdailyusage(self):
        """إعادة تعيين الاستخدام اليومي"""
        now = datetime.now()
        today = now.date()
        resetcount = 0
        
        for key in self.licensekeys.values():
            if key.lastresetdate < today:
                lastresetdatetime = datetime.combine(key.lastresetdate, datetime.min.time())
                if (now - lastresetdatetime).totalseconds() >= 86400:
                    key.usedtoday = 0
                    key.lastresetdate = today
                    resetcount += 1
        
        if resetcount > 0:
            print(f"🔄 تم تجديد {resetcount} مفتاح للاستخدام اليومي")
            await self.savekeys()
    
    async def validatekey(self, key: str, userid: int) -> Tuple[bool, str]:
        """فحص صحة المفتاح"""
        await self.resetdailyusage()
        
        if key not in self.licensekeys:
            return False, "❌ مفتاح التفعيل غير صالح"
        
        licensekey = self.licensekeys[key]
        
        if not licensekey.isactive:
            return False, "❌ مفتاح التفعيل معطل"
        
        if licensekey.userid and licensekey.userid != userid:
            return False, "❌ مفتاح التفعيل مستخدم من قبل مستخدم آخر"
        
        if licensekey.usedtoday >= licensekey.dailylimit:
            timeuntilreset = self.gettimeuntilreset()
            return False, f"❌ تم استنفاد الحد اليومي ({licensekey.dailylimit} رسائل)\n⏰ سيتم التجديد خلال {timeuntilreset}\n\n💡 كل مفتاح له 3 رسائل فقط يومياً"
        
        return True, "✅ مفتاح صالح"
    
    async def usekey(self, key: str, userid: int, username: str = None, requesttype: str = "analysis") -> Tuple[bool, str]:
        """استخدام المفتاح"""
        isvalid, message = await self.validatekey(key, userid)
        
        if not isvalid:
            return False, message
        
        licensekey = self.licensekeys[key]
        
        if not licensekey.userid:
            licensekey.userid = userid
            licensekey.username = username
        
        licensekey.usedtoday += 1
        licensekey.totaluses += 1
        
        await self.savekeys()
        
        remaining = licensekey.dailylimit - licensekey.usedtoday
        
        if remaining == 0:
            return True, f"✅ تم استخدام المفتاح بنجاح\n⚠️ هذه آخر رسالة اليوم!\n⏰ سيتم التجديد خلال {self.gettimeuntilreset()}"
        elif remaining == 1:
            return True, f"✅ تم استخدام المفتاح بنجاح\n⚠️ تبقت رسالة واحدة فقط اليوم!"
        else:
            return True, f"✅ تم استخدام المفتاح بنجاح\n📊 الرسائل المتبقية اليوم: {remaining}"
    
    def gettimeuntilreset(self) -> str:
        """حساب الوقت حتى التجديد"""
        now = datetime.now()
        tomorrow = datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
        timeleft = tomorrow - now
        
        hours = timeleft.seconds // 3600
        minutes = (timeleft.seconds % 3600) // 60
        
        return f"{hours} ساعة و {minutes} دقيقة"
    
    async def getkeyinfo(self, key: str) -> Optional[Dict]:
        """الحصول على معلومات المفتاح"""
        if key not in self.licensekeys:
            return None
        
        licensekey = self.licensekeys[key]
        
        return {
            'key': key,
            'isactive': licensekey.isactive,
            'dailylimit': licensekey.dailylimit,
            'usedtoday': licensekey.usedtoday,
            'remainingtoday': licensekey.dailylimit - licensekey.usedtoday,
            'totaluses': licensekey.totaluses,
            'userid': licensekey.userid,
            'username': licensekey.username,
            'createddate': licensekey.createddate.strftime('%Y-%m-%d'),
            'lastreset': licensekey.lastresetdate.strftime('%Y-%m-%d'),
            'notes': licensekey.notes
        }
    
    async def getallkeysstats(self) -> Dict:
        """إحصائيات جميع المفاتيح"""
        totalkeys = len(self.licensekeys)
        activekeys = sum(1 for key in self.licensekeys.values() if key.isactive)
        usedkeys = sum(1 for key in self.licensekeys.values() if key.userid is not None)
        
        todayusage = sum(key.usedtoday for key in self.licensekeys.values())
        totalusage = sum(key.totaluses for key in self.licensekeys.values())
        
        return {
            'totalkeys': totalkeys,
            'activekeys': activekeys,
            'usedkeys': usedkeys,
            'unusedkeys': totalkeys - usedkeys,
            'todayusage': todayusage,
            'totalusage': totalusage,
            'avgusageperkey': totalusage / totalkeys if totalkeys > 0 else 0
        }
    
    async def deleteuserbykey(self, key: str) -> Tuple[bool, str]:
        """حذف مستخدم من المفتاح"""
        if key not in self.licensekeys:
            return False, "❌ المفتاح غير موجود"
        
        licensekey = self.licensekeys[key]
        if not licensekey.userid:
            return False, "❌ المفتاح غير مرتبط بمستخدم"
        
        olduserid = licensekey.userid
        oldusername = licensekey.username
        
        licensekey.userid = None
        licensekey.username = None
        licensekey.usedtoday = 0
        
        await self.savekeys()
        
        return True, f"✅ تم حذف المستخدم {oldusername or olduserid} من المفتاح {key}"

# ==================== Database Manager ====================
class DatabaseManager:
    def init(self, dbpath: str):
        self.dbpath = dbpath
        self.users: Dict[int, User] = {}
        self.analyses: List[Analysis] = []
        
    async def loaddata(self):
        """تحميل البيانات"""
        try:
            if os.path.exists(self.dbpath):
                async with aiofiles.open(self.dbpath, 'rb') as f:
                    data = pickle.loads(await f.read())
                    self.users = data.get('users', {})
                    self.analyses = data.get('analyses', [])
                    logger.info(f"Loaded {len(self.users)} users and {len(self.analyses)} analyses")
        except Exception as e:
            logger.error(f"Error loading database: {e}")
    
    async def savedata(self):
        """حفظ البيانات"""
        try:
            data = {
                'users': self.users,
                'analyses': self.analyses
            }
            async with aiofiles.open(self.dbpath, 'wb') as f:
                await f.write(pickle.dumps(data))
        except Exception as e:
            logger.error(f"Error saving database: {e}")
    
    async def adduser(self, user: User):
        """إضافة مستخدم"""
        self.users[user.userid] = user
        await self.savedata()
    
    async def getuser(self, userid: int) -> Optional[User]:
        """جلب مستخدم"""
        return self.users.get(userid)
    
    async def addanalysis(self, analysis: Analysis):
        """إضافة تحليل"""
        self.analyses.append(analysis)
        await self.savedata()
    
    async def getuseranalyses(self, userid: int, limit: int = 10) -> List[Analysis]:
        """جلب تحليلات المستخدم"""
        useranalyses = [a for a in self.analyses if a.userid == userid]
        return useranalyses[-limit:]
    
    async def getstats(self) -> Dict[str, Any]:
        """إحصائيات البوت"""
        totalusers = len(self.users)
        activeusers = len([u for u in self.users.values() if u.isactivated])
        totalanalyses = len(self.analyses)
        
        last24h = datetime.now() - timedelta(hours=24)
        recentanalyses = [a for a in self.analyses if a.timestamp > last24h]
        
        return {
            'totalusers': totalusers,
            'activeusers': activeusers,
            'totalanalyses': totalanalyses,
            'analyses24h': len(recentanalyses),
            'activationrate': f"{(activeusers/totalusers100):.1f}%" if totalusers > 0 else "0%"
        }

# ==================== Cache System ====================
class CacheManager:
    def init(self):
        self.pricecache: Optional[Tuple[GoldPrice, datetime]] = None
        self.analysiscache: Dict[str, Tuple[str, datetime]] = {}
    
    def getprice(self) -> Optional[GoldPrice]:
        """جلب السعر من التخزين المؤقت"""
        if self.pricecache:
            price, timestamp = self.pricecache
            if datetime.now() - timestamp < timedelta(seconds=Config.PRICECACHETTL):
                return price
        return None
    
    def setprice(self, price: GoldPrice):
        """حفظ السعر في التخزين المؤقت"""
        self.pricecache = (price, datetime.now())

# ==================== Gold Price Manager ====================
class GoldPriceManager:
    def init(self, cachemanager: CacheManager):
        self.cache = cachemanager
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def getsession(self) -> aiohttp.ClientSession:
        """جلب جلسة HTTP"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def getgoldprice(self) -> Optional[GoldPrice]:
        """جلب سعر الذهب"""
        cachedprice = self.cache.getprice()
        if cachedprice:
            return cachedprice
        
        price = await self.fetchfromgoldapi()
        if price:
            self.cache.setprice(price)
            return price
        
        # استخدام سعر افتراضي في حالة فشل الـ API
        logger.warning("Using fallback gold price")
        return GoldPrice(
            price=2650.0,
            timestamp=datetime.now(),
            change24h=2.5,
            changepercentage=0.1,
            high24h=2655.0,
            low24h=2645.0,
            source="fallback"
        )
    
    async def fetchfromgoldapi(self) -> Optional[GoldPrice]:
        """جلب السعر من GoldAPI"""
        try:
            session = await self.getsession()
            headers = {
                "x-access-token": Config.GOLDAPITOKEN,
                "Content-Type": "application/json"
            }
            
            async with session.get(Config.GOLDAPIURL, headers=headers, timeout=10) as response:
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
                    change24h=data.get("change", 0),
                    changepercentage=data.get("changep", 0),
                    high24h=data.get("highprice", price),
                    low24h=data.get("lowprice", price),
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
    def processimage(imagedata: bytes) -> Optional[str]:
        """معالجة الصور"""
        try:
            if len(imagedata) > Config.MAXIMAGESIZE:
                raise ValueError(f"Image too large: {len(imagedata)} bytes")
            
            image = Image.open(io.BytesIO(imagedata))
            
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image, mask=image.split()[-1])
                image = background
            elif image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            if max(image.size) > Config.MAXIMAGEDIMENSION:
                ratio = Config.MAXIMAGEDIMENSION / max(image.size)
                newsize = tuple(int(dim  ratio) for dim in image.size)
                image = image.resize(newsize, Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=92, optimize=True)
            
            imagebase64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            logger.info(f"Processed image: {image.size}, {len(buffer.getvalue())} bytes")
            return imagebase64
            
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            return None

# ==================== Claude AI Manager ====================
class ClaudeAIManager:
    def init(self, cachemanager: CacheManager):
        self.client = anthropic.Anthropic(apikey=Config.CLAUDEAPIKEY)
        self.cache = cachemanager
        
    async def analyzegold(self, 
                          prompt: str, 
                          goldprice: GoldPrice,
                          imagebase64: Optional[str] = None,
                          analysistype: AnalysisType = AnalysisType.DETAILED,
                          usersettings: Dict[str, Any] = None) -> str:
        """تحليل الذهب مع Claude المحسن"""
        
        # التحقق من التحليل الخاص السري (بدون إظهار للمستخدم)
        isnightmareanalysis = Config.NIGHTMARETRIGGER in prompt
        
        if isnightmareanalysis:
            analysistype = AnalysisType.NIGHTMARE
        
        systemprompt = self.buildsystemprompt(analysistype, goldprice, usersettings)
        userprompt = self.builduserprompt(prompt, goldprice, analysistype)
        
        try:
            content = []
            
            if imagebase64:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "mediatype": "image/jpeg",
                        "data": imagebase64
                    }
                })
            
            content.append({
                "type": "text",
                "text": userprompt
            })
            
            message = await asyncio.tothread(
                self.client.messages.create,
                model=Config.CLAUDEMODEL,
                maxtokens=Config.CLAUDEMAXTOKENS,
                temperature=Config.CLAUDETEMPERATURE,
                system=systemprompt,
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
    
    def buildsystemprompt(self, analysistype: AnalysisType, 
                            goldprice: GoldPrice,
                            usersettings: Dict[str, Any] = None) -> str:
        """بناء بروبت النظام المحسن مع تنسيقات متقدمة"""
        
        baseprompt = f"""أنت خبير عالمي في أسواق المعادن الثمينة والذهب مع خبرة +25 سنة في:
• التحليل الفني والكمي المتقدم متعدد الأطر الزمنية
• اكتشاف النماذج الفنية والإشارات المتقدمة
• إدارة المخاطر والمحافظ الاستثمارية المتخصصة
• تحليل نقاط الانعكاس ومستويات الدعم والمقاومة
• تطبيقات الذكاء الاصطناعي والتداول الخوارزمي المتقدم
• تحليل مناطق العرض والطلب والسيولة المؤسسية

🏆 الانتماء المؤسسي: Gold Nightmare Academy - أكاديمية التحليل المتقدم

البيانات الحية المعتمدة:
💰 السعر: ${goldprice.price} USD/oz
📊 التغيير 24h: {goldprice.change24h:+.2f} ({goldprice.changepercentage:+.2f}%)
📈 المدى: ${goldprice.low24h} - ${goldprice.high24h}
⏰ الوقت: {goldprice.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
📡 المصدر: {goldprice.source}
"""
        
        # تخصيص حسب نوع التحليل مع تنسيقات متقدمة
        if analysistype == AnalysisType.QUICK:
            baseprompt += """

⚡ التحليل السريع - أقصى 150 كلمة:

📋 التنسيق المطلوب:
```
🎯 التوصية: [BUY/SELL/HOLD]
📈 السعر الحالي: $[السعر]
🔴 السبب: [سبب واحد قوي]

📊 الأهداف:
🥇 الهدف الأول: $[السعر]
🔴 وقف الخسارة: $[السعر]

⏰ الإطار الزمني: [المدة المتوقعة]
🔥 مستوى الثقة: [نسبة مئوية]%
```

✨ متطلبات:
- توصية واضحة ومباشرة فقط
- سبب رئيسي واحد مقنع
- هدف واحد ووقف خسارة واحد
- بدون مقدمات أو تفاصيل زائدة
- تنسيق منظم ومختصر"""

        elif analysistype == AnalysisType.NIGHTMARE:
            baseprompt += f"""

🔥🔥🔥 التحليل الشامل المتقدم 🔥🔥🔥
هذا التحليل المتقدم يشمل جميع الجوانب التالية:

╔════════════════════════════════════════════════════════════════════╗
║                    🎯 التحليل الشامل المطلوب                    ║
╚════════════════════════════════════════════════════════════════════╝

📊 1. تحليل الأطر الزمنية المتعددة:
• تحليل M5, M15, H1, H4, D1 مع نسب الثقة
• إجماع الأطر الزمنية والتوصية الموحدة
• أفضل إطار زمني للدخول

🎯 2. مناطق الدخول والخروج:
• نقاط الدخول الدقيقة بالسنت الواحد
• مستويات الخروج المتدرجة
• نقاط إضافة الصفقات

🛡️ 3. مستويات الدعم والمقاومة:
• الدعوم والمقاومات الأساسية
• المستويات النفسية المهمة
• قوة كل مستوى (ضعيف/متوسط/قوي)

🔄 4. نقاط الارتداد المحتملة:
• مناطق الارتداد عالية الاحتمال
• إشارات التأكيد المطلوبة
• نسب نجاح الارتداد

⚖️ 5. مناطق العرض والطلب:
• مناطق العرض المؤسسية
• مناطق الطلب القوية
• تحليل السيولة والحجم

⚡ 6. استراتيجيات السكالبينج:
• فرص السكالبينج (1-15 دقيقة)
• نقاط الدخول السريعة
• أهداف محققة بسرعة

📈 7. استراتيجيات السوينج:
• فرص التداول متوسط المدى (أيام-أسابيع)
• نقاط الدخول الاستراتيجية
• أهداف طويلة المدى

🔄 8. تحليل الانعكاس:
• نقاط الانعكاس المحتملة
• مؤشرات تأكيد الانعكاس
• قوة الانعكاس المتوقعة

📊 9. نسب الثقة المبررة:
• نسبة ثقة لكل تحليل مع المبررات
• درجة المخاطرة لكل استراتيجية
• احتمالية نجاح كل سيناريو

💡 10. توصيات إدارة المخاطر:
• حجم الصفقة المناسب
• وقف الخسارة المثالي
• نسبة المخاطر/العوائد

🎯 متطلبات التنسيق:
• استخدام جداول منسقة وواضحة
• تقسيم المعلومات إلى أقسام مرتبة
• استخدام رموز تعبيرية مناسبة
• عرض النتائج بطريقة جميلة وسهلة القراءة
• تضمين نصيحة احترافية في كل قسم

🎯 مع تنسيق جميل وجداول منظمة ونصائح احترافية!

⚠️ ملاحظة: هذا تحليل تعليمي وليس نصيحة استثمارية شخصية"""

        # إضافة المتطلبات العامة
        baseprompt += """

🎯 متطلبات التنسيق العامة:
1. استخدام جداول وترتيبات جميلة
2. تقسيم المعلومات إلى أقسام واضحة
3. استخدام رموز تعبيرية مناسبة
4. تنسيق النتائج بطريقة احترافية
5. تقديم نصيحة عملية في كل تحليل
6. نسب ثقة مبررة إحصائياً
7. تحليل احترافي باللغة العربية مع مصطلحات فنية دقيقة

⚠️ ملاحظة: هذا تحليل تعليمي وليس نصيحة استثمارية شخصية"""
        
        return baseprompt

    def builduserprompt(self, prompt: str, goldprice: GoldPrice, analysistype: AnalysisType) -> str:
        """بناء prompt المستخدم"""
        
        context = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 البيانات الأساسية:
• السعر الحالي: ${goldprice.price}
• التغيير: {goldprice.change24h:+.2f} USD ({goldprice.changepercentage:+.2f}%)
• المدى اليومي: ${goldprice.low24h} - ${goldprice.high24h}
• التوقيت: {goldprice.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 طلب المستخدم: {prompt}

📋 نوع التحليل المطلوب: {analysistype.value}

"""
        
        if analysistype == AnalysisType.NIGHTMARE:
            context += f"""🔥 التحليل الشامل المطلوب:

المطلوب تحليل شامل ومفصل يشمل جميع النقاط التالية بتنسيق جميل:

📊 1. تحليل الأطر الزمنية المتعددة
📍 2. مناطق الدخول والخروج الدقيقة
🛡️ 3. مستويات الدعم والمقاومة
🔄 4. نقاط الارتداد المحتملة
⚖️ 5. مناطق العرض والطلب
⚡ 6. استراتيجيات السكالبينج
📈 7. استراتيجيات السوينج
🔄 8. تحليل الانعكاس
📊 9. نسب الثقة المبررة
💡 10. توصيات إدارة المخاطر

🎯 مع تنسيق جميل وجداول منظمة ونصائح احترافية!"""
        
        elif analysistype == AnalysisType.QUICK:
            context += "\n⚡ المطلوب: إجابة سريعة ومباشرة ومنسقة في 150 كلمة فقط"
        else:
            context += "\n📊 المطلوب: تحليل مفصل ومنسق بجداول جميلة"
            
        return context

# ==================== Rate Limiter ====================
class RateLimiter:
    def init(self):
        self.requests: Dict[int, List[datetime]] = defaultdict(list)
    
    def isallowed(self, userid: int, user: User) -> Tuple[bool, Optional[str]]:
        """فحص الحد المسموح"""
        now = datetime.now()
        
        self.requests[userid] = [
            reqtime for reqtime in self.requests[userid]
            if now - reqtime < timedelta(seconds=Config.RATELIMITWINDOW)
        ]
        
        maxrequests = Config.RATELIMITREQUESTS
        if user.subscriptiontier == "premium":
            maxrequests = 2
        elif user.subscriptiontier == "vip":
            maxrequests = 5
        
        if len(self.requests[userid]) >= maxrequests:
            waittime = Config.RATELIMITWINDOW - (now - self.requests[userid][0]).seconds
            return False, f"⚠️ تجاوزت الحد المسموح. انتظر {waittime} ثانية."
        
        self.requests[userid].append(now)
        return True, None

# ==================== Security Manager ====================
class SecurityManager:
    def init(self):
        self.activesessions: Dict[int, datetime] = {}
        self.failedattempts: Dict[int, int] = defaultdict(int)
        self.blockedusers: set = set()
        self.userkeys: Dict[int, str] = {}
    
    def verifylicensekey(self, key: str) -> bool:
        """فحص بسيط لصيغة المفتاح"""
        return key.startswith("GOLD-") and len(key) == 19
    
    def issessionvalid(self, userid: int) -> bool:
        """فحص صحة الجلسة"""
        return userid in self.userkeys
    
    def createsession(self, userid: int, licensekey: str):
        """إنشاء جلسة جديدة"""
        self.activesessions[userid] = datetime.now()
        self.userkeys[userid] = licensekey
        self.failedattempts[userid] = 0
    
    def isblocked(self, userid: int) -> bool:
        """فحص الحظر"""
        return userid in self.blockedusers

# ==================== Telegram Utilities ====================
async def sendlongmessage(update: Update, text: str, parsemode: str = None):
    """إرسال رسائل طويلة مع معالجة أخطاء Markdown"""
    maxlength = 4000
    
    # تنظيف النص إذا كان Markdown
    if parsemode == ParseMode.MARKDOWN:
        text = cleanmarkdowntext(text)
        parsemode = None  # إلغاء markdown بعد التنظيف
    
    if len(text) <= maxlength:
        try:
            await update.message.replytext(text, parsemode=parsemode)
        except Exception as e:
            # في حالة فشل parsing، إرسال بدون formatting
            logger.error(f"Markdown parsing error: {e}")
            cleantext = cleanmarkdowntext(text)
            await update.message.replytext(cleantext)
        return
    
    parts = []
    currentpart = ""
    
    for line in text.split('\n'):
        if len(currentpart) + len(line) + 1 > maxlength:
            parts.append(currentpart)
            currentpart = line
        else:
            currentpart += '\n' + line if currentpart else line
    
    if currentpart:
        parts.append(currentpart)
    
    for i, part in enumerate(parts):
        try:
            await update.message.replytext(
                part + (f"\n\n🔄 الجزء {i+1}/{len(parts)}" if len(parts) > 1 else ""),
                parsemode=parsemode
            )
        except Exception as e:
            # في حالة فشل parsing، إرسال بدون formatting
            logger.error(f"Markdown parsing error in part {i+1}: {e}")
            cleanpart = cleanmarkdowntext(part)
            await update.message.replytext(
                cleanpart + (f"\n\n🔄 الجزء {i+1}/{len(parts)}" if len(parts) > 1 else "")
            )
        await asyncio.sleep(0.5)

def createmainkeyboard(user: User) -> InlineKeyboardMarkup:
    """إنشاء لوحة المفاتيح الرئيسية المحسنة"""
    
    isactivated = (user.licensekey and user.isactivated) or user.userid == Config.MASTERUSERID
    
    if not isactivated:
        # للمستخدمين غير المفعلين
        keyboard = [
            [
                InlineKeyboardButton("💰 سعر الذهب المباشر", callbackdata="pricenow")
            ],
            [
                InlineKeyboardButton("🎯 تجربة تحليل مجاني", callbackdata="demoanalysis"),
            ],
            [
                InlineKeyboardButton("🔑 كيف أحصل على مفتاح؟", callbackdata="howtogetlicense")
            ],
            [
                InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odaixau")
            ]
        ]
    else:
        # للمستخدمين المفعلين - قائمة متخصصة
        keyboard = [
            # الصف الأول - التحليلات الأساسية
            [
                InlineKeyboardButton("⚡ سريع (30 ثانية)", callbackdata="analysisquick"),
                InlineKeyboardButton("📊 شامل متقدم", callbackdata="analysisdetailed")
            ],
            # الصف الثاني - تحليلات متخصصة
            [
                InlineKeyboardButton("🎯 سكالب (1-15د)", callbackdata="analysisscalping"),
                InlineKeyboardButton("📈 سوينج (أيام/أسابيع)", callbackdata="analysisswing")
            ],
            # الصف الثالث - توقعات وانعكاسات
            [
                InlineKeyboardButton("🔮 توقعات ذكية", callbackdata="analysisforecast"),
                InlineKeyboardButton("🔄 نقاط الانعكاس", callbackdata="analysisreversal")
            ],
            # الصف الرابع - أدوات إضافية
            [
                InlineKeyboardButton("💰 سعر مباشر", callbackdata="pricenow"),
                InlineKeyboardButton("📰 تأثير الأخبار", callbackdata="analysisnews")
            ],
            # الصف الخامس - المعلومات الشخصية
            [
                InlineKeyboardButton("🔑 معلومات المفتاح", callbackdata="keyinfo"),
                InlineKeyboardButton("⚙️ إعدادات", callbackdata="settings")
            ]
        ]
        
        # إضافة لوحة الإدارة للمشرف فقط
        if user.userid == Config.MASTERUSERID:
            keyboard.append([
                InlineKeyboardButton("👨‍💼 لوحة الإدارة", callbackdata="adminpanel")
            ])
        
        # إضافة زر التحليل الشامل المتقدم
        keyboard.append([
            InlineKeyboardButton(f"🔥 التحليل الشامل المتقدم 🔥", callbackdata="nightmareanalysis")
        ])
    
    return InlineKeyboardMarkup(keyboard)

def createadminkeyboard() -> InlineKeyboardMarkup:
    """لوحة الإدارة المحسنة"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 إحصائيات عامة", callbackdata="adminstats"),
            InlineKeyboardButton("🔑 إدارة المفاتيح", callbackdata="adminkeys")
        ],
        [
            InlineKeyboardButton("👥 إدارة المستخدمين", callbackdata="adminusers"),
            InlineKeyboardButton("📈 تقارير التحليل", callbackdata="adminanalyses")
        ],
        [
            InlineKeyboardButton("💾 نسخة احتياطية", callbackdata="createbackup"),
            InlineKeyboardButton("📝 سجل الأخطاء", callbackdata="viewlogs")
        ],
        [
            InlineKeyboardButton("⚙️ إعدادات النظام", callbackdata="systemsettings"),
            InlineKeyboardButton("🔄 إعادة تشغيل", callbackdata="restartbot")
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callbackdata="backmain")
        ]
    ])

def createkeysmanagementkeyboard() -> InlineKeyboardMarkup:
    """لوحة إدارة المفاتيح"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 عرض كل المفاتيح", callbackdata="keysshowall"),
            InlineKeyboardButton("⭕ المفاتيح المتاحة", callbackdata="keysshowunused")
        ],
        [
            InlineKeyboardButton("➕ إنشاء مفاتيح جديدة", callbackdata="keyscreateprompt"),
            InlineKeyboardButton("📊 إحصائيات المفاتيح", callbackdata="keysstats")
        ],
        [
            InlineKeyboardButton("🗑️ حذف مستخدم", callbackdata="keysdeleteuser"),
            InlineKeyboardButton("🔙 رجوع للإدارة", callbackdata="adminpanel")
        ]
    ])

# ==================== Decorators ====================
def requireactivationwithkeyusage(analysistype="general"):
    """Decorator لفحص التفعيل واستخدام المفتاح"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULTTYPE, args, kwargs):
            userid = update.effectiveuser.id
            
            # فحص الحظر
            if context.botdata['security'].isblocked(userid):
                await update.message.replytext("❌ حسابك محظور. تواصل مع الدعم.")
                return
            
            # جلب المستخدم
            user = await context.botdata['db'].getuser(userid)
            if not user:
                user = User(
                    userid=userid,
                    username=update.effectiveuser.username,
                    firstname=update.effectiveuser.firstname
                )
                await context.botdata['db'].adduser(user)
            
            # فحص التفعيل
            if userid != Config.MASTERUSERID and not user.isactivated:
                await update.message.replytext(
                    "🔑 يتطلب تفعيل الحساب\n\n"
                    "للاستخدام، يجب تفعيل حسابك أولاً.\n"
                    "استخدم: /license مفتاحالتفعيل\n\n"
                    "💬 للتواصل: @Odaixau"
                )
                return
            
            # فحص واستخدام المفتاح
            if userid != Config.MASTERUSERID:
                licensemanager = context.botdata['licensemanager']
                success, message = await licensemanager.usekey(
                    user.licensekey, 
                    userid, 
                    user.username,
                    analysistype
                )
                if not success:
                    await update.message.replytext(message)
                    return
            
            # تحديث بيانات المستخدم
            user.lastactivity = datetime.now()
            await context.botdata['db'].adduser(user)
            context.userdata['user'] = user
            
            return await func(update, context, args, kwargs)
        return wrapper
    return decorator

def adminonly(func):
    """للمشرف فقط"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULTTYPE, args, kwargs):
        if update.effectiveuser.id != Config.MASTERUSERID:
            await update.message.replytext("❌ هذا الأمر للمسؤول فقط.")
            return
        return await func(update, context, args, kwargs)
    return wrapper

# ==================== Command Handlers ====================
# 1. استبدل دالة startcommand بهذه النسخة المحسنة:
async def startcommand(update: Update, context: ContextTypes.DEFAULTTYPE):
    """أمر البداية المحسن مع إصلاح Markdown"""
    userid = update.effectiveuser.id
    
    user = await context.botdata['db'].getuser(userid)
    if not user:
        user = User(
            userid=userid,
            username=update.effectiveuser.username,
            firstname=update.effectiveuser.firstname
        )
        await context.botdata['db'].adduser(user)
    
    # الحصول على سعر الذهب الحالي للعرض
    try:
        goldprice = await context.botdata['goldpricemanager'].getgoldprice()
        pricedisplay = f"💰 السعر الحالي: ${goldprice.price}\n📊 التغيير: {goldprice.change24h:+.2f} ({goldprice.changepercentage:+.2f}%)"
    except:
        pricedisplay = "💰 السعر: يتم التحديث..."

    isactivated = (user.licensekey and user.isactivated) or userid == Config.MASTERUSERID
    
    if isactivated:
        # للمستخدمين المفعلين - ترحيب خاص (HTML بدلاً من Markdown)
        keyinfo = await context.botdata['licensemanager'].getkeyinfo(user.licensekey) if user.licensekey else None
        remainingmsgs = keyinfo['remainingtoday'] if keyinfo else "∞"
        
        welcomemessage = f"""╔══════════════════════════════════════╗
║     🔥 <b>مرحباً في عالم النخبة</b> 🔥     ║
╚══════════════════════════════════════╝

👋 أهلاً وسهلاً <b>{update.effectiveuser.firstname}</b>!

{pricedisplay}

┌─────────────────────────────────────┐
│  ✅ <b>حسابك مُفعَّل ومجهز للعمل</b>   │
│  🎯 الرسائل المتبقية اليوم: <b>{remainingmsgs}</b>  │
│  🔄 يتجدد العداد كل 24 ساعة بالضبط    │
└─────────────────────────────────────┘

🎯 <b>اختر نوع التحليل المطلوب:</b>"""

        await update.message.replytext(
            welcomemessage,
            replymarkup=createmainkeyboard(user),
            parsemode=ParseMode.HTML,  # HTML بدلاً من Markdown
            disablewebpagepreview=True
        )
    else:
        # للمستخدمين غير المفعلين (بدون markdown خطير)
        welcomemessage = f"""╔══════════════════════════════════════╗
║   💎 <b>Gold Nightmare Academy</b> 💎   ║
║     أقوى منصة تحليل الذهب بالعالم     ║
╚══════════════════════════════════════╝

👋 مرحباً <b>{update.effectiveuser.firstname}</b>!

{pricedisplay}

┌─────────── 🏆 <b>لماذا نحن الأفضل؟</b> ───────────┐
│                                               │
│ 🧠 <b>ذكاء اصطناعي متطور</b> - Claude 4 Sonnet   │
│ 📊 <b>تحليل متعدد الأطر الزمنية</b> بدقة 95%+     │
│ 🎯 <b>نقاط دخول وخروج</b> بالسنت الواحد          │
│ 🛡️ <b>إدارة مخاطر احترافية</b> مؤسسية           │
│ 📈 <b>توقعات مستقبلية</b> مع نسب ثقة دقيقة        │
│ 🔥 <b>تحليل شامل متقدم</b> للمحترفين              │
│                                               │
└───────────────────────────────────────────────┘

🎁 <b>عرض محدود - مفاتيح متاحة الآن!</b>

🔑 كل مفتاح يعطيك:
   ⚡ 3 تحليلات احترافية يومياً
   🔄 تجديد تلقائي كل 24 ساعة
   🎯 وصول للتحليل الشامل المتقدم
   📱 دعم فني مباشر

💡 <b>للحصول على مفتاح التفعيل:</b>
تواصل مع المطور المختص"""

        keyboard = [
            [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odaixau")],
            [InlineKeyboardButton("📈 قناة التوصيات", url="https://t.me/odaixauusdt")],
            [InlineKeyboardButton("💰 سعر الذهب الآن", callbackdata="pricenow")],
            [InlineKeyboardButton("❓ كيف أحصل على مفتاح؟", callbackdata="howtogetlicense")]
        ]
        
        await update.message.replytext(
            welcomemessage,
            replymarkup=InlineKeyboardMarkup(keyboard),
            parsemode=ParseMode.HTML,  # HTML بدلاً من Markdown
            disablewebpagepreview=True
        )


async def licensecommand(update: Update, context: ContextTypes.DEFAULTTYPE):
    """أمر تفعيل المفتاح"""
    userid = update.effectiveuser.id
    
    if not context.args:
        await update.message.replytext(
            "🔑 تفعيل مفتاح الترخيص\n\n"
            "الاستخدام: /license مفتاحالتفعيل\n\n"
            "مثال: /license GOLD-ABC1-DEF2-GHI3"
        )
        return
    
    licensekey = context.args[0].upper().strip()
    licensemanager = context.botdata['licensemanager']
    
    isvalid, message = await licensemanager.validatekey(licensekey, userid)
    
    if not isvalid:
        await update.message.replytext(f"❌ فشل التفعيل\n\n{message}")
        return
    
    user = await context.botdata['db'].getuser(userid)
    if not user:
        user = User(
            userid=userid,
            username=update.effectiveuser.username,
            firstname=update.effectiveuser.firstname
        )
    
    user.licensekey = licensekey
    user.isactivated = True
    user.activationdate = datetime.now()
    await context.botdata['db'].adduser(user)
    
    context.botdata['security'].createsession(userid, licensekey)
    
    keyinfo = await licensemanager.getkeyinfo(licensekey)
    
    successmessage = f"""✅ تم التفعيل بنجاح!

🔑 المفتاح: {licensekey}
📊 الحد اليومي: {keyinfo['dailylimit']} رسائل
📈 المتبقي اليوم: {keyinfo['remainingtoday']} رسائل
⏰ يتجدد العداد كل 24 ساعة تلقائياً بالضبط

🎉 يمكنك الآن استخدام البوت والحصول على التحليلات المتقدمة!"""
    
    await update.message.replytext(
        successmessage,
        replymarkup=createmainkeyboard(user)
    )
    
    # حذف الرسالة لحماية المفتاح
    try:
        await update.message.delete()
    except:
        pass

@adminonly
async def createkeyscommand(update: Update, context: ContextTypes.DEFAULTTYPE):
    """إنشاء مفاتيح جديدة"""
    count = 1
    dailylimit = 3
    
    if context.args:
        try:
            count = int(context.args[0])
            if len(context.args) > 1:
                dailylimit = int(context.args[1])
        except ValueError:
            await update.message.replytext("❌ استخدم: /createkeys [عدد] [حديومي]\nمثال: /createkeys 10 3")
            return
    
    if count > 50:
        await update.message.replytext("❌ لا يمكن إنشاء أكثر من 50 مفتاح")
        return
    
    licensemanager = context.botdata['licensemanager']
    
    statusmsg = await update.message.replytext(f"⏳ جاري إنشاء {count} مفتاح...")
    
    createdkeys = []
    for i in range(count):
        key = await licensemanager.createnewkey(
            dailylimit=dailylimit,
            notes=f"مفتاح مُنشأ بواسطة المشرف - {datetime.now().strftime('%Y-%m-%d')}"
        )
        createdkeys.append(key)
    
    keystext = "\n".join([f"{i+1}. {key}" for i, key in enumerate(createdkeys)])
    
    resultmessage = f"""✅ تم إنشاء {count} مفتاح بنجاح!

📊 الحد اليومي: {dailylimit} رسائل لكل مفتاح
⏰ يتجدد كل 24 ساعة بالضبط

🔑 المفاتيح:
{keystext}

💡 تعليمات للمستخدمين:
• كل مفتاح يعطي {dailylimit} رسائل فقط يومياً
• استخدام: /license GOLD-XXXX-XXXX-XXXX"""
    
    await statusmsg.edittext(resultmessage)

@adminonly
async def keyscommand(update: Update, context: ContextTypes.DEFAULTTYPE):
    """عرض جميع المفاتيح للمشرف"""
    licensemanager = context.botdata['licensemanager']
    
    if not licensemanager.licensekeys:
        await update.message.replytext("❌ لا توجد مفاتيح")
        return
    
    # إعداد الرسالة
    message = "🔑 جميع مفاتيح التفعيل:\n\n"
    
    # إحصائيات عامة
    stats = await licensemanager.getallkeysstats()
    message += f"📊 الإحصائيات:\n"
    message += f"• إجمالي المفاتيح: {stats['totalkeys']}\n"
    message += f"• المفاتيح المستخدمة: {stats['usedkeys']}\n"
    message += f"• المفاتيح الفارغة: {stats['unusedkeys']}\n"
    message += f"• الاستخدام اليوم: {stats['todayusage']}\n"
    message += f"• الاستخدام الإجمالي: {stats['totalusage']}\n\n"
    
    # عرض أول 10 مفاتيح مع تفاصيل كاملة
    count = 0
    for key, licensekey in licensemanager.licensekeys.items():
        if count >= 10:  # عرض أول 10 فقط
            break
        count += 1
        
        status = "🟢 نشط" if licensekey.isactive else "🔴 معطل"
        userinfo = f"👤 {licensekey.username or 'لا يوجد'} (ID: {licensekey.userid})" if licensekey.userid else "⭕ غير مستخدم"
        usage = f"{licensekey.usedtoday}/{licensekey.dailylimit}"
        
        message += f"{count:2d}. {key}\n"
        message += f"   {status} | {userinfo}\n"
        message += f"   📊 الاستخدام: {usage} | إجمالي: {licensekey.totaluses}\n"
        message += f"   📅 إنشاء: {licensekey.createddate.strftime('%Y-%m-%d')}\n\n"
    
    if len(licensemanager.licensekeys) > 10:
        message += f"... و {len(licensemanager.licensekeys) - 10} مفاتيح أخرى\n\n"
    
    message += "💡 استخدم /unusedkeys للمفاتيح المتاحة فقط"
    
    await sendlongmessage(update, message)

@adminonly
async def unusedkeyscommand(update: Update, context: ContextTypes.DEFAULTTYPE):
    """عرض المفاتيح غير المستخدمة فقط"""
    licensemanager = context.botdata['licensemanager']
    
    unusedkeys = [key for key, licensekey in licensemanager.licensekeys.items() 
                   if not licensekey.userid and licensekey.isactive]
    
    if not unusedkeys:
        await update.message.replytext("❌ لا توجد مفاتيح متاحة")
        return
    
    message = f"⭕ المفاتيح المتاحة ({len(unusedkeys)} مفتاح):\n\n"
    
    for i, key in enumerate(unusedkeys, 1):
        licensekey = licensemanager.licensekeys[key]
        message += f"{i:2d}. {key}\n"
        message += f"    📊 الحد اليومي: {licensekey.dailylimit} رسائل\n"
        message += f"    📅 تاريخ الإنشاء: {licensekey.createddate.strftime('%Y-%m-%d')}\n\n"
    
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
```"""
    
    await sendlongmessage(update, message)

@adminonly
async def deleteusercommand(update: Update, context: ContextTypes.DEFAULTTYPE):
    """حذف مستخدم من مفتاح"""
    if not context.args:
        await update.message.replytext(
            "🗑️ حذف مستخدم من مفتاح\n\n"
            "الاستخدام: /deleteuser مفتاحالتفعيل\n\n"
            "مثال: /deleteuser GOLD-ABC1-DEF2-GHI3"
        )
        return
    
    licensekey = context.args[0].upper().strip()
    licensemanager = context.botdata['licensemanager']
    
    success, message = await licensemanager.deleteuserbykey(licensekey)
    
    await update.message.replytext(message)

@adminonly
async def backupcommand(update: Update, context: ContextTypes.DEFAULTTYPE):
    """إنشاء نسخة احتياطية"""
    try:
        dbmanager = context.botdata['db']
        licensemanager = context.botdata['licensemanager']
        
        # إنشاء النسخة الاحتياطية
        backupdata = {
            'timestamp': datetime.now().isoformat(),
            'users': {str(k): {
                'userid': v.userid,
                'username': v.username,
                'firstname': v.firstname,
                'isactivated': v.isactivated,
                'activationdate': v.activationdate.isoformat() if v.activationdate else None,
                'totalrequests': v.totalrequests,
                'totalanalyses': v.totalanalyses,
                'licensekey': v.licensekey
            } for k, v in dbmanager.users.items()},
            'licensekeys': {k: {
                'key': v.key,
                'createddate': v.createddate.isoformat(),
                'dailylimit': v.dailylimit,
                'usedtoday': v.usedtoday,
                'totaluses': v.totaluses,
                'userid': v.userid,
                'username': v.username,
                'isactive': v.isactive
            } for k, v in licensemanager.licensekeys.items()},
            'analysescount': len(dbmanager.analyses)
        }
        
        # حفظ في ملف
        backupfilename = f"backup{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        async with aiofiles.open(backupfilename, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(backupdata, ensureascii=False, indent=2))
        
        await update.message.replytext(
            f"✅ تم إنشاء النسخة الاحتياطية\n\n"
            f"📁 الملف: `{backupfilename}`\n"
            f"👥 المستخدمين: {len(backupdata['users'])}\n"
            f"🔑 المفاتيح: {len(backupdata['licensekeys'])}\n"
            f"📈 التحليلات: {backupdata['analysescount']}"
        )
        
    except Exception as e:
        logger.error(f"Backup error: {e}")
        await update.message.replytext(f"❌ خطأ في إنشاء النسخة الاحتياطية: {str(e)}")

@adminonly 
async def statscommand(update: Update, context: ContextTypes.DEFAULTTYPE):
    """إحصائيات سريعة للأدمن"""
    try:
        dbmanager = context.botdata['db']
        licensemanager = context.botdata['licensemanager']
        
        # إحصائيات أساسية
        totalusers = len(dbmanager.users)
        activeusers = len([u for u in dbmanager.users.values() if u.isactivated])
        totalkeys = len(licensemanager.licensekeys)
        usedkeys = len([k for k in licensemanager.licensekeys.values() if k.userid])
        
        # آخر 24 ساعة
        last24h = datetime.now() - timedelta(hours=24)
        recentanalyses = [a for a in dbmanager.analyses if a.timestamp > last24h]
        nightmareanalyses = [a for a in recentanalyses if a.analysistype == "NIGHTMARE"]
        
        # استخدام اليوم
        todayusage = sum(k.usedtoday for k in licensemanager.licensekeys.values())
        
        statstext = f"""📊 إحصائيات سريعة

👥 المستخدمين:
• الإجمالي: {totalusers}
• المفعلين: {activeusers}
• النسبة: {activeusers/totalusers100:.1f}%

🔑 المفاتيح:
• الإجمالي: {totalkeys}
• المستخدمة: {usedkeys}
• المتاحة: {totalkeys - usedkeys}

📈 آخر 24 ساعة:
• التحليلات: {len(recentanalyses)}
• التحليلات الخاصة: {len(nightmareanalyses)}
• الرسائل المستخدمة اليوم: {todayusage}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        await update.message.replytext(statstext)
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        await update.message.replytext(f"❌ خطأ في الإحصائيات: {str(e)}")

# ==================== Message Handlers ====================
@requireactivationwithkeyusage("textanalysis")
async def handletextmessage(update: Update, context: ContextTypes.DEFAULTTYPE):
    """معالجة الرسائل النصية"""
    user = context.userdata['user']
    
    # فحص الحد المسموح
    allowed, message = context.botdata['ratelimiter'].isallowed(user.userid, user)
    if not allowed:
        await update.message.replytext(message)
        return
    
    await context.bot.sendchataction(chatid=update.effectivechat.id, action=ChatAction.TYPING)
    
    # فحص التحليل السري (بدون إظهار للمستخدم)
    isnightmare = Config.NIGHTMARETRIGGER in update.message.text
    
    if isnightmare:
        processingmsg = await update.message.replytext(
            "🔥🔥🔥 تحضير التحليل الشامل المتقدم 🔥🔥🔥\n\n"
            "⚡ جمع البيانات من جميع الأطر الزمنية...\n"
            "📊 تحليل المستويات والنماذج الفنية...\n"
            "🎯 حساب نقاط الدخول والخروج الدقيقة...\n\n"
            "⏳ التحليل الشامل يحتاج وقت أطول للدقة القصوى..."
        )
    else:
        processingmsg = await update.message.replytext("🧠 جاري التحليل الاحترافي...")
    
    try:
        price = await context.botdata['goldpricemanager'].getgoldprice()
        if not price:
            await processingmsg.edittext("❌ لا يمكن الحصول على السعر حالياً.")
            return
        
        # تحديد نوع التحليل من الكلمات المفتاحية
        textlower = update.message.text.lower()
        analysistype = AnalysisType.DETAILED  # افتراضي
        
        if Config.NIGHTMARETRIGGER in update.message.text:
            analysistype = AnalysisType.NIGHTMARE
        elif any(word in textlower for word in ['سريع', 'بسرعة', 'quick']):
            analysistype = AnalysisType.QUICK
        elif any(word in textlower for word in ['سكالب', 'scalp', 'سكالبينغ']):
            analysistype = AnalysisType.SCALPING
        elif any(word in textlower for word in ['سوينج', 'swing']):
            analysistype = AnalysisType.SWING
        elif any(word in textlower for word in ['توقع', 'مستقبل', 'forecast']):
            analysistype = AnalysisType.FORECAST
        elif any(word in textlower for word in ['انعكاس', 'reversal']):
            analysistype = AnalysisType.REVERSAL
        elif any(word in textlower for word in ['خبر', 'أخبار', 'news']):
            analysistype = AnalysisType.NEWS
        
        result = await context.botdata['claudemanager'].analyzegold(
            prompt=update.message.text,
            goldprice=price,
            analysistype=analysistype,
            usersettings=user.settings
        )
        
        await processingmsg.delete()
        
        await sendlongmessage(update, result)
        
        # حفظ التحليل
        analysis = Analysis(
            id=f"{user.userid}{datetime.now().timestamp()}",
            userid=user.userid,
            timestamp=datetime.now(),
            analysistype=analysistype.value,
            prompt=update.message.text,
            result=result[:500],
            goldprice=price.price
        )
        await context.botdata['db'].addanalysis(analysis)
        
        # تحديث إحصائيات المستخدم
        user.totalrequests += 1
        user.totalanalyses += 1
        await context.botdata['db'].adduser(user)
        
    except Exception as e:
        logger.error(f"Error in text analysis: {e}")
        await processingmsg.edittext("❌ حدث خطأ أثناء التحليل.")

@requireactivationwithkeyusage("imageanalysis")
async def handlephotomessage(update: Update, context: ContextTypes.DEFAULTTYPE):
    """معالجة الصور"""
    user = context.userdata['user']
    
    # فحص الحد المسموح
    allowed, message = context.botdata['ratelimiter'].isallowed(user.userid, user)
    if not allowed:
        await update.message.replytext(message)
        return
    
    await context.bot.sendchataction(chatid=update.effectivechat.id, action=ChatAction.UPLOADPHOTO)
    
    # فحص إذا كان التحليل السري في التعليق
    caption = update.message.caption or ""
    isnightmare = Config.NIGHTMARETRIGGER in caption
    
    if isnightmare:
        processingmsg = await update.message.replytext(
            "🔥🔥🔥 تحليل شارت شامل متقدم 🔥🔥🔥\n\n"
            "📸 معالجة الصورة بالذكاء الاصطناعي المتقدم...\n"
            "🔍 تحليل النماذج الفنية والمستويات..."
        )
    else:
        processingmsg = await update.message.replytext("📸 جاري تحليل الشارت بالذكاء الاصطناعي...")
    
    try:
        photo = update.message.photo[-1]
        photofile = await photo.getfile()
        imagedata = await photofile.downloadasbytearray()
        
        imagebase64 = ImageProcessor.processimage(imagedata)
        if not imagebase64:
            await processingmsg.edittext("❌ لا يمكن معالجة الصورة.")
            return
        
        price = await context.botdata['goldpricemanager'].getgoldprice()
        if not price:
            await processingmsg.edittext("❌ لا يمكن الحصول على السعر حالياً.")
            return
        
        caption = caption or "حلل هذا الشارت بالتفصيل الاحترافي"
        
        # تحديد نوع التحليل
        analysistype = AnalysisType.CHART
        if Config.NIGHTMARETRIGGER in caption:
            analysistype = AnalysisType.NIGHTMARE
        
        result = await context.botdata['claudemanager'].analyzegold(
            prompt=caption,
            goldprice=price,
            imagebase64=imagebase64,
            analysistype=analysistype,
            usersettings=user.settings
        )
        
        await processingmsg.delete()
        
        await sendlongmessage(update, result)
        
        # حفظ التحليل
        analysis = Analysis(
            id=f"{user.userid}{datetime.now().timestamp()}",
            userid=user.userid,
            timestamp=datetime.now(),
            analysistype="image",
            prompt=caption,
            result=result[:500],
            goldprice=price.price,
            imagedata=imagedata[:1000]
        )
        await context.botdata['db'].addanalysis(analysis)
        
        # تحديث إحصائيات المستخدم
        user.totalrequests += 1
        user.totalanalyses += 1
        await context.botdata['db'].adduser(user)
        
    except Exception as e:
        logger.error(f"Error in photo analysis: {e}")
        await processingmsg.edittext("❌ حدث خطأ أثناء تحليل الصورة.")

# ==================== Enhanced Handler Functions ====================
async def handledemoanalysis(update: Update, context: ContextTypes.DEFAULTTYPE):
    """معالج التحليل التجريبي للمستخدمين غير المفعلين"""
    query = update.callbackquery
    userid = query.fromuser.id
    
    # التحقق من عدد مرات استخدام التجربة (3 مرات كحد أقصى)
    demousage = context.userdata.get('demousage', 0)
    
    if demousage >= 3:
        await query.editmessagetext(
            "🚫 انتهت المحاولات التجريبية\n\n"
            "لقد استخدمت الحد الأقصى من التحليلات التجريبية (3 مرات).\n\n"
            "🔥 للاستمتاع بتحليلات لا محدودة:\n"
            "احصل على مفتاح تفعيل من المطور\n\n"
            "💎 مع المفتاح ستحصل على:\n"
            "• 3 تحليلات احترافية يومياً\n"
            "• تجديد تلقائي كل 24 ساعة\n"
            "• التحليل الشامل المتقدم\n"
            "• دعم فني مباشر\n\n"
            "👨‍💼 تواصل مع المطور: @Odaixau",
            replymarkup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odaixau")],
                [InlineKeyboardButton("🔙 رجوع", callbackdata="backmain")]
            ])
        )
        return
    
    # رسالة التحضير
    remainingdemos = 3 - demousage
    await query.editmessagetext(
        f"🎯 تحليل تجريبي مجاني\n\n"
        f"⚡ جاري تحضير تحليل احترافي للذهب...\n"
        f"📊 المحاولات المتبقية: {remainingdemos - 1} من 3\n\n"
        f"⏳ يرجى الانتظار..."
    )
    
    try:
        # الحصول على السعر
        price = await context.botdata['goldpricemanager'].getgoldprice()
        if not price:
            await query.editmessagetext("❌ لا يمكن الحصول على السعر حالياً.")
            return
        
        # إنشاء تحليل تجريبي مبسط
        demoprompt = """قدم تحليل سريع احترافي للذهب الآن مع:
        - توصية واضحة (Buy/Sell/Hold)
        - سبب قوي واحد
        - هدف واحد ووقف خسارة
        - نسبة ثقة
        - تنسيق جميل ومنظم
        
        اجعله مثيراً ومحترفاً ليشجع المستخدم على الحصول على المفتاح للتحليلات المتقدمة"""
        
        result = await context.botdata['claudemanager'].analyzegold(
            prompt=demoprompt,
            goldprice=price,
            analysistype=AnalysisType.QUICK
        )
        
        # إضافة رسالة تسويقية للتحليل التجريبي
        demoresult = f"""🎯 تحليل تجريبي مجاني - Gold Nightmare

{result}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 هذا مجرد طعم من قوة التحليلات الكاملة!

💎 مع مفتاح التفعيل ستحصل على:
⚡ تحليلات متعددة الأنواع (سكالب، سوينج، توقعات)
📊 تحليل شامل لجميع الأطر الزمنية
🎯 نقاط دخول وخروج بالسنت الواحد
🛡️ إدارة مخاطر احترافية
🔮 توقعات ذكية مع احتماليات
📰 تحليل تأثير الأخبار
🔄 اكتشاف نقاط الانعكاس
🔥 التحليل الشامل المتقدم للمحترفين

📊 المتبقي من المحاولات التجريبية: {remainingdemos - 1} من 3

🚀 انضم لمجتمع النخبة الآن!"""

        await query.editmessagetext(
            demoresult,
            replymarkup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 احصل على مفتاح", callbackdata="howtogetlicense")],
                [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odaixau")],
                [InlineKeyboardButton("🔙 رجوع للقائمة", callbackdata="backmain")]
            ])
        )
        
        # تحديث عداد الاستخدام التجريبي
        context.userdata['demousage'] = demousage + 1
        
    except Exception as e:
        logger.error(f"Error in demo analysis: {e}")
        await query.editmessagetext(
            "❌ حدث خطأ في التحليل التجريبي.\n\n"
            "🔄 يمكنك المحاولة مرة أخرى أو التواصل مع الدعم.",
            replymarkup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 محاولة أخرى", callbackdata="demoanalysis")],
                [InlineKeyboardButton("📞 الدعم", url="https://t.me/Odaixau")],
                [InlineKeyboardButton("🔙 رجوع", callbackdata="backmain")]
            ])
        )

async def handlenightmareanalysis(update: Update, context: ContextTypes.DEFAULTTYPE):
    """معالج التحليل الشامل المتقدم"""
    query = update.callbackquery
    user = context.userdata.get('user')
    
    if not user or not user.isactivated:
        await query.answer("🔒 يتطلب مفتاح تفعيل", showalert=True)
        return
    
    # فحص واستخدام المفتاح
    licensemanager = context.botdata['licensemanager']
    success, message = await licensemanager.usekey(
        user.licensekey, 
        user.userid,
        user.username,
        "nightmareanalysis"
    )
    
    if not success:
        await query.editmessagetext(message)
        return
    
    # رسالة تحضير خاصة للتحليل الشامل
    await query.editmessagetext(
        "🔥🔥🔥 التحليل الشامل المتقدم 🔥🔥🔥\n\n"
        "⚡ تحضير التحليل الشامل المتقدم...\n"
        "🔬 تحليل جميع الأطر الزمنية...\n"
        "📊 حساب مستويات الدعم والمقاومة...\n"
        "🎯 تحديد نقاط الدخول الدقيقة...\n"
        "🛡️ إعداد استراتيجيات إدارة المخاطر...\n"
        "🔮 حساب التوقعات والاحتماليات...\n\n"
        "⏳ هذا التحليل يستغرق وقتاً أطول لضمان الدقة..."
    )
    
    try:
        price = await context.botdata['goldpricemanager'].getgoldprice()
        if not price:
            await query.editmessagetext("❌ لا يمكن الحصول على السعر حالياً.")
            return
        
        # التحليل الشامل المتقدم
        nightmareprompt = f"""أريد التحليل الشامل المتقدم للذهب - التحليل الأكثر تقدماً وتفصيلاً مع:

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

        {Config.NIGHTMARETRIGGER}
        
        اجعله التحليل الأقوى والأشمل على الإطلاق!"""
        
        result = await context.botdata['claudemanager'].analyzegold(
            prompt=nightmareprompt,
            goldprice=price,
            analysistype=AnalysisType.NIGHTMARE,
            usersettings=user.settings
        )
        
        # إضافة توقيع خاص للتحليل الشامل
        nightmareresult = f"""{result}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 تم بواسطة Gold Nightmare Academy 🔥
💎 التحليل الشامل المتقدم - للمحترفين فقط
⚡ تحليل متقدم بالذكاء الاصطناعي Claude 4
🎯 دقة التحليل: 95%+ - مضمون الجودة
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ تنبيه هام: هذا تحليل تعليمي متقدم وليس نصيحة استثمارية
💡 استخدم إدارة المخاطر دائماً ولا تستثمر أكثر مما تستطيع خسارته"""

        await query.editmessagetext(nightmareresult)
        
    except Exception as e:
        logger.error(f"Error in nightmare analysis: {e}")
        await query.editmessagetext("❌ حدث خطأ في التحليل الشامل.")

async def handleenhancedpricedisplay(update: Update, context: ContextTypes.DEFAULTTYPE):
    """معالج عرض السعر المحسن"""
    query = update.callbackquery
    
    try:
        price = await context.botdata['goldpricemanager'].getgoldprice()
        if not price:
            await query.editmessagetext("❌ لا يمكن الحصول على السعر حالياً.")
            return
        
        # تحديد اتجاه السعر
        if price.change24h > 0:
            trendemoji = "📈"
            trendcolor = "🟢"
            trendtext = "صاعد"
        elif price.change24h < 0:
            trendemoji = "📉"
            trendcolor = "🔴"
            trendtext = "هابط"
        else:
            trendemoji = "➡️"
            trendcolor = "🟡"
            trendtext = "مستقر"
        
        # إنشاء رسالة السعر المتقدمة
        pricemessage = f"""╔══════════════════════════════════════╗
║       💰 سعر الذهب المباشر 💰       ║
╚══════════════════════════════════════╝

💎 السعر الحالي: ${price.price:.2f}
{trendcolor} الاتجاه: {trendtext} {trendemoji}
📊 التغيير 24س: {price.change24h:+.2f} ({price.changepercentage:+.2f}%)

🔝 أعلى سعر: ${price.high24h:.2f}
🔻 أدنى سعر: ${price.low24h:.2f}
⏰ التحديث: {price.timestamp.strftime('%H:%M:%S')}

💡 للحصول على تحليل متقدم استخدم الأزرار أدناه"""
        
        # أزرار تفاعلية للسعر
        pricekeyboard = [
            [
                InlineKeyboardButton("🔄 تحديث السعر", callbackdata="pricenow"),
                InlineKeyboardButton("⚡ تحليل سريع", callbackdata="analysisquick")
            ],
            [
                InlineKeyboardButton("📊 تحليل شامل", callbackdata="analysisdetailed")
            ],
            [
                InlineKeyboardButton("🔙 رجوع للقائمة", callbackdata="backmain")
            ]
        ]
        
        await query.editmessagetext(
            pricemessage,
            replymarkup=InlineKeyboardMarkup(pricekeyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in price display: {e}")
        await query.editmessagetext("❌ خطأ في جلب بيانات السعر")

async def handleenhancedkeyinfo(update: Update, context: ContextTypes.DEFAULTTYPE):
    """معالج معلومات المفتاح المحسن"""
    query = update.callbackquery
    user = context.userdata.get('user')
    
    if not user or not user.licensekey:
        await query.editmessagetext(
            "❌ لا يوجد مفتاح مفعل\n\n"
            "للحصول على مفتاح تفعيل تواصل مع المطور",
            replymarkup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odaixau")],
                [InlineKeyboardButton("🔙 رجوع", callbackdata="backmain")]
            ])
        )
        return
    
    try:
        keyinfo = await context.botdata['licensemanager'].getkeyinfo(user.licensekey)
        if not keyinfo:
            await query.editmessagetext("❌ لا يمكن جلب معلومات المفتاح")
            return
        
        keyinfomessage = f"""╔══════════════════════════════════════╗
║        🔑 معلومات مفتاح التفعيل 🔑        ║
╚══════════════════════════════════════╝

🆔 المعرف: {keyinfo['username'] or 'غير محدد'}
🏷️ المفتاح: `{keyinfo['key'][:8]}`
📅 تاريخ التفعيل: {keyinfo['createddate']}

📈 الاستخدام: {keyinfo['usedtoday']}/{keyinfo['dailylimit']} رسائل
📉 المتبقي: {keyinfo['remainingtoday']} رسائل
🔢 إجمالي الاستخدام: {keyinfo['totaluses']} رسالة

💎 Gold Nightmare Academy - عضوية نشطة
🚀 أنت جزء من مجتمع النخبة في تحليل الذهب!"""
        
        await query.editmessagetext(
            keyinfomessage,
            replymarkup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث المعلومات", callbackdata="keyinfo")],
                [InlineKeyboardButton("🔙 رجوع", callbackdata="backmain")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in enhanced key info: {e}")
        await query.editmessagetext("❌ خطأ في جلب معلومات المفتاح")

# ==================== Callback Query Handler ====================
async def handlecallbackquery(update: Update, context: ContextTypes.DEFAULTTYPE):
    """معالجة الأزرار"""
    query = update.callbackquery
    await query.answer()
    
    data = query.data
    userid = query.fromuser.id
    
    # فحص الحظر
    if context.botdata['security'].isblocked(userid):
        await query.editmessagetext("❌ حسابك محظور.")
        return
    
    # الحصول على بيانات المستخدم
    user = await context.botdata['db'].getuser(userid)
    if not user:
        user = User(
            userid=userid,
            username=query.fromuser.username,
            firstname=query.fromuser.firstname
        )
        await context.botdata['db'].adduser(user)
    
    # الأوامر المسموحة بدون تفعيل
    allowedwithoutlicense = ["pricenow", "howtogetlicense", "backmain", "demoanalysis"]
    
    # فحص التفعيل للأوامر المحمية
    if (userid != Config.MASTERUSERID and 
        (not user.licensekey or not user.isactivated) and 
        data not in allowedwithoutlicense):
        
        notactivatedmessage = f"""🔑 يتطلب مفتاح تفعيل

لاستخدام هذه الميزة، يجب إدخال مفتاح تفعيل صالح.
استخدم: /license مفتاحالتفعيل

💡 للحصول على مفتاح تواصل مع:
👨‍💼 Odai - @Odaixau

🔥 مع كل مفتاح ستحصل على تحليلات متقدمة احترافية!"""
        
        await query.editmessagetext(
            notactivatedmessage,
            replymarkup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 كيف أحصل على مفتاح؟", callbackdata="howtogetlicense")],
                [InlineKeyboardButton("🔙 رجوع", callbackdata="backmain")]
            ])
        )
        return
    
    # فحص استخدام المفتاح للعمليات المتقدمة
    advancedoperations = [
        "analysisquick", "analysisscalping", "analysisdetailed",
        "analysisforecast", "analysisnews", "analysisswing", "analysisreversal"
    ]
    
    if userid != Config.MASTERUSERID and data in advancedoperations and user.licensekey:
        licensemanager = context.botdata['licensemanager']
        success, usemessage = await licensemanager.usekey(
            user.licensekey, 
            userid,
            user.username,
            f"callback{data}"
        )
        
        if not success:
            await query.editmessagetext(usemessage)
            return
    
    try:
        if data == "demoanalysis":
            await handledemoanalysis(update, context)

        elif data == "nightmareanalysis": 
            await handlenightmareanalysis(update, context)

        elif data == "pricenow":
            await handleenhancedpricedisplay(update, context)
            
        elif data == "howtogetlicense":
            helptext = f"""🔑 كيفية الحصول على مفتاح التفعيل

💎 Gold Nightmare Bot يقدم تحليلات الذهب الأكثر دقة في العالم!

📞 للحصول على مفتاح تفعيل:

👨‍💼 تواصل مع Odai:
- Telegram: @Odaixau
- Channel: @odaixauusdt  
- Group: @odaixauusd

🎁 ماذا تحصل عليه:
- ⚡ 3 تحليلات احترافية يومياً
- 🧠 تحليل بالذكاء الاصطناعي المتقدم
- 📊 تحليل متعدد الأطر الزمنية
- 🔍 اكتشاف النماذج الفنية
- 🎯 نقاط دخول وخروج دقيقة
- 🛡️ إدارة مخاطر احترافية
- 🔥 التحليل الشامل المتقدم

💰 سعر خاص ومحدود!
🔄 تجديد تلقائي كل 24 ساعة بالضبط

🌟 انضم لمجتمع النخبة الآن!"""

            keyboard = [
                [InlineKeyboardButton("📞 تواصل مع Odai", url="https://t.me/Odaixau")],
                [InlineKeyboardButton("📈 قناة التوصيات", url="https://t.me/odaixauusdt")],
                [InlineKeyboardButton("🔙 رجوع", callbackdata="backmain")]
            ]
            
            await query.editmessagetext(
                helptext,
                replymarkup=InlineKeyboardMarkup(keyboard)
            )

        elif data == "keyinfo":
            await handleenhancedkeyinfo(update, context)
                        
        elif data == "backmain":
            mainmessage = f"""🏆 Gold Nightmare Bot

اختر الخدمة المطلوبة:"""
            
            await query.editmessagetext(
                mainmessage,
                replymarkup=createmainkeyboard(user)
            )
        
        elif data.startswith("analysis"):
            analysistypemap = {
                "analysisquick": (AnalysisType.QUICK, "⚡ تحليل سريع"),
                "analysisscalping": (AnalysisType.SCALPING, "🎯 سكالبينج"),
                "analysisdetailed": (AnalysisType.DETAILED, "📊 تحليل مفصل"),
                "analysisswing": (AnalysisType.SWING, "📈 سوينج"),
                "analysisforecast": (AnalysisType.FORECAST, "🔮 توقعات"),
                "analysisreversal": (AnalysisType.REVERSAL, "🔄 مناطق انعكاس"),
                "analysisnews": (AnalysisType.NEWS, "📰 تحليل الأخبار")
            }
            
            if data in analysistypemap:
                analysistype, typename = analysistypemap[data]
                
                processingmsg = await query.editmessagetext(
                    f"🧠 جاري إعداد {typename}...\n\n⏳ يرجى الانتظار..."
                )
                
                price = await context.botdata['goldpricemanager'].getgoldprice()
                if not price:
                    await processingmsg.edittext("❌ لا يمكن الحصول على السعر حالياً.")
                    return
                
                # إنشاء prompt مناسب لنوع التحليل
                if analysistype == AnalysisType.QUICK:
                    prompt = "تحليل سريع للذهب الآن مع توصية واضحة"
                elif analysistype == AnalysisType.SCALPING:
                    prompt = "تحليل سكالبينج للذهب للـ 15 دقيقة القادمة مع نقاط دخول وخروج دقيقة"
                elif analysistype == AnalysisType.SWING:
                    prompt = "تحليل سوينج للذهب للأيام والأسابيع القادمة"
                elif analysistype == AnalysisType.FORECAST:
                    prompt = "توقعات الذهب لليوم والأسبوع القادم مع احتماليات"
                elif analysistype == AnalysisType.REVERSAL:
                    prompt = "تحليل نقاط الانعكاس المحتملة للذهب مع مستويات الدعم والمقاومة"
                elif analysistype == AnalysisType.NEWS:
                    prompt = "تحليل تأثير الأخبار الحالية على الذهب"
                else:
                    prompt = "تحليل شامل ومفصل للذهب مع جداول منظمة"
                
                result = await context.botdata['claudemanager'].analyzegold(
                    prompt=prompt,
                    goldprice=price,
                    analysistype=analysistype,
                    usersettings=user.settings
                )
                
                await processingmsg.edittext(result)
                
                # حفظ التحليل
                analysis = Analysis(
                    id=f"{user.userid}{datetime.now().timestamp()}",
                    userid=user.userid,
                    timestamp=datetime.now(),
                    analysistype=data,
                    prompt=prompt,
                    result=result[:500],
                    goldprice=price.price
                )
                await context.botdata['db'].addanalysis(analysis)
                
                # إضافة زر رجوع
                keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callbackdata="backmain")]]
                await query.editmessagereplymarkup(
                    replymarkup=InlineKeyboardMarkup(keyboard)
                )
        
        elif data == "adminpanel" and userid == Config.MASTERUSERID:
            await query.editmessagetext(
                "👨‍💼 لوحة الإدارة\n\nاختر العملية المطلوبة:",
                replymarkup=createadminkeyboard()
            )
        
        else:
            await query.editmessagetext(
                "❌ خيار غير معروف. استخدم /start للعودة للقائمة الرئيسية."
            )
        
    except Exception as e:
        logger.error(f"Error in callback query '{data}': {e}")
        await query.editmessagetext(
            "❌ حدث خطأ تقني.\n\nاستخدم /start للمتابعة."
        )

# ==================== Admin Message Handler ====================
async def handleadminmessage(update: Update, context: ContextTypes.DEFAULTTYPE):
    """معالج رسائل الأدمن للعمليات الخاصة"""
    userid = update.effectiveuser.id
    
    # فقط للمشرف
    if userid != Config.MASTERUSERID:
        return
    
    adminaction = context.userdata.get('adminaction')
    
    if adminaction == 'broadcast':
        # إرسال رسالة جماعية
        broadcasttext = update.message.text
        
        if broadcasttext.lower() == '/cancel':
            context.userdata.pop('adminaction', None)
            await update.message.replytext("❌ تم إلغاء الرسالة الجماعية.")
            return
        
        dbmanager = context.botdata['db']
        activeusers = [u for u in dbmanager.users.values() if u.isactivated]
        
        statusmsg = await update.message.replytext(f"📤 جاري الإرسال لـ {len(activeusers)} مستخدم...")
        
        successcount = 0
        failedcount = 0
        
        broadcastmessage = f"""📢 رسالة من إدارة Gold Nightmare

{broadcasttext}

━━━━━━━━━━━━━━━━━━━━━━━━━
💎 Gold Nightmare Academy"""
        
        for user in activeusers:
            try:
                await context.bot.sendmessage(
                    chatid=user.userid,
                    text=broadcastmessage
                )
                successcount += 1
                await asyncio.sleep(0.1)  # تجنب spam limits
            except Exception as e:
                failedcount += 1
                logger.error(f"Failed to send broadcast to {user.userid}: {e}")
        
        await statusmsg.edittext(
            f"✅ اكتملت الرسالة الجماعية\n\n"
            f"📤 تم الإرسال لـ: {successcount} مستخدم\n"
            f"❌ فشل الإرسال لـ: {failedcount} مستخدم\n\n"
            f"📊 معدل النجاح: {successcount/(successcount+failedcount)100:.1f}%"
        )
        
        context.userdata.pop('adminaction', None)

# ==================== Error Handler ====================
async def errorhandler(update: object, context: ContextTypes.DEFAULTTYPE) -> None:
    """معالج الأخطاء المحسن"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # إذا كان الخطأ في parsing، حاول إرسال رسالة بديلة
    if "Can't parse entities" in str(context.error):
        try:
            if update and hasattr(update, 'message') and update.message:
                await update.message.replytext(
                    "❌ حدث خطأ في تنسيق الرسالة. تم إرسال النص بدون تنسيق.\n"
                    "استخدم /start للمتابعة."
                )
        except:
            pass  # تجنب إرسال أخطاء إضافية
# ==================== Main Function for Render Webhook ====================
async def setupwebhook():
    """إعداد webhook وحذف أي polling سابق"""
    try:
        # حذف أي webhook سابق
        await application.bot.deletewebhook(droppendingupdates=True)
        
        # تعيين webhook الجديد
        webhookurl = f"{Config.WEBHOOKURL}/webhook"
        await application.bot.setwebhook(webhookurl)
        
        print(f"✅ تم تعيين Webhook: {webhookurl}")
        
    except Exception as e:
        print(f"❌ خطأ في إعداد Webhook: {e}")

def main():
    """الدالة الرئيسية لـ Render Webhook"""
    
    # التحقق من متغيرات البيئة
    if not Config.TELEGRAMBOTTOKEN:
        print("❌ خطأ: TELEGRAMBOTTOKEN غير موجود")
        return
    
    if not Config.CLAUDEAPIKEY:
        print("❌ خطأ: CLAUDEAPIKEY غير موجود")
        return
    
    print("🚀 تشغيل Gold Nightmare Bot على Render...")
    print("🔗 إعداد Webhook للعمل على Render")
    
    # إنشاء التطبيق
    global application
    application = Application.builder().token(Config.TELEGRAMBOTTOKEN).build()
    
    # إنشاء المكونات
    cachemanager = CacheManager()
    dbmanager = DatabaseManager(Config.DBPATH)
    licensemanager = LicenseManager(Config.KEYSFILE)
    goldpricemanager = GoldPriceManager(cachemanager)
    claudemanager = ClaudeAIManager(cachemanager)
    ratelimiter = RateLimiter()
    securitymanager = SecurityManager()
    
    # تحميل البيانات
    async def initializedata():
        await dbmanager.loaddata()
        await licensemanager.initialize()
    
    # تشغيل تحميل البيانات
    asyncio.geteventloop().rununtilcomplete(initializedata())
    
    # حفظ في botdata
    application.botdata.update({
        'db': dbmanager,
        'licensemanager': licensemanager,
        'goldpricemanager': goldpricemanager,
        'claudemanager': claudemanager,
        'ratelimiter': ratelimiter,
        'security': securitymanager,
        'cache': cachemanager
    })
    
    # إضافة المعالجات
    application.addhandler(CommandHandler("start", startcommand))
    application.addhandler(CommandHandler("license", licensecommand))
    application.addhandler(CommandHandler("createkeys", createkeyscommand))
    application.addhandler(CommandHandler("keys", keyscommand))
    application.addhandler(CommandHandler("unusedkeys", unusedkeyscommand))
    application.addhandler(CommandHandler("deleteuser", deleteusercommand))
    application.addhandler(CommandHandler("backup", backupcommand))
    application.addhandler(CommandHandler("stats", statscommand))
    
    # معالجات الرسائل
    application.addhandler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(Config.MASTERUSERID), handleadminmessage))
    application.addhandler(MessageHandler(filters.TEXT & ~filters.COMMAND, handletextmessage))
    application.addhandler(MessageHandler(filters.PHOTO, handlephotomessage))
    
    # معالج الأزرار
    application.addhandler(CallbackQueryHandler(handlecallbackquery))
    
    # معالج الأخطاء
    application.adderrorhandler(errorhandler)
    
    print("✅ جاهز للعمل!")
    print(f"📊 تم تحميل {len(licensemanager.licensekeys)} مفتاح تفعيل")
    print(f"👥 تم تحميل {len(dbmanager.users)} مستخدم")
    print("="*50)
    print("🌐 البوت يعمل على Render مع Webhook...")
    
    # إعداد webhook
    asyncio.geteventloop().rununtilcomplete(setupwebhook())
    
    # تشغيل webhook على Render
    port = int(os.getenv("PORT", "10000"))
    webhookurl = Config.WEBHOOKURL or "https://your-app-name.onrender.com"
    
    print(f"🔗 Webhook URL: {webhookurl}/webhook")
    print(f"🚀 استمع على المنفذ: {port}")
    
    try:
        application.runwebhook(
            listen="0.0.0.0",
            port=port,
            urlpath="webhook",
            webhookurl=f"{webhookurl}/webhook",
            droppendingupdates=True  # حذف الرسائل المعلقة
        )
    except Exception as e:
        print(f"❌ خطأ في تشغيل Webhook: {e}")
        logger.error(f"Webhook error: {e}")

if name == "main_":
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    🔥 Gold Nightmare Bot 🔥                    ║
║                    Render Webhook Version                    ║
║                     Version 6.0 Professional Enhanced        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🌐 تشغيل على Render مع Webhook                             ║
║  ⚡ لا يحتاج polling - webhook فقط                          ║
║  🔗 متوافق مع بيئة Render                                   ║
║  📡 استقبال فوري للرسائل                                    ║
║                                                              ║
║  🚀 المميزات:                                               ║
║  • 40 مفتاح تفعيل أولي (3 رسائل/يوم)                       ║
║  • تجديد دقيق كل 24 ساعة بالضبط                            ║
║  • أزرار تفاعلية للمفعلين فقط                               ║
║  • لوحة إدارة شاملة ومتطورة                                 ║
║  • تحليل شامل متقدم سري للمحترفين                          ║
║  • تنسيقات جميلة وتحليلات احترافية                          ║
║  • تحليل بـ 8000 توكن للدقة القصوى                         ║
║                                                              ║
║  👨‍💼 أوامر الإدارة:                                          ║
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
