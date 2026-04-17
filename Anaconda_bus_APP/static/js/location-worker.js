let locationIntervalId = null;
let currentBusId = null;

// دالة لإرسال الموقع
function sendLocation() {
    if (!currentBusId) return;

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const { latitude, longitude } = position.coords;
            const url = `/allen/api/update-location/${currentBusId}/`;

            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ latitude, longitude })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    console.log('Background location sent successfully.');
                } else {
                    // إذا انتهت الجلسة، أوقف الإرسال
                    console.log('Session expired or inactive. Stopping background updates.');
                    stopSending();
                }
            })
            .catch(err => console.error('Background fetch failed:', err));
        },
        (error) => {
            console.error('Background geolocation error:', error);
        }
    );
}

function startSending(busId) {
    if (locationIntervalId) {
        clearInterval(locationIntervalId);
    }
    currentBusId = busId;
    console.log(`Starting background location updates for bus ${busId} every 30 seconds.`);
    // الإرسال عند الطلب فقط هو أمر معقد جدًا (يتطلب Push API)
    // الحل الأبسط هو الإرسال بشكل دوري طالما الجلسة نشطة
    sendLocation(); // أرسل مرة فورًا
    locationIntervalId = setInterval(sendLocation, 30000); // كل 30 ثانية
}

function stopSending() {
    if (locationIntervalId) {
        clearInterval(locationIntervalId);
        locationIntervalId = null;
        currentBusId = null;
        console.log('Stopped background location updates.');
    }
}

// الاستماع للرسائل من الصفحة الرئيسية
self.addEventListener('message', (event) => {
    const { action, busId } = event.data;
    if (action === 'start') {
        startSending(busId);
    } else if (action === 'stop') {
        stopSending();
    }
});
