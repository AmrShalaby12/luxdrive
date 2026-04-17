
    // منع كليك يمين
    document.addEventListener("contextmenu", e => e.preventDefault());

    // منع اختصارات أدوات المطور
    document.addEventListener("keydown", function(e) {
        if (e.key === "F12" || 
            (e.ctrlKey && e.shiftKey && e.key === "I") || 
            (e.ctrlKey && e.shiftKey && e.key === "J") || 
            (e.ctrlKey && e.key === "U")) {
            e.preventDefault();
        }
    });
        // تهيئة الخريطة
        let map, directionsService, directionsRenderer, fromAutocomplete, toAutocomplete;
        let distanceInKm = 0;
        const pricePerKm = parseFloat("{{ car.price_per_KM }}");
        
        function initMap() {
            // إنشاء الخريطة
            map = new google.maps.Map(document.getElementById("map"), {
                center: { lat: 30.0444, lng: 31.2357 }, // القاهرة
                zoom: 13,
                styles: [
    { elementType: 'geometry', stylers: [{ color: '#212121' }] },
    { elementType: 'labels.icon', stylers: [{ visibility: 'off' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#757575' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#212121' }] },
    {
        featureType: 'administrative',
        elementType: 'geometry',
        stylers: [{ color: '#757575' }]
    },
    {
        featureType: 'administrative.country',
        elementType: 'labels.text.fill',
        stylers: [{ color: '#9e9e9e' }]
    },
    {
        featureType: 'administrative.land_parcel',
        stylers: [{ visibility: 'off' }]
    },
    {
        featureType: 'administrative.locality',
        elementType: 'labels.text.fill',
        stylers: [{ color: '#bdbdbd' }]
    },
    {
        featureType: 'poi',
        elementType: 'labels.text.fill',
        stylers: [{ color: '#757575' }]
    },
    {
        featureType: 'poi.park',
        elementType: 'geometry',
        stylers: [{ color: '#181818' }]
    },
    {
        featureType: 'poi.park',
        elementType: 'labels.text.fill',
        stylers: [{ color: '#616161' }]
    },
    {
        featureType: 'poi.park',
        elementType: 'labels.text.stroke',
        stylers: [{ color: '#1b1b1b' }]
    },
    {
        featureType: 'road',
        elementType: 'geometry.fill',
        stylers: [{ color: '#2c2c2c' }]
    },
    {
        featureType: 'road',
        elementType: 'labels.text.fill',
        stylers: [{ color: '#8a8a8a' }]
    },
    {
        featureType: 'road.arterial',
        elementType: 'geometry',
        stylers: [{ color: '#373737' }]
    },
    {
        featureType: 'road.highway',
        elementType: 'geometry',
        stylers: [{ color: '#3c3c3c' }]
    },
    {
        featureType: 'road.highway.controlled_access',
        elementType: 'geometry',
        stylers: [{ color: '#4e4e4e' }]
    },
    {
        featureType: 'road.local',
        elementType: 'labels.text.fill',
        stylers: [{ color: '#616161' }]
    },
    {
        featureType: 'transit',
        elementType: 'geometry',
        stylers: [{ color: '#2f2f2f' }]
    },
    {
        featureType: 'transit.station',
        elementType: 'labels.text.fill',
        stylers: [{ color: '#757575' }]
    },
    {
        featureType: 'water',
        elementType: 'geometry',
        stylers: [{ color: '#000000' }]
    },
    {
        featureType: 'water',
        elementType: 'labels.text.fill',
        stylers: [{ color: '#3d3d3d' }]
    }
]

            });
            
            // تهيئة خدمة الاتجاهات
            directionsService = new google.maps.DirectionsService();
            directionsRenderer = new google.maps.DirectionsRenderer({
                map: map,
                suppressMarkers: true,
                polylineOptions: {
                    strokeColor: '#93148f',
                    strokeOpacity: 0.8,
                    strokeWeight: 5
                }
            });
            
            // إضافة علامة للمستخدم
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(position => {
                    const userLocation = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    
                    new google.maps.Marker({
                        position: userLocation,
                        map: map,
                        icon: {
                            path: google.maps.SymbolPath.CIRCLE,
                            scale: 8,
                            fillColor: '#4285F4',
                            fillOpacity: 1,
                            strokeWeight: 2,
                            strokeColor: '#ffffff'
                        }
                    });
                    
                    map.setCenter(userLocation);
                    
            
                });
            }
            
            // تهيئة الإكمال التلقائي
            fromAutocomplete = new google.maps.places.Autocomplete(
                document.getElementById("from"),
                { types: ["geocode"] }
            );
            
            toAutocomplete = new google.maps.places.Autocomplete(
                document.getElementById("to"),
                { types: ["geocode"] }
            );
            
            fromAutocomplete.addListener("place_changed", calcRoute);
            toAutocomplete.addListener("place_changed", calcRoute);
        }
        
        // حساب المسار
        function calcRoute() {
            const fromPlace = fromAutocomplete.getPlace();
            const toPlace = toAutocomplete.getPlace();
            
            if (!fromPlace || !toPlace) return;
            
            const request = {
                origin: fromPlace.formatted_address,
                destination: toPlace.formatted_address,
                travelMode: google.maps.TravelMode.DRIVING,
                unitSystem: google.maps.UnitSystem.METRIC
            };
            
            directionsService.route(request, (result, status) => {
                if (status == "OK") {
                    directionsRenderer.setDirections(result);
                    distanceInKm = result.routes[0].legs[0].distance.value / 1000;
                    calculatePrice();
                }
            });
        }
        
function calculatePrice() {
    const tripType = document.getElementById('trip_type').value;
    let totalPrice = 0;

    // أسعار ثابتة من السيرفر (ثابتة مهما كانت المسافة)
    const fixedPrices = {
        "day_use_12": parseFloat("{{ car.day_use_12_price }}"),
        "day_use_10": parseFloat("{{ car.day_use_10_price }}"),
        "day_use_8": parseFloat("{{ car.day_use_8_price }}"),
        "airport_pickup": parseFloat("{{ car.airport_pickup_price }}")
    };

    // لو الخدمة من النوع الثابت
    if (fixedPrices.hasOwnProperty(tripType)) {
        totalPrice = fixedPrices[tripType];
        hideMapSection();  // ⛔ إخفاء الخريطة لأن الخدمة ثابتة
    } else {
        showMapSection();  // ✅ إظهار الخريطة لأننا نحتاج مسافة
        let totalDistance = distanceInKm;
        if (tripType === 'round_trip') {
            totalDistance *= 2;
        }

        const below300Price = parseFloat("{{ car.price_per_km_below_300 }}");
        const above300Price = parseFloat("{{ car.price_per_km_above_300 }}");

        const pricePerKm = totalDistance <= 300 ? below300Price : above300Price;
        totalPrice = totalDistance * pricePerKm;
    }

    const totalWithFees = totalPrice * 1.02;
    document.getElementById("total-amount").textContent = totalWithFees.toFixed(2) + " EGP";
    updatePaymentAmount();
}

// إظهار/إخفاء خريطة الموقع حسب نوع الرحلة
function hideMapSection() {
    document.querySelector(".map-fullscreen").style.display = "none";
}
function showMapSection() {
    document.querySelector(".map-fullscreen").style.display = "block";
}

// تحديث السعر عند تغيير نوع الرحلة
document.getElementById("trip_type").addEventListener("change", function () {
    calculatePrice();
});

// تحديث المبلغ المطلوب دفعه بناء على نسبة الدفع
function updatePaymentAmount() {
    const totalWithFees = parseFloat(document.getElementById("total-amount").textContent.split(" ")[0]);
    const paymentPercentage = document.querySelector('input[name="payment_percentage"]:checked').value;
    let paymentAmount = totalWithFees;

    if (paymentPercentage === "50") {
        paymentAmount = totalWithFees / 2;
    }

    document.getElementById("payment-amount").textContent = paymentAmount.toFixed(2) + " EGP";
    document.getElementById("payment-amount-section").style.display = "block";
}

// تحديث المبلغ عند تغيير النسبة
document.querySelectorAll('input[name="payment_percentage"]').forEach(radio => {
    radio.addEventListener('change', updatePaymentAmount);
});

// تحديث السعر تلقائيًا عند تحميل الصفحة (اختياري)
window.addEventListener("load", function () {
    calculatePrice();
});
document.getElementById("trip_type").addEventListener("change", function () {
    const tripType = this.value;

    const goGroup = document.getElementById("go-date-group");
    const returnGroup = document.getElementById("return-date-group");

    if (tripType === "one_way_go") {
        goGroup.style.display = "block";
        returnGroup.style.display = "none";
    } else if (tripType === "one_way_return") {
        goGroup.style.display = "none";
        returnGroup.style.display = "block";
    } else if (tripType === "round_trip") {
        goGroup.style.display = "block";
        returnGroup.style.display = "block";
    }
});


function updatePaymentAmount() {
    const totalWithFees = parseFloat(document.getElementById("total-amount").textContent.split(" ")[0]);
    const paymentPercentage = document.querySelector('input[name="payment_percentage"]:checked').value;
    let paymentAmount = totalWithFees;
    
    if (paymentPercentage === "50") {
        paymentAmount = totalWithFees / 2;
    }
    
    document.getElementById("payment-amount").textContent = paymentAmount.toFixed(2) + " EGP";
    document.getElementById("payment-amount-section").style.display = "block";
}
// أضف مستمع حدث لخيارات نسبة الدفع
document.querySelectorAll('input[name="payment_percentage"]').forEach(radio => {
    radio.addEventListener('change', updatePaymentAmount);
});
        // تهيئة بانوراما 360 درجة
        window.addEventListener("load", function() {
            const panoramaURL = "{{ car.panorama_image.url }}";
            if (panoramaURL) {
                pannellum.viewer('panorama-container', {
                    type: "equirectangular",
                    panorama: panoramaURL,
                    autoLoad: true,
                    showZoomCtrl: true,
                    compass: true,
                    autoRotate: -2,
                    hotSpots: [
                        {
                            pitch: 0,
                            yaw: 0,
                            type: "info",
                            text: "{{ car.brand }} - {{ car.name }}"
                        }
                    ]
                });
            }
        });
        
function openKashierCheckout() {
    const paymentAmount = document.getElementById("payment-amount").innerText.split(" ")[0];

    if (parseFloat(paymentAmount) <= 0) {
        alert("الرجاء تحديد مسار الرحلة أولاً");
        return;
    }

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // 🟢 اجلب القيم من الفورم
    const customerName = document.getElementById("id_customer_name").value;
    const phoneNumber = document.getElementById("id_phone_number").value;
    const tripType = document.getElementById("trip_type").value;
    const goDate = document.getElementById("go_date")?.value || "";
    const returnDate = document.getElementById("return_date")?.value || "";
    const carId = "{{ car.id }}"; 

    // ⚠️ تحقق من القيم الأساسية
    if (!customerName || !phoneNumber || !tripType) {
        alert("يرجى تعبئة جميع البيانات المطلوبة قبل الدفع.");
        return;
    }

    fetch("{% url 'create_car_payment' %}", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({
            total_price: paymentAmount,
            payment_percentage: document.querySelector('input[name="payment_percentage"]:checked').value,
            customer_name: customerName,
            phone_number: phoneNumber,
            trip_type: tripType,
            go_date: goDate,
            return_date: returnDate,
            car_id: carId
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw err; });
        }
        return response.json();
    })
    .then(data => {
        if (data.checkout_url) {
            window.open(data.checkout_url, "_blank");
        } else if (data.error) {
            alert("خطأ: " + data.error);
        }
    })
    .catch(error => {
        console.error("حدث خطأ:", error);
        alert("فشل في إنشاء رابط الدفع: " + (error.error || error.message || "حدث خطأ غير معروف"));
    });
}

