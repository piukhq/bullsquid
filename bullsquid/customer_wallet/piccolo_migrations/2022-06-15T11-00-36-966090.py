from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text
from piccolo.table import Table

ID = "2022-06-15T11:00:36:966090"
VERSION = "0.74.4"
DESCRIPTION = "replace unique constraint on user_id with auth_id+user_id"


class UserLookup(Table):
    ...


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="customer_wallet", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="UserLookup",
        tablename="user_lookup",
        column_name="user_id",
        params={"unique": False},
        old_params={"unique": True},
        column_class=Text,
        old_column_class=Text,
    )

    async def run():
        q = "CREATE UNIQUE INDEX unique_auth_id_user_id ON user_lookup(auth_id, user_id)"
        await UserLookup.raw(q)

    manager.add_raw(run)

    return manager
