import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.users.models import Role, User


class Command(BaseCommand):
    help = "Crée un agent et un usager de démonstration (environnement de dev uniquement)."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Mot de passe des comptes (généré aléatoirement sinon).")
        parser.add_argument("--npi", default="0123456789", help="NPI de l'usager de démo.")

    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError("seed_demo est réservé à DJANGO_DEBUG=1.")
        password = opts["password"] or secrets.token_urlsafe(12)
        User.objects.filter(username="agent1").delete()
        User.objects.filter(username=opts["npi"]).delete()
        User.objects.create_user(username="agent1", role=Role.AGENT, password=password)
        User.objects.create_user(username=opts["npi"], npi=opts["npi"], role=Role.USAGER, password=password)
        self.stdout.write(f"agent  : username=agent1  password={password}")
        self.stdout.write(f"usager : username={opts['npi']}  password={password}")
