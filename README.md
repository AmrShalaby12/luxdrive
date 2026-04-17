# Allen Bus Management

الملف ده معمول مخصوص عشان أي طالب أو ديفلوبر يمسك المشروع بسرعة ويفهمه من غير ما يتوه في الملفات. الشرح هنا بالعامية المصرية، بس محافظ على أسماء الملفات والكلاسات والراوتات زي ما هي في الكود.

## فكرة المشروع ببساطة

المشروع ده نظام إدارة نقل ورحلات معمول بـ Django. فكرته إنه يخدم شركة أو جهة بتدير:

- رحلات باصات للجامعات أو العملاء.
- اشتراكات ركاب وطلاب.
- حجوزات مقاعد ورحلات.
- حضور عن طريق QR أو كود جامعي.
- متابعة مكان الباص لايف.
- تأجير سيارات خاصة.
- دفع أونلاين عن طريق Kashier.
- رسائل واتساب عن طريق UltraMsg.
- Telegram bot للتنبيهات وربط المستخدمين.
- شوية مميزات AI زي OpenAI وGemini.

يعني المشروع مش صفحة واحدة، هو أقرب لنظام تشغيل كامل لشركة نقل: أدمن، عملاء، رحلات، عربيات، مدفوعات، إشعارات، وخرائط.

## التكنولوجي المستخدمة

- Backend: Django 5.0.7
- Database: PostgreSQL
- Background jobs: Celery + Redis
- API: Django REST Framework في أجزاء من المشروع
- Frontend: Django Templates + HTML + CSS + JavaScript
- Maps: Leaflet + MapLibre + OSRM/Nominatim/Photon حسب الإعدادات
- Payments: Kashier
- WhatsApp: UltraMsg
- Bot: python-telegram-bot
- AI integrations: OpenAI + Gemini
- Deployment/Dev: Docker و docker compose

## أهم فولدرات المشروع

`Main_Bus_Management/`
: إعدادات مشروع Django الأساسية. هنا هتلاقي `settings.py` و`urls.py` و`wsgi.py`.

`Anaconda_bus_APP/`
: الأبلكيشن الأساسي. هنا معظم الشغل: الموديلات، الفيوز، الراوتات، القوالب، الأدمن، الداشبورد، حجوزات الباصات، تأجير السيارات، الدفع، الخرائط، والواتساب.

`Anaconda_bus_APP/models.py`
: تعريف جداول الداتابيز. زي الطالب، الباص، الرحلة، الحجز، السيارة، حجز السيارة، المدن، أماكن الركوب، وهكذا.

`Anaconda_bus_APP/views.py`
: منطق الباك إند. أي URL بيخش غالبا على function هنا ترجع صفحة HTML أو JSON.

`Anaconda_bus_APP/urls.py`
: خريطة الراوتات الداخلية بتاعة الأبلكيشن. مثلا `/allen/cars/` و`/allen/car/5/`.

`Anaconda_bus_APP/templates/`
: صفحات الفرونت إند اللي Django بيرندرها.

`telegram_bot/`
: جزء خاص بويبهوك وإدارة Telegram bot.

`driver_monitoring/`
: أبلكيشن منفصل ظاهر إنه معمول لمراقبة السائق أو بيانات مرتبطة بالسواقة.

`docker-compose.yml`
: تشغيل المشروع ومعاه PostgreSQL وRedis وCelery.

`requirements.txt`
: باكدجات Python المطلوبة.

## متطلبات التشغيل

أسهل طريقة للتشغيل هي Docker. محتاج:

- Docker Desktop
- Docker Compose
- Git لو هترفع أو تسحب من GitHub

ولو هتشغله من غير Docker محتاج:

- Python 3.11
- PostgreSQL شغال
- Redis شغال لو هتشغل Celery

## تجهيز ملف البيئة

اعمل نسخة من `.env.example` باسم `.env`:

```powershell
Copy-Item .env.example .env
```

أو على Linux/Mac:

```bash
cp .env.example .env
```

أهم متغيرات البيئة:

