"""Migration router."""

import os
import re
import sys
import peewee
import pkgutil
import pathlib
import logging
from unittest import mock
from types import ModuleType
from importlib import import_module
from functools import cached_property

from .logger import LOGGER
from .migrator import Migrator
from tg_bot.etc.conf import settings
from .auto import diff_many, NEWLINE
from tg_bot.etc.database.models import MigrateHistory


CLEAN_RE = re.compile(r'\s+$', re.M)
CURDIR = os.getcwd()
UNDEFINED = object()
VOID = lambda m, d: None # noqa
template_path = os.path.join(pathlib.Path(__file__).parent, "template.txt")
with open(template_path) as t:
    MIGRATE_TEMPLATE = t.read()


class BaseRouter(object):

    """Abstract base class for router."""

    def __init__(self, database, ignore=None, schema=None, logger=LOGGER):
        """Initialize the router."""
        self.database = database
        self.schema = schema
        self.ignore = ignore
        self.logger = logger
        if not isinstance(self.database, (peewee.Database, peewee.Proxy)):
            raise RuntimeError('Invalid database: %s' % database)

    @cached_property
    def model(self) -> MigrateHistory:
        """Initialize and cache MigrationHistory model."""
        MigrateHistory._meta.database = self.database
        MigrateHistory._meta.schema = self.schema
        MigrateHistory.create_table(True)
        return MigrateHistory

    @property
    def todo(self):
        """Get migrations to run."""
        raise NotImplementedError

    @property
    def done(self):
        """Scan migrations in database."""
        return [mm.name for mm in self.model.select().order_by(self.model.id)]

    @property
    def diff(self):
        """Calculate difference between fs and db."""
        done = set(self.done)
        return [name for name in self.todo if name not in done]

    @cached_property
    def migrator(self):
        """Create migrator and setup it with fake migrations."""
        migrator = Migrator(self.database)
        for name in self.done:
            self.run_one(name, migrator)
        return migrator

    def create(self, name='auto', auto=False):
        """Create a migration.

        :param auto: Python module path to scan for models.
        """
        migrate = rollback = ''
        if auto:
            # Need to append the CURDIR to the path for import to work.
            sys.path.append(CURDIR)
            models = auto if isinstance(auto, list) else [auto]
            if not all([_check_model(m) for m in models]):
                try:
                    modules = models
                    if isinstance(auto, bool):
                        modules = [m for _, m, ispkg in pkgutil.iter_modules([CURDIR]) if ispkg]
                    models = [m for module in modules for m in load_models(module)]

                except ImportError as exc:
                    self.logger.exception(exc)
                    return self.logger.error("Can't import models module: %s", auto)

            if self.ignore:
                models = [m for m in models if m._meta.name not in self.ignore]

            for migration in self.diff:
                self.run_one(migration, self.migrator, fake=True)

            migrate = compile_migrations(self.migrator, models)
            if not migrate:
                return self.logger.warning('No changes found.')

            rollback = compile_migrations(self.migrator, models, reverse=True)

        self.logger.info('Creating migration "%s"', name)
        name = self.compile(name, migrate, rollback)
        self.logger.info('Migration has been created as "%s"', name)
        return name

    def merge(self, name='initial'):
        """Merge migrations into one."""
        migrator = Migrator(self.database)
        migrate = compile_migrations(migrator, self.migrator.orm.values())
        if not migrate:
            return self.logger.error("Can't merge migrations")

        self.clear()

        self.logger.info('Merge migrations into "%s"', name)
        rollback = compile_migrations(self.migrator, [])
        name = self.compile(name, migrate, rollback, 0)

        migrator = Migrator(self.database)
        self.run_one(name, migrator, fake=True, force=True)
        self.logger.info('Migrations has been merged into "%s"', name)

    def clear(self):
        """Clear migrations."""
        self.model.delete().execute()

    def compile(self, name, migrate='', rollback='', num=None):
        raise NotImplementedError

    def read(self, name):
        raise NotImplementedError

    def run_one(self, name, migrator, fake=True, downgrade=False, force=False):
        """Run/emulate a migration with given name."""
        try:
            migrate, rollback = self.read(name)
            if fake:
                mocked_cursor = mock.Mock()
                mocked_cursor.fetch_one.return_value = None
                with mock.patch('peewee.Model.select'):
                    with mock.patch('peewee.Database.execute_sql', return_value=mocked_cursor):
                        migrate(migrator, self.database, fake=fake)

                if force:
                    self.model.create(name=name)
                    self.logger.info('Done %s', name)

                migrator.clean()
                return migrator

            with self.database.transaction():
                if not downgrade:
                    self.logger.info('Migrate "%s"', name)
                    migrate(migrator, self.database, fake=fake)
                    migrator.run()
                    self.model.create(name=name)
                else:
                    self.logger.info('Rolling back %s', name)
                    rollback(migrator, self.database, fake=fake)
                    migrator.run()
                    self.model.delete().where(self.model.name == name).execute()

                self.logger.info('Done %s', name)

        except Exception:
            self.database.rollback()
            operation = 'Migration' if not downgrade else 'Rollback'
            self.logger.exception('%s failed: %s', operation, name)
            raise

    def run(self, name=None, fake=False):
        """Run migrations."""
        self.logger.info('Starting migrations')

        done = []
        diff = self.diff
        if not diff:
            self.logger.info('There is nothing to migrate')
            return done

        migrator = self.migrator
        for mname in diff:
            self.run_one(mname, migrator, fake=fake, force=fake)
            done.append(mname)
            if name and name == mname:
                break

        return done

    def rollback(self, name):
        name = name.strip()
        done = self.done
        if not done:
            raise RuntimeError('No migrations are found.')
        if name != done[-1]:
            raise RuntimeError('Only last migration can be canceled.')

        migrator = self.migrator
        self.run_one(name, migrator, False, True)
        self.logger.warning('Downgraded migration: %s', name)


