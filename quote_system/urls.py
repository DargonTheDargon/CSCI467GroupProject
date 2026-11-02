from django.urls import include, path

from . import views

urlpatterns = [
    path("interface1/", views.interface1, name="interface1"),
    path("accounts/", include("django.contrib.auth.urls")),
]