```env
DJANGO_SECRET_KEY=django-insecure-change-me

POSTGRES_DB=Allen_bus
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=db
POSTGRES_PORT=5432

KASHIER_API_KEY=
KASHIER_SECRET_KEY=
KASHIER_ACCOUNT_KEY=
KASHIER_MODE=live

ULTRAMSG_INSTANCE_ID=
ULTRAMSG_API_TOKEN=

TELEGRAM_BOT_TOKEN=

OPENAI_API_KEY=
GEMINI_API_KEY=
GOOGLE_MAPS_API_KEY=
```

مهم: في التطوير عادي تسيب مفاتيح الدفع والواتساب والـ AI فاضية، بس الصفحات اللي بتحتاج الخدمات دي مش هتشتغل كاملة غير لما تحط مفاتيح صحيحة.

## تشغيل المشروع بـ Docker

من روت المشروع شغل:

```powershell
docker compose up --build
```

لو جهازك بيستخدم الأمر القديم:

```powershell
docker-compose up --build
```

بعد ما السيرفسات تقوم، افتح تيرمنال تاني ونفذ:

```powershell
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py collectstatic --noinput
```

افتح الموقع:

```text
http://localhost:8443/allen/
```

ولو عايز لوحة الأدمن:

```text
http://localhost:8443/allen/admin/
```

## تشغيل المشروع من غير Docker

الطريقة دي مناسبة لو عندك PostgreSQL وRedis شغالين على جهازك.

اعمل virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

ثبت المتطلبات:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install Kashier==1.0.6
```

شغل PostgreSQL محلي وخلي الإعدادات تشير على localhost:

```powershell
$env:POSTGRES_DB="Allen_bus"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="change-me"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
```

نفذ المايجريشن:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

شغل السيرفر:

```powershell
python manage.py runserver 0.0.0.0:8000
```

افتح:

```text
http://127.0.0.1:8000/allen/
```

## أوامر مفيدة للطلبة

تشغيل السيرفر محلي:

```powershell
python manage.py runserver
```

عمل migrations بعد تعديل models:

```powershell
python manage.py makemigrations
python manage.py migrate
```

إنشاء admin:

```powershell
python manage.py createsuperuser
```

فتح Django shell:

```powershell
python manage.py shell
```

تشغيل Celery worker داخل Docker:

```powershell
docker compose up celery_worker
```

تشغيل Celery beat داخل Docker:

```powershell
docker compose up celery_beat
```

## فكرة Django في المشروع ده

أي طلب في Django بيمشي غالبا كده:

1. المستخدم يفتح URL في المتصفح.
2. `Main_Bus_Management/urls.py` يستقبل الطلب.
3. الطلب يتبعت لـ `Anaconda_bus_APP/urls.py`.
4. Django يختار view مناسبة من `Anaconda_bus_APP/views.py`.
5. الـ view تجيب بيانات من database عن طريق models.
6. الـ view ترجع template HTML أو JSON.
7. المتصفح يعرض الصفحة ويشغل JavaScript لو موجود.

مثال سريع:

```text
/allen/cars/
        |
        v
Anaconda_bus_APP/urls.py
        |
        v
views.car_list
        |
        v
Car.objects.all()
        |
        v
