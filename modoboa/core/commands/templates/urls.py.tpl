from django.conf.urls import include, url

urlpatterns = [
    url(r'', include('modoboa.urls')),
    url(r'django_rq/', include('django_rq.urls')),
]
