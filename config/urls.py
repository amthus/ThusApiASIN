from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.demandes.urls")),
    path("", TemplateView.as_view(template_name="ecran.html"), name="ecran"),
]