templates/car_list.html
```

## أهم الموديلات في الداتابيز

`passenger`
: ده موديل الراكب أو الطالب. فيه الاسم، رقم الموبايل، الجامعة، الكود الجامعي، نوع المستخدم، مدة الاشتراك، عدد الرحلات المستخدمة، QR، صورة الوجه، وبيانات Telegram.

`Category`
: هنا غالبا المقصود بيها الجامعة أو الفئة. بتتربط بالباصات والطلاب والرحلات. فيها أسعار الذهاب والعودة وإعدادات هل الحجز بالفورم متاح ولا لا.

`Bus`
: بيانات الباص: الاسم، السعة، رقم اللوحة، رقم السائق، نوع الباص، الجامعة، صورة الكراسي، صورة الباص، مكانه الحالي، وهل مشاركة الموقع شغالة.

`Seat`
: كراسي الباص. كل كرسي مربوط بباص، وله رقم، وهل محجوز ولا لا.

`Trip`
: الرحلة نفسها. بتربط بين باص، جامعة، وجهة، وقت، تاريخ، وسعر وبيانات تشغيل الرحلة.

`Booking`
: حجز راكب في رحلة باص. ده مهم في نظام الرحلات العادية.

`Car`
: السيارة المتاحة للإيجار. فيها الماركة، الاسم، الموديل، ناقل الحركة، عدد المقاعد، رقم سائق السيارة، صورة، صورة بانوراما، وأسعار لكل شرائح المسافة.

`CarImage`
: صور إضافية للسيارة.

`CarBooking`
: حجز سيارة. فيه العميل، رقم الموبايل، نوع الرحلة، تواريخ وأوقات الذهاب والعودة، نقطة البداية والنهاية، المسافة، السعر، المدفوع، حالة الحجز، ورقم طلب Kashier.

## شرح `/allen/cars/`

ده لينك صفحة قائمة السيارات:

```text
/allen/cars/
```

### الراوت فين؟

في الملف:

```text
Anaconda_bus_APP/urls.py
```

الراوت:

```python
path('allen/cars/', views.car_list, name='car_list')
```

معناه: لما المستخدم يفتح `/allen/cars/` Django يشغل function اسمها `car_list`.

### الباك إند بيعمل إيه؟

الفيو موجود في:

```text
Anaconda_bus_APP/views.py
```

الفكرة:

```python
def car_list(request):
    unique_models = Car.objects.values_list('model', flat=True).distinct()
    category = request.GET.get('category', '')
    cars = Car.objects.filter(model=category) if category else Car.objects.all()
```

الشرح بالمصري:

- بيجيب كل موديلات العربيات المختلفة من جدول `Car`.
- بيشوف هل المستخدم مختار فلتر من الرابط ولا لا.
- لو الرابط فيه `?category=Toyota` مثلا، هيعرض العربيات اللي `model` بتاعها Toyota.
- لو مفيش فلتر، هيعرض كل العربيات.
- بعد كده يبعت البيانات للتمبليت `car_list.html`.

الداتا اللي بتتبعته للفرونت:

```python
context = {
    'unique_models': unique_models,
    'cars': cars,
    'category': category,
    'cars_count': cars.count(),
    'models_count': unique_models.count(),
}
```

يعني الصفحة معاها:

- `cars`: العربيات اللي هتتعرض.
- `unique_models`: الفلاتر الموجودة فوق.
- `category`: الفلتر الحالي.
- `cars_count`: عدد العربيات المعروضة.
- `models_count`: عدد الموديلات المختلفة.

### الفرونت إند بيعمل إيه؟

التمبليت:

```text
Anaconda_bus_APP/templates/car_list.html
```

الصفحة بتعرض:

- Hero section فيه عنوان وعدد العربيات.
- أزرار فلترة حسب الموديل.
- Grid كروت للسيارات.
- كل كارت فيه صورة السيارة، اسمها، موديلها، نوع الفتيس، عدد المقاعد، وزر "اعرض التفاصيل".

لما تدوس على "اعرض التفاصيل"، بيروح على:

```django
{% url 'car_detail' car.id %}
```

يعني مثلا لو العربية ID بتاعها 5:

```text
/allen/car/5/
```

### شكل الداتا اللي الصفحة محتاجاها

كل عربية في القائمة جاية من موديل `Car`، وأهم الحقول:

- `brand`: ماركة العربية.
- `name`: اسم العربية.
- `model`: الموديل أو الفئة.
- `transmission`: Automatic أو Manual.
- `seats`: عدد المقاعد.
- `image`: صورة العربية.
- `is_available`: هل العربية متاحة.
- أسعار شرائح الكيلومترات زي `price_per_km_0_100`.

ملاحظة مهمة للطلبة: `car_list.html` بيحاول يعرض `car.price_per_KM` و`car.fuel_type`، لكن موديل `Car` الحالي في `models.py` مش معرف فيه الحقول دي بالاسم ده. علشان كده ممكن يظهروا فاضيين. التسعير الحقيقي في صفحة التفاصيل معتمد على حقول الشرائح زي `price_per_km_0_100` و`price_per_km_101_200`.

## شرح `/allen/car/5/`

ده لينك تفاصيل عربية معينة:

```text
/allen/car/5/
```

رقم `5` هنا هو `id` بتاع العربية في جدول `Car`. لو مفيش عربية ID بتاعها 5، Django هيرجع 404.

### الراوت فين؟

في:

```text
Anaconda_bus_APP/urls.py
```

الراوت:

```python
path('allen/car/<int:car_id>/', views.car_detail, name='car_detail')
```

معناه إن Django بياخد الرقم اللي في الرابط ويحطه في متغير اسمه `car_id`.

### الباك إند بيعمل إيه؟

الفيو:

```python
def car_detail(request, car_id):
    car = get_object_or_404(Car, id=car_id)
