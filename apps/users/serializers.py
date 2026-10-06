from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.demandes.exceptions import ConflictError
from apps.demandes.validators import npi_validator

from .models import Role, User


class RegisterSerializer(serializers.Serializer):
    npi = serializers.CharField(validators=[npi_validator])
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)

    def validate(self, attrs):
        validate_password(attrs["password"], user=User(username=attrs["npi"]))
        return attrs

    def create(self, validated_data):
        npi = validated_data["npi"]
        if User.objects.filter(npi=npi).exists():
            raise ConflictError("Un compte existe déjà pour ce NPI.")
        try:
            # create_user hache le mot de passe (PBKDF2 Django) ; l'unicité est aussi garantie en base.
            return User.objects.create_user(
                username=npi, npi=npi, role=Role.USAGER, password=validated_data["password"]
            )
        except IntegrityError:
            raise ConflictError("Un compte existe déjà pour ce NPI.")


class LoginSerializer(TokenObtainPairSerializer):
    """Ajoute le rôle et le NPI à la réponse de connexion pour adapter l'interface."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["role"] = self.user.role
        data["npi"] = self.user.npi
        return data
