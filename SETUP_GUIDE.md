# دليل إعداد وتشغيل Highrise Music Bot على الاستضافات

## نظرة عامة
هذا الدليل سيساعدك على تشغيل البوت بنجاح على أي استضافة بوت (Bot Hosting).

## الملفات المطلوبة للرفع

### الملفات الأساسية (مطلوبة)
```
main.py                       # ملف التشغيل الرئيسي
config.py                     # الإعدادات
highrise_music_bot.py         # بوت Highrise
streamer.py                   # خدمة البث
continuous_playlist_manager.py # مدير قائمة التشغيل
responses.py                  # الردود
tickets_system.py             # نظام التذاكر
bot_runner.py                 # مشغل البوت
updates_manager.py            # سيرفر التحديثات
requirements.txt              # المكتبات المطلوبة
startup.sh                    # سكربت التشغيل
install.sh                    # سكربت التثبيت
```

### ملفات البيانات (اختيارية - تُنشأ تلقائياً)
```
default_playlist.txt          # قائمة التشغيل الافتراضية
bot_dances.json               # رقصات البوت
owners.json                   # المالكين
```

## طريقة التشغيل

### الخطوة 1: رفع الملفات
ارفع جميع الملفات المطلوبة إلى الاستضافة

### الخطوة 2: تثبيت المتطلبات
```bash
# الطريقة 1: استخدام سكربت التثبيت (مُستحسن)
chmod +x install.sh
./install.sh

# الطريقة 2: تثبيت يدوي
pip3 install -r requirements.txt
```

### الخطوة 3: تعيين المتغيرات البيئية
في لوحة إعدادات الاستضافة (Environment Variables):

```
HIGHRISE_BOT_TOKEN=<رمز البوت من Highrise>
HIGHRISE_ROOM_ID=<معرف الغرفة>
ZENO_PASSWORD=<كلمة مرور Zeno.fm>
```

### الخطوة 4: تشغيل البوت
```bash
# الطريقة 1: استخدام startup.sh
chmod +x startup.sh
./startup.sh

# الطريقة 2: تشغيل مباشر
python3 main.py
```

## المتطلبات النظامية

### البرامج المطلوبة
| البرنامج | الإصدار الأدنى | الوظيفة |
|----------|---------------|---------|
| Python | 3.10+ | تشغيل البوت |
| FFmpeg | أي إصدار | معالجة الصوت |
| yt-dlp | 2024.10+ | تحميل من يوتيوب |

### تثبيت FFmpeg على الاستضافات المختلفة

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

**CentOS/RHEL:**
```bash
sudo yum install -y ffmpeg
# أو
sudo dnf install -y ffmpeg
```

**Alpine (Docker):**
```bash
apk add --no-cache ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### تثبيت yt-dlp

**الطريقة 1: عبر pip (مُستحسن)**
```bash
pip3 install -U "yt-dlp[default]"
```

**الطريقة 2: تحميل مباشر**
```bash
# Linux/macOS
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o yt-dlp
chmod +x yt-dlp

# أو عبر wget
wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp
chmod +x yt-dlp
```

## حل المشاكل الشائعة

### مشكلة: "yt-dlp: command not found"
```bash
# الحل 1: تثبيت عبر pip
pip3 install -U "yt-dlp[default]"

# الحل 2: إضافة إلى PATH
export PATH="$HOME/.local/bin:$PATH"

# الحل 3: تحميل binary مباشرة
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o yt-dlp
chmod +x yt-dlp
```

### مشكلة: "ffmpeg: command not found"
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y ffmpeg

# تحقق من التثبيت
ffmpeg -version
```

### مشكلة: "ModuleNotFoundError: No module named 'highrise'"
```bash
pip3 install -r requirements.txt
```

### مشكلة: "ERROR: Unable to extract JS player URL"
yt-dlp يحتاج تحديث:
```bash
pip3 install -U yt-dlp
```

