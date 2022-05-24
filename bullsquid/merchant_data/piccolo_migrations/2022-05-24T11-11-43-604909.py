from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns import Integer, Text
from piccolo.table import Table

ID = "2022-05-24T11:11:43:604909"
VERSION = "0.71.1"
DESCRIPTION = "set default payment scheme codes and labels if fixtures are loaded"


class PaymentScheme(Table):
    slug = Text(primary_key=True)
    code = Integer(required=True, unique=False)
    label = Text(required=True)


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="", description=DESCRIPTION)

    async def run():
        await PaymentScheme.update(
            {PaymentScheme.code: 1, PaymentScheme.label: "VISA"}
        ).where(PaymentScheme.slug == "visa")

        await PaymentScheme.update(
            {PaymentScheme.code: 2, PaymentScheme.label: "MASTERCARD"}
        ).where(PaymentScheme.slug == "mastercard")

        await PaymentScheme.update(
            {PaymentScheme.code: 3, PaymentScheme.label: "AMEX"}
        ).where(PaymentScheme.slug == "amex")

    manager.add_raw(run)

    return manager
