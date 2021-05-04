from tg_bot.etc.database import model, models


def test_model_is_modified():
    assert models.Users.is_modified() is False


def test_import_sql():
    assert "CREATE TABLE" in model.Model.import_sql()