### مشكلة: "HTTP Error 429: Too Many Requests"
البوت لديه نظام ذكي لتجنب الحظر:
- تأخير عشوائي بين التحميلات (5-15 ثانية)
- حد أقصى 20 تحميل في الساعة
- انتظار تلقائي عند اكتشاف خطأ 429

### مشكلة: البوت لا يظهر في الغرفة
تأكد من:
1. `HIGHRISE_BOT_TOKEN` صحيح
2. `HIGHRISE_ROOM_ID` صحيح
3. البوت مدعو للغرفة في Highrise

## الاستضافات المُختبرة

### ✅ تعمل بشكل ممتاز
- **Replit** - يدعم كل المتطلبات
- **Railway** - يدعم FFmpeg و yt-dlp
- **Render** - يحتاج Dockerfile
- **DigitalOcean App Platform** - يحتاج إعداد
- **VPS (أي توزيعة Linux)** - يعمل مباشرة

### ⚠️ تحتاج إعداد خاص
- **Heroku** - يحتاج buildpack لـ FFmpeg
- **PythonAnywhere** - لا يدعم FFmpeg مباشرة
- **Vercel** - لا يدعم عمليات طويلة

## إعداد Heroku

أضف هذه الـ buildpacks:
```bash
heroku buildpacks:add --index 1 https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
heroku buildpacks:add --index 2 heroku/python
```

## إعداد Docker

```dockerfile
FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Install yt-dlp
RUN pip install --upgrade pip && pip install "yt-dlp[default]"

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy app files
COPY . .

# Create directories
RUN mkdir -p song_cache downloads backups

# Run the bot
CMD ["python3", "main.py"]
```

## هيكل المجلدات

```
bot/
├── main.py                    # ملف التشغيل الرئيسي
├── config.py                  # الإعدادات
├── requirements.txt           # المكتبات
├── startup.sh                 # سكربت التشغيل
├── install.sh                 # سكربت التثبيت
├── highrise_music_bot.py      # بوت Highrise
├── streamer.py                # خدمة البث
├── continuous_playlist_manager.py
├── responses.py
├── tickets_system.py
├── bot_runner.py
├── updates_manager.py
├── default_playlist.txt       # قائمة التشغيل
├── bot_dances.json            # الرقصات
├── song_cache/                # مخزن الأغاني (يُنشأ تلقائياً)
├── downloads/                 # التحميلات (يُنشأ تلقائياً)
└── backups/                   # النسخ الاحتياطية (يُنشأ تلقائياً)
```

## المتغيرات البيئية

| المتغير | مطلوب | الوصف |
|---------|-------|-------|
| HIGHRISE_BOT_TOKEN | ✅ نعم | رمز البوت من Highrise |
| HIGHRISE_ROOM_ID | ✅ نعم | معرف الغرفة |
| ZENO_PASSWORD | ✅ نعم | كلمة مرور Zeno.fm |
| OWNER_USERNAME | ❌ لا | اسم المالك |
| LOG_LEVEL | ❌ لا | مستوى اللوج (INFO, DEBUG, WARNING) |
| UPDATES_PORT | ❌ لا | منفذ سيرفر التحديثات (افتراضي: 8080) |

## التحقق السريع

بعد التثبيت، تحقق من:
```bash
# Python
python3 --version  # يجب أن يكون 3.10+

# FFmpeg
ffmpeg -version

# yt-dlp
yt-dlp --version

# المكتبات
python3 -c "import highrise; import yt_dlp; import flask; print('All OK!')"
```

## الدعم

إذا واجهت مشاكل:
1. تحقق من اللوجز للأخطاء
2. تأكد من تثبيت كل المتطلبات
3. تأكد من صحة المتغيرات البيئية
4. جرب إعادة تشغيل البوت

---
**نصيحة ذهبية**: استخدم `./install.sh` أولاً ثم `./startup.sh` - سيتم التعامل مع كل شيء تلقائياً!
