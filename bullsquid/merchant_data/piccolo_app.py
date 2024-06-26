"""
Import all of the Tables subclasses in your app here, and register them with
the APP_CONFIG.
"""

import os

from piccolo.conf.apps import AppConfig, table_finder

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


APP_CONFIG = AppConfig(
    app_name="merchant_data",
    migrations_folder_path=os.path.join(CURRENT_DIRECTORY, "piccolo_migrations"),
    table_classes=table_finder(
        [
            "bullsquid.merchant_data.locations.tables",
            "bullsquid.merchant_data.psimis.tables",
            "bullsquid.merchant_data.merchants.tables",
            "bullsquid.merchant_data.payment_schemes.tables",
            "bullsquid.merchant_data.plans.tables",
            "bullsquid.merchant_data.primary_mids.tables",
            "bullsquid.merchant_data.secondary_mids.tables",
            "bullsquid.merchant_data.secondary_mid_location_links.tables",
            "bullsquid.merchant_data.comments.tables",
        ],
        exclude_imported=True,
    ),
    migration_dependencies=[],
    commands=[],
)
