function showAiSuggestions(reservationId) {
    window.open(`/admin/app/formreservation/ai-suggestions/${reservationId}/`, '_blank', 'width=800,height=600');
}

function applyAiSuggestion(reservationId) {
    if (confirm('هل تريد تطبيق اقتراح الذكاء الاصطناعي على هذا الحجز؟')) {
        fetch(`/admin/app/formreservation/apply-ai-suggestion/${reservationId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('تم تطبيق الاقتراح بنجاح');
                location.reload();
            } else {
                alert('حدث خطأ: ' + data.error);
            }
        })
        .catch(error => {
            alert('حدث خطأ في الاتصال');
        });
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}