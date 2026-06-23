# استخدام إصدار Python 3.11 الأكثر استقراراً
FROM python:3.11

# تعيين مجلد العمل داخل الحاوية
WORKDIR /app

# تثبيت التبعيات اللازمة للنظام
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    libpq-dev \
    zbar-tools \
    libssl-dev \
    zlib1g-dev \
    libffi-dev \
    libbz2-dev \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملف المتطلبات إلى الحاوية
COPY requirements.txt .

# تثبيت المتطلبات
RUN python3.11 -m pip install --no-cache-dir --upgrade pip && \
    python3.11 -m pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع إلى الحاوية
COPY . .

# تحديد المنفذ الذي يعمل عليه التطبيق في docker-compose
EXPOSE 8443

# تشغيل التطبيق في وضع التطوير
CMD ["python", "manage.py", "runserver", "0.0.0.0:8443"]
