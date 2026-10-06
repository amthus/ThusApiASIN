from rest_framework.routers import SimpleRouter

from .views import DemandeViewSet

router = SimpleRouter()
router.register("demandes", DemandeViewSet, basename="demande")
urlpatterns = router.urls
