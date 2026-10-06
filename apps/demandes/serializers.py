from rest_framework import serializers

from .models import Demande, HistoriqueStatut, Statut, TypeActe
from .validators import npi_validator


class DemandeCreateSerializer(serializers.Serializer):
    npi = serializers.CharField(validators=[npi_validator])
    type_acte = serializers.ChoiceField(choices=TypeActe.choices)
    nombre_copies = serializers.IntegerField(min_value=1, max_value=5)


class RejetSerializer(serializers.Serializer):
    motif = serializers.CharField(max_length=500)  # obligatoire, non vide


class ListQuerySerializer(serializers.Serializer):
    npi = serializers.CharField(required=False, validators=[npi_validator])
    statut = serializers.ChoiceField(choices=Statut.choices, required=False)


class HistoriqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoriqueStatut
        fields = ["ancien_statut", "nouveau_statut", "motif", "acteur_id", "created_at"]


class DemandeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Demande
        fields = ["id", "npi", "type_acte", "nombre_copies", "statut", "motif_rejet", "created_at", "updated_at"]


class DemandeDetailSerializer(DemandeSerializer):
    historique = HistoriqueSerializer(many=True, read_only=True)

    class Meta(DemandeSerializer.Meta):
        fields = DemandeSerializer.Meta.fields + ["historique"]
