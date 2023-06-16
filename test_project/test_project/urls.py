from django.urls import include, path

urlpatterns = [
    path("", include("modoboa.urls")),
    path("django_rq/", include("django_rq.urls")),
]
