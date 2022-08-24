from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.table import Table

ID = "2022-08-24T16:08:38:889419"
VERSION = "0.74.4"
DESCRIPTION = "add unique constraint for location & secondary MID link table"


class LocationSecondaryMIDLink(Table):
    ...


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    async def run():
        q = "CREATE UNIQUE INDEX unique_location_secondary_mid ON location_secondary_mid_link(location, secondary_mid)"
        await LocationSecondaryMIDLink.raw(q)

    manager.add_raw(run)

    return manager
