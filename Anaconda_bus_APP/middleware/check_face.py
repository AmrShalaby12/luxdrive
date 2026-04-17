from django.shortcuts import redirect
from django.urls import reverse

class FaceCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            passenger = getattr(request.user, "passenger", None)
            if passenger and (not passenger.face_thumbnail ):
                # السماح فقط لصفحة رفع الصورة
                if request.path not in [reverse("upload_face")]:
                    return redirect("upload_face")

        return self.get_response(request)