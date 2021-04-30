from . import BaseCommand
from tg_bot.etc.conf import settings
from tg_bot.etc.database import migrations


class Command(BaseCommand):
    def handle(self):
        router = migrations.Router(settings.DATABASE["peewee_engine"], settings.BASE_DIR / "migrations")
        router.create(auto=True)
        