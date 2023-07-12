from typing import BinaryIO
from azure.storage.blob import BlobServiceClient
from bullsquid.service.interface import ServiceInterface


class AzureBlobStorageServiceInterface(ServiceInterface):
    def __init__(self, dsn: str):
        self.client = BlobServiceClient.from_connection_string(dsn)

    def upload_blob(self, contents: BinaryIO, *, container: str, blob: str) -> None:
        blob_client = self.client.get_blob_client(container=container, blob=blob)
        blob_client.upload_blob(contents)
