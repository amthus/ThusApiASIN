from django.core.validators import RegexValidator

npi_validator = RegexValidator(r"^[0-9]{10}$", "Le NPI doit comporter exactement 10 chiffres.")


def mask_npi(npi: str | None) -> str:
    """N'écrit jamais un NPI complet dans les logs."""
    return f"******{npi[-4:]}" if npi else "-"