```

يعني:

- هات العربية اللي ID بتاعها `car_id`.
- لو مش موجودة، رجع صفحة 404.

بعدها بيجهز قائمة عربيات للمقارنة:

```python
comparison_cars = [
    _serialize_car_for_client(item)
    for item in Car.objects.filter(Q(is_available=True) | Q(id=car.id)).distinct().order_by('seats', 'brand', 'name')
]
```

الشرح:

- بيجيب العربيات المتاحة.
- وبيضمن إن العربية الحالية موجودة حتى لو مش متاحة.
- بيرتبهم بعدد المقاعد ثم الماركة ثم الاسم.
- بيحول كل عربية لـ JSON ينفع JavaScript يستخدمه.

الدالة `_serialize_car_for_client` بتجهز بيانات زي:

- `id`
- `title`
- `brand`
- `name`
- `model`
- `seats`
- `transmission`
- `image_url`
- `panorama_url`
- `pricing`

وجوا `pricing` بيحط أسعار الشرائح:

- من 0 لـ 100 كم
- من 101 لـ 200 كم
- وهكذا لحد أكبر من 1000 كم
- أسعار ثابتة لـ 12 ساعة و10 ساعات و8 ساعات واستقبال المطار

آخر الفيو بيرندر:

```python
return render(request, 'car_detail.html', {
    'car': car,
    'form': form,
    'car_fuel_type': getattr(car, 'fuel_type', '') or 'غير محدد',
    'car_image_url': car.image.url if car.image else '',
    'car_panorama_url': car.panorama_image.url if car.panorama_image else '',
    'comparison_cars': comparison_cars,
    'map_style_url': settings.SELF_HOSTED_MAP_DARK_STYLE_URL or settings.SELF_HOSTED_MAP_STYLE_URL,
    'map_tile_url': settings.SELF_HOSTED_TILE_URL,
    'map_tile_attribution': settings.SELF_HOSTED_TILE_ATTRIBUTION,
})
```

يعني الفرونت بياخد:

- بيانات العربية الحالية.
- الفورم.
- صورة العربية.
- صورة 360 لو موجودة.
- قائمة عربيات للمقارنة.
- إعدادات الخريطة.

### الفرونت إند في صفحة التفاصيل

التمبليت:

```text
Anaconda_bus_APP/templates/car_detail.html
```

الصفحة دي كبيرة لأنها مش بتعرض تفاصيل بس. هي بتشتغل كأنها صفحة حجز كاملة.

بتستخدم مكتبات:

- Leaflet للخريطة.
- MapLibre لستايل الخريطة.
- Pannellum لعرض صورة 360 لو موجودة.
- JavaScript مخصص لحساب السعر والحجز.

الواجهة فيها:

- خريطة لاختيار نقطة البداية والوصول.
- أزرار لاستخدام موقع المستخدم.
- بحث autocomplete عن الأماكن.
- اختيار نوع الرحلة.
- اختيار تاريخ الذهاب والعودة.
- اختيار وقت الذهاب والعودة.
- اختيار دفع كامل أو دفع 50%.
- حساب السعر لحظيا.
- مقارنة عربيات تانية لنفس المشوار.
- فورم الاسم ورقم الموبايل.
- زر متابعة إلى الدفع.

### أنواع الرحلات في صفحة السيارة

القيم المهمة موجودة في `CarBooking.TRIP_TYPE_CHOICES`:

```text
one_way_go       = ذهاب فقط
one_way_return   = عودة فقط
round_trip       = ذهاب وعودة
day_use          = يوم كامل على حساب المسافة + تكلفة يومية
day_use_12       = استخدام يومي 12 ساعة بسعر ثابت
day_use_10       = استخدام يومي 10 ساعات بسعر ثابت
day_use_8        = استخدام يومي 8 ساعات بسعر ثابت
airport_pickup   = استقبال من المطار بسعر ثابت
```

في الفرونت، المستخدم بيختار النوع من buttons، والقيمة بتتحط في input hidden اسمه `trip_type`.

### حساب المسافة والخريطة

الصفحة بتستخدم 3 endpoints للخرائط:

```text
/allen/api/maps/search/
/allen/api/maps/reverse/
/allen/api/maps/route/
```

وظيفتهم:

- `map_search`: تبحث عن مكان بالاسم وترجع اقتراحات.
- `map_reverse`: تاخد lat/lng وترجع عنوان.
- `map_route`: تاخد نقطة بداية ونقطة نهاية وترجع المسافة والمدة والمسار.

لما المستخدم يحدد من وإلى:

1. JavaScript يحفظ النقطتين.
2. يطلب route من الباك إند.
3. يرسم الخط على الخريطة.
4. يحدث المسافة والمدة في الصفحة.
5. يعيد حساب السعر.

### حساب السعر في الفرونت

الدالة المهمة:

```javascript
calculateEstimateForCar(carData, selectedType, tripDistance)
```

فكرتها:

- لو الرحلة بسعر ثابت زي `day_use_12`، تاخد السعر الثابت من بيانات العربية.
- لو الرحلة حسب المسافة، تشوف المسافة داخلة في أنهي شريحة.
- تضرب المسافة في سعر الكيلومتر للشريحة.
- لو `round_trip` تضرب السعر في 2.
- لو `day_use` تضيف سعر `DAY_USE`.
- في الآخر تضيف 2%:

```javascript
return total * 1.02;
```

دي نقطة مهمة: السعر اللي المستخدم شايفه محسوب في الفرونت، وبعدها بيتبعت للباك إند وقت إنشاء الدفع.

### إنشاء حجز سيارة والدفع

لما المستخدم يضغط "متابعة إلى الدفع"، JavaScript يشغل:

```javascript
submitBooking()
```

الدالة دي بتعمل validation:

- لازم نوع الرحلة يتحدد.
- لازم من وإلى يتحددوا.
- لازم تاريخ الذهاب.
- لو ذهاب وعودة لازم تاريخ العودة.
- لازم الاسم ورقم الموبايل.
- لازم السعر يكون اتحسب.

بعدها تبعت POST JSON للراوت:

```text
/allen/create_car_payment/
```

الراوت ده في `urls.py`:

```python
path('allen/create_car_payment/', views.create_car_payment, name='create_car_payment')
```

والفيو في `views.py`:

```python
def create_car_payment(request):
```

مثال للبيانات اللي بتتبعت:

```json
{
  "customer_name": "Ahmed Ali",
  "phone_number": "01000000000",
  "trip_type": "round_trip",
  "go_date": "2026-05-01",
  "return_date": "2026-05-03",
  "go_time": "10:00",
  "back_time": "18:00",
  "payment_percentage": "50",
  "total_price": 3000,
  "distance_km": 120,
  "from": "Cairo",
  "to": "Alexandria",
  "car_id": 5
}
```

### الباك إند وقت الدفع بيعمل إيه؟

`create_car_payment` بيعمل الخطوات دي:

1. يقرأ JSON من request body.
2. يتأكد إن السعر أكبر من صفر.
3. يتأكد إن نسبة الدفع 50 أو 100.
4. يتأكد إن الاسم ورقم التليفون موجودين.
5. يتأكد إن نوع الرحلة موجود.
6. يتأكد إن من وإلى موجودين.
7. يحول التواريخ والأوقات لقيم Django مفهومة.
8. يجيب العربية من جدول `Car`.
9. يراجع لو العربية محجوزة في نفس الفترة.
10. يعمل `CarBooking` جديد بحالة `pending`.
11. يعمل `merchant_order_id` بالشكل `car-BOOKING_ID`.
12. يحسب المبلغ المدفوع حسب نسبة الدفع.
13. يعمل hash خاص بـ Kashier.
14. يرجع للفرونت `checkout_url`.

بعدها الفرونت يعمل:

```javascript
window.location.href = result.checkout_url;
```

يعني المستخدم يتنقل على صفحة الدفع بتاعة Kashier.

### بعد نجاح الدفع

Kashier بيرجع المستخدم على:

```text
/allen/car/payment/success/
```

الراوت:

```python
path('allen/car/payment/success/', views.car_payment_success, name="car_payment_success")
```

الفيو `car_payment_success` بيعمل:

1. يقرأ `paymentStatus` و`merchantOrderId` من query string.
2. يجيب `CarBooking` من `merchant_order_id`.
3. لو `paymentStatus == SUCCESS`:
   - يغير `status` إلى `confirmed`.
   - يبعت رسالة واتساب للعميل.
   - لو العربية ليها `car_driver_number`، يبعت رسالة للسائق فيها بيانات العميل والمشوار والدفع.
4. يعرض صفحة نجاح.

يعني دورة حجز السيارة كاملة:

```text
/allen/car/5/
    -> المستخدم يحدد المشوار
    -> الفرونت يحسب السعر
    -> POST /allen/create_car_payment/
    -> يتسجل CarBooking pending
    -> المستخدم يروح Kashier
    -> /allen/car/payment/success/
    -> CarBooking يبقى confirmed
    -> رسائل واتساب تتبعت
