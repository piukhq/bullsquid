from piccolo.apps.migrations.auto.migration_manager import MigrationManager

ID = "2022-08-24T16:06:08:228420"
VERSION = "0.74.4"
DESCRIPTION = "rename location/secondary MID link table"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="merchant_data", description=DESCRIPTION
    )

    manager.rename_table(
        old_class_name="LocationSecondaryMIDAssociation",
        old_tablename="location_secondary_mid_association",
        new_class_name="LocationSecondaryMIDLink",
        new_tablename="location_secondary_mid_link",
    )

    return manager
