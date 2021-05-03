from . import BaseCommand
from tg_bot.etc.conf import settings
from tg_bot.etc.database import migrations


class Command(BaseCommand):
    def handle(self):
        migrate_dir = settings.BASE_DIR / "migrations"
        return migrations.Router(settings.DATABASE["peewee_engine"], migrate_dir, module_name="bot").create(auto=True)