```

## الفرق بين `/allen/cars/` و`/allen/car/5/`

`/allen/cars/`
: صفحة عرض واختيار. بتجيب كل العربيات وتفلتر حسب الموديل وتخلي المستخدم يدخل على تفاصيل عربية.

`/allen/car/5/`
: صفحة تنفيذ. بتعرض عربية واحدة بالتفصيل، وتحسب المسار والسعر، وتعمل الحجز والدفع.

بالمصري: الأولى كتالوج، والتانية صفحة حجز ودفع.

## شرح مبسط للباك والفرونت والداتا في جزء السيارات

### Backend

- `urls.py` يربط الروابط بالفيوز.
- `car_list` يجيب العربيات من الداتابيز.
- `car_detail` يجيب عربية واحدة ويجهز بيانات المقارنة.
- `map_search`, `map_reverse`, `map_route` يخدموا الخريطة.
- `create_car_payment` ينشئ حجز مبدئي ويرجع لينك Kashier.
- `car_payment_success` يؤكد الحجز بعد الدفع.

### Frontend

- `car_list.html` يعرض كروت العربيات والفلاتر.
- `car_detail.html` يعرض الخريطة والفورم وحساب السعر والمقارنة.
- JavaScript في `car_detail.html` مسؤول عن:
  - البحث عن الأماكن.
  - رسم المسار.
  - حساب المسافة.
  - حساب السعر.
  - حفظ بيانات الاختيار في URL عشان لما تغير العربية البيانات متضيعش.
  - إرسال طلب الدفع.

### Data

- جدول `Car` هو مصدر بيانات العربيات والأسعار.
- جدول `CarBooking` هو مصدر حجوزات السيارات.
- كل حجز مرتبط بعربية.
- حالة الحجز تبدأ `pending`.
- بعد نجاح الدفع تبقى `confirmed`.
- لو الدفع فشل أو المستخدم لغى، تفضل غير مؤكدة أو تظهر رسالة فشل حسب الرجوع من بوابة الدفع.

## شرح باقي أجزاء المشروع بسرعة

### التسجيل والطلاب

فيه صفحات لتسجيل الطلاب والركاب وربطهم بجامعة أو فئة. الطالب له كود جامعي، رقم موبايل، مدة اشتراك، وعدد رحلات مستخدمة.

### الرحلات والباصات

الأدمن يضيف باصات ورحلات. كل باص له سعة ومقاعد، وكل رحلة ممكن يتعمل عليها حجوزات.

### الحجز العادي

المستخدم يختار رحلة أو فورم حجز، يدخل بياناته، يدفع أو يتأكد حجزه، وبعدها يقدر يشوف حجوزاته من `/allen/bookings/` أو `/allen/my-buses/`.

### QR والحضور

فيه صفحات لمسح QR وتأكيد حضور الراكب. ده مفيد في الرحلات الجامعية عشان السائق أو الأدمن يعرف مين ركب فعلا.

### تتبع الباص

فيه endpoints لتحديث مكان الباص وجلبه:

```text
/allen/api/update-location/<bus_id>/
/allen/api/get-location/<bus_id>/
/allen/track/<bus_id>/
```

الفكرة إن مكان الباص يتبعت للسيرفر، والعميل يقدر يشوفه على خريطة.

### لوحة الأدمن والداشبورد

فيه Django admin على:

```text
/allen/admin/
```

وفيه dashboard مخصصة على:

```text
/allen/dashboard/
```

الداشبورد فيها إدارة رحلات، ركاب، تقارير، جامعات، باصات، وإحصائيات.

### WhatsApp وTelegram

المشروع بيستخدم UltraMsg لإرسال واتساب، وTelegram bot للتنبيهات وربط الحسابات. لازم تحط التوكنات في environment variables عشان يشتغلوا.

## ملاحظات مهمة للطلبة

- المشروع كبير وفيه كود قديم وكود جديد مع بعض، فطبيعي تلاقوا imports متكررة أو functions قديمة متعلقة بتجارب سابقة.
- جزء تأجير السيارات الحالي يعتمد أكتر على `create_car_payment` والـ JavaScript في `car_detail.html`.
- في `CarBooking.calculate_total_price` فيه إشارات لحقول قديمة زي `price_per_km_below_300` و`price_per_km_above_300`، بينما موديل `Car` الحالي يستخدم شرائح مفصلة زي `price_per_km_0_100`. لو هتستخدموا الدالة دي لازم تتراجع.
- صفحة `car_list.html` بتعرض أسماء حقول غير موجودة حاليا في `Car` زي `price_per_KM` و`fuel_type`. الأفضل توحيد الأسماء أو إضافة الحقول بمigration لو مطلوبة.
- متحطوش مفاتيح الدفع أو واتساب أو Telegram في GitHub. خلوها في `.env`.
- لو الدفع مش شغال، غالبا مفاتيح Kashier ناقصة أو `KASHIER_MODE` مش مناسب.
- لو البحث في الخريطة مش شغال، راجع إعدادات `SELF_HOSTED_NOMINATIM_URL`, `SELF_HOSTED_OSRM_URL`, `PUBLIC_PHOTON_URL`, و`PUBLIC_OSRM_URL`.

## رفع المشروع على GitHub

لو المشروع لسه مش Git repo:

```powershell
git init
git branch -M main
git remote add origin https://github.com/AmrShalaby12/eslam_project.git
git add .
git commit -m "Add Egyptian Arabic project documentation"
git push -u origin main
```

لو المشروع already Git repo:

```powershell
git remote set-url origin https://github.com/AmrShalaby12/eslam_project.git
git add .
git commit -m "Add Egyptian Arabic project documentation"
git push origin main
```

لو GitHub طلب login، استخدم GitHub account أو Personal Access Token حسب إعدادات جهازك.

## ملخص سريع جدا

المشروع ده Django system لإدارة رحلات وباصات وطلاب وتأجير سيارات. `/allen/cars/` بتعرض قائمة السيارات، و`/allen/car/5/` بتعرض تفاصيل عربية ID بتاعها 5 وتخلي المستخدم يحدد المشوار ويتحسبله السعر ويتنقل للدفع. الداتا الأساسية في جزء السيارات جاية من `Car` و`CarBooking`، والفرونت بيعتمد على خريطة وJavaScript لحساب المسافة والسعر قبل ما الباك إند ينشئ طلب دفع على Kashier.
