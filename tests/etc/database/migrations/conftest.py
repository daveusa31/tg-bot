import os
import peewee
import pathlib
import pytest
import playhouse.db_url


@pytest.fixture()
def migrations_dir():
    """Migrations dir"""
    return pathlib.Path(__file__).with_name('migrations')


@pytest.fixture(params=['sqlite', 'postgresql'])
def database(request):
    if request.param == 'sqlite':
        db = playhouse.db_url.connect('sqlite:///:memory:')
    else:
        dsn = os.getenv('POSTGRES_DSN')
        if not dsn:
            raise pytest.skip('Postgres not found')
        db = playhouse.db_url.connect(dsn)

    with db.atomic():
        yield db
        db.rollback()


@pytest.fixture()
def router(migrations_dir, database):
    from tg_bot.etc.database.migrations.cli import get_router
    router = get_router(migrations_dir, database)

    assert isinstance(router.database, peewee.Database)

    return router
