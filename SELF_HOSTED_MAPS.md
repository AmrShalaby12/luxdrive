# Self-Hosted Maps Stack

الهدف هنا هو تشغيل الخريطة والبحث والمسافات بدون `Google Maps` وبدون أي `API key` خارجي.

## التركيبة المقترحة

- `Tiles`: سيرفر tiles محلي مبني على بيانات OpenStreetMap لمصر فقط.
- `Search / Reverse`: `Photon` مفضل للـ autocomplete، أو `Nominatim` كبديل.
- `Routing`: `OSRM` محلي لحساب مسافات القيادة الفعلية.

## ما تم ربطه داخل المشروع

الواجهة في صفحة السيارة لم تعد تعتمد على Google.

الصفحة الآن تعتمد على:

- `GET /allen/api/maps/search/`
- `GET /allen/api/maps/reverse/`
- `GET /allen/api/maps/route/`

وهذه الـ endpoints بدورها تتكلم مع الخدمات الداخلية حسب متغيرات البيئة.

## متغيرات البيئة

أضف القيم التالية في بيئة Django:

```env
SELF_HOSTED_TILE_URL=/tiles/{z}/{x}/{y}.png
SELF_HOSTED_TILE_ATTRIBUTION=&copy; OpenStreetMap contributors
SELF_HOSTED_PHOTON_URL=
SELF_HOSTED_NOMINATIM_URL=http://nominatim:8080
SELF_HOSTED_OSRM_URL=http://osrm:5000
SELF_HOSTED_VALHALLA_URL=
```

ملاحظات:

- لو `Photon` غير متاح، سيستخدم المشروع `Nominatim` افتراضيًا على `http://nominatim:8080`.
- لو `OSRM` غير متاح، يمكن استخدام `Valhalla` كبديل، لكن `OSRM` أبسط في الدمج الحالي.

## Troubleshooting

إذا ظهرت رسالة أن `reverse geocoding` غير متاح:

- الواجهة الآن ستكمل العمل باستخدام الإحداثيات بدل اسم العنوان.
- هذا يعني أن خدمة `Nominatim` أو `Photon` المحلية غير شغالة أو غير مربوطة على نفس الشبكة.
- في هذا الوضع: اختيار النقاط من الخريطة سيعمل، لكن البحث النصي لن يكون بالمستوى المطلوب حتى تشغّل geocoder الداخلي.

## Nginx

لازم تعمل proxy للـ tile server على نفس الدومين:

```nginx
location /tiles/ {
    proxy_pass http://tiles:8080/tile/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## بيانات مصر

استخدم extract مصر فقط بدل planet كامل لتقليل الحجم والـ RAM.

ملف البيانات الموصى به:

- `https://download.geofabrik.de/africa/egypt-latest.osm.pbf`

## الترتيب العملي

1. شغّل tile server محلي لبيانات مصر.
2. شغّل `OSRM` على نفس extract مصر.
3. شغّل `Photon` أو `Nominatim` للبحث.
4. اضبط متغيرات البيئة أعلاه.
5. اضبط Nginx لمسار `/tiles/`.

## ملاحظة مهمة

إذا كان المطلوب "قوة قريبة من Google" بدون أي API خارجي، فهذا لا يتحقق بخدمة مجانية عامة من الإنترنت. الحل الجاد الوحيد هو stack self-hosted على سيرفرك مع تحديث بيانات OSM باستمرار.
