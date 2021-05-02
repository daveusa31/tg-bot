from unittest import mock

import pytest


@pytest.fixture()
def _mock_connection():
    """Monkey patch psycopg2 connect"""
    import psycopg2
    from tests.etc.database.migrations.mocks import postgres

    with mock.patch.object(psycopg2, "connect", postgres.MockConnection):
        yield


def test_migrator():
    import peewee as pw
    from playhouse.db_url import connect
    from tg_bot.etc.database.migrations import Migrator

    database = connect('sqlite:///:memory:')
    migrator = Migrator(database)

    @migrator.create_table
    class Customer(pw.Model):
        name = pw.CharField()

    assert Customer == migrator.orm['customer']

    @migrator.create_table
    class Order(pw.Model):
        number = pw.CharField()
        uid = pw.CharField(unique=True)

        customer_id = pw.ForeignKeyField(Customer, column_name='customer_id')

    assert Order == migrator.orm['order']
    migrator.run()

    migrator.add_columns(Order, finished=pw.BooleanField(default=False))
    assert 'finished' in Order._meta.fields
    migrator.run()

    migrator.drop_columns('order', 'finished', 'customer_id', 'uid')
    assert 'finished' not in Order._meta.fields
    assert not hasattr(Order, 'customer_id')
    assert not hasattr(Order, 'customer_id_id')
    migrator.run()

    migrator.add_columns(Order, customer=pw.ForeignKeyField(Customer, null=True))
    assert 'customer' in Order._meta.fields
    assert Order.customer.name == 'customer'
    migrator.run()
    assert Order.customer.name == 'customer'

    migrator.rename_field(Order, 'number', 'identifier')
    assert 'identifier' in Order._meta.fields
    migrator.run()

    migrator.drop_not_null(Order, 'identifier')
    assert Order._meta.fields['identifier'].null
    assert Order._meta.columns['identifier'].null
    migrator.run()

    migrator.add_default(Order, 'identifier', 11)
    assert Order._meta.fields['identifier'].default == 11
    migrator.run()

    migrator.change_columns(Order, identifier=pw.IntegerField(default=0))
    assert Order.identifier.field_type == 'INT'
    migrator.run()

    Order.create(identifier=55)
    migrator.sql('UPDATE "order" SET identifier = 77;')
    migrator.run()
    order = Order.get()
    assert order.identifier == 77

    migrator.add_index(Order, 'identifier', 'customer')
    migrator.run()
    assert Order._meta.indexes
    assert not Order.identifier.index

    migrator.drop_index(Order, 'identifier', 'customer')
    migrator.run()
    assert not Order._meta.indexes

    migrator.remove_fields(Order, 'customer')
    migrator.run()
    assert not hasattr(Order, 'customer')

    migrator.add_index(Order, 'identifier', unique=True)
    migrator.run()
    assert not Order.identifier.index
    assert Order.identifier.unique
    assert Order._meta.indexes

    migrator.change_columns(Order, identifier=pw.IntegerField(default=0))
    assert not Order._meta.indexes


def test_migrator_postgres(_mock_connection):
    """
    Ensure change_fields generates queries and
    does not cause exception
    """
    import peewee
    from playhouse.db_url import connect
    from tg_bot.etc.database.migrations import Migrator

    database = connect('postgres:///fake')

    migrator = Migrator(database)
    @migrator.create_table
    class User(peewee.Model):
        name = peewee.CharField()
        created_at = peewee.DateField()

    assert User == migrator.orm['user']

    # Date -> DateTime
    migrator.change_fields('user', created_at=peewee.DateTimeField())
    migrator.run()
    assert 'ALTER TABLE "user" ALTER COLUMN "created_at" TYPE TIMESTAMP' in database.cursor().queries
    
    # Char -> Text
    migrator.change_fields('user', name=peewee.TextField())
    migrator.run()
    assert 'ALTER TABLE "user" ALTER COLUMN "name" TYPE TEXT' in database.cursor().queries


def test_migrator_schema(_mock_connection):
    import peewee as pw
    from playhouse.db_url import connect
    from tg_bot.etc.database.migrations import Migrator

    database = connect('postgres:///fake')
    schema_name = 'test_schema'
    migrator = Migrator(database, schema=schema_name)

    def has_schema_select_query():
        return database.cursor().queries[0] == 'SET search_path TO {}'.format(schema_name)

    @migrator.create_table
    class User(pw.Model):
        name = pw.CharField()
        created_at = pw.DateField()

    migrator.run()
    assert has_schema_select_query()

    migrator.change_fields('user', created_at=pw.DateTimeField())
    migrator.run()
    assert has_schema_select_query()

