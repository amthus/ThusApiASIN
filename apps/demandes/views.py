from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import Demande, Statut
from .permissions import IsAgent, assert_can_access_npi
from .serializers import (
    DemandeCreateSerializer,
    DemandeDetailSerializer,
    DemandeSerializer,
    ListQuerySerializer,
    RejetSerializer,
)


class DemandeViewSet(viewsets.GenericViewSet):
    lookup_value_regex = "[0-9a-fA-F-]{36}"
    serializer_class = DemandeSerializer

    def get_permissions(self):
        if self.action in {"prendre_en_charge", "valider", "rejeter"}:
            return [IsAgent()]
        return super().get_permissions()

    def get_queryset(self):
        """Périmètre de visibilité : un usager ne voit que son NPI (les autres ids donnent 404)."""
        qs = Demande.objects.all()
        user = self.request.user
        if user.is_usager:
            qs = qs.filter(npi=user.npi)
        if self.action == "retrieve":
            qs = qs.prefetch_related("historique")
        return qs

    def _filtered(self, request):
        q = ListQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        npi = q.validated_data.get("npi")
        if npi:
            assert_can_access_npi(request.user, npi)
        qs = self.get_queryset()
        if npi:
            qs = qs.filter(npi=npi)
        return qs, q.validated_data.get("statut")

    # POST /api/demandes/
    def create(self, request):
        s = DemandeCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        assert_can_access_npi(request.user, s.validated_data["npi"])
        key = request.headers.get("Idempotency-Key", "").strip()[:100]
        demande, created = services.creer_demande(acteur=request.user, idempotency_key=key, **s.validated_data)
        return Response(
            DemandeSerializer(demande).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    # GET /api/demandes/?npi=&statut=&page=   (plus récentes d'abord)
    def list(self, request):
        qs, statut = self._filtered(request)
        if statut:
            qs = qs.filter(statut=statut)
        qs = qs.order_by("-created_at", "-id")  # ordre total stable pour la pagination
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(DemandeSerializer(page, many=True).data)

    # GET /api/demandes/{id}/
    def retrieve(self, request, pk=None):
        demande = self.get_object()
        return Response(DemandeDetailSerializer(demande).data)

    # GET /api/demandes/stats/?npi=
    @action(detail=False, methods=["get"])
    def stats(self, request):
        qs, _ = self._filtered(request)
        counts = dict(qs.values_list("statut").annotate(n=Count("id")).order_by())
        par_statut = {s: counts.get(s, 0) for s in Statut.values}
        return Response({"total": sum(par_statut.values()), "par_statut": par_statut})

    def _transition(self, request, pk, nouveau, motif=""):
        demande = services.changer_statut(
            demande_id=pk, nouveau_statut=nouveau, acteur=request.user, motif=motif
        )
        return Response(DemandeSerializer(demande).data)

    @action(detail=True, methods=["post"], url_path="prendre-en-charge")
    def prendre_en_charge(self, request, pk=None):
        return self._transition(request, pk, Statut.EN_COURS)

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        return self._transition(request, pk, Statut.VALIDEE)

    @action(detail=True, methods=["post"])
    def rejeter(self, request, pk=None):
        s = RejetSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return self._transition(request, pk, Statut.REJETEE, s.validated_data["motif"])
