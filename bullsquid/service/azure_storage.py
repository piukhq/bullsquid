from typing import BinaryIO
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from bullsquid.service.interface import ServiceInterface


class AzureBlobStorageServiceInterface(ServiceInterface):
    def __init__(self, dsn: str):
        self.client = BlobServiceClient.from_connection_string(dsn)

    def upload_blob(self, contents: BinaryIO, *, container: str, blob: str) -> None:
        contents.seek(0)
        try:
            self.client.create_container(container)
        except ResourceExistsError:
            pass
        blob_client = self.client.get_blob_client(container=container, blob=blob)
        blob_client.upload_blob(contents)