class Router(BaseRouter):

    filemask = re.compile(r"[\d]{3}_[^\.]+\.py$")

    def __init__(self, database, migrate_dir, **kwargs):
        super(Router, self).__init__(database, **kwargs)
        self.migrate_dir = migrate_dir

    @property
    def todo(self):
        """Scan migrations in file system."""
        if not os.path.exists(self.migrate_dir):
            self.logger.warning('Migration directory: %s does not exist.', self.migrate_dir)
            os.makedirs(self.migrate_dir)
        return sorted(f[:-3] for f in os.listdir(self.migrate_dir) if self.filemask.match(f))

    def compile(self, name, migrate='', rollback='', num=None):
        """Create a migration."""
        if num is None:
            num = len(self.todo)

        name = '{:03}_'.format(num + 1) + name
        filename = name + '.py'
        path = os.path.join(self.migrate_dir, filename)
        with open(path, 'w') as f:
            f.write(MIGRATE_TEMPLATE.format(migrate=migrate, rollback=rollback, name=filename))

        return name

    def read(self, name):
        """Read migration from file."""
        call_params = dict()
        if os.name == 'nt' and sys.version_info >= (3, 0):
            # if system is windows - force utf-8 encoding
            call_params['encoding'] = 'utf-8'

        migration_file = "{}.py".format(name)

        if name.endswith("tg_bot") is False:
            migration_path = os.path.join(self.migrate_dir, migration_file)
        else:
            migration_path = os.path.join(pathlib.Path(__file__).parent.parent.parent, "migrations", migration_file)


        with open(migration_path, **call_params) as f:
            code = f.read()
            scope = {}
            code = compile(code, '<string>', 'exec', dont_inherit=True)
            exec(code, scope, None)
            return scope.get('migrate', VOID), scope.get('rollback', VOID)

    def clear(self):
        """Remove migrations from fs."""
        super(Router, self).clear()
        for name in self.todo:
            filename = os.path.join(self.migrate_dir, name + '.py')
            os.remove(filename)


class ModuleRouter(BaseRouter):

    def __init__(self, database, migrate_module='migrations', **kwargs):
        """Initialize the router."""
        super(ModuleRouter, self).__init__(database, **kwargs)

        if isinstance(migrate_module, str):
            migrate_module = import_module(migrate_module)

        self.migrate_module = migrate_module

    def read(self, name):
        """Read migrations from a module."""
        mod = getattr(self.migrate_module, name)
        return getattr(mod, 'migrate', VOID), getattr(mod, 'rollback', VOID)


def load_models(module):
    models = []
    models_module = import_module("models")
    for attribute_name in dir(models_module):
        model = getattr(models_module, attribute_name)
        if _check_model(model):
            models.append(model)

    return models

def _import_submodules(package, passed=UNDEFINED):
    return import_module("models")


def _check_model(obj):
    """Check object if it's a peewee model and unique."""
    return isinstance(obj, type) and issubclass(obj, peewee.Model) and hasattr(obj, '_meta')


def compile_migrations(migrator, models, reverse=False):
    """Compile migrations for given models."""
    source = migrator.orm.values()
    if reverse:
        source, models = models, source

    migrations = diff_many(models, source, migrator, reverse=reverse)
    if not migrations:
        return False

    migrations = NEWLINE + NEWLINE.join('\n\n'.join(migrations).split('\n'))
    return CLEAN_RE.sub('\n', migrations)
