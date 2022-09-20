from piccolo.apps.migrations.auto.migration_manager import MigrationManager

ID = "2022-09-20T17:30:53:077239"
VERSION = "0.74.4"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.rename_table(
        old_class_name="LocationSecondaryMIDLink",
        old_tablename="location_secondary_mid_link",
        new_class_name="SecondaryMIDLocationLink",
        new_tablename="secondary_mid_location_link",
    )

    return manager
