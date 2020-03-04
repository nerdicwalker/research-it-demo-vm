from modules import azm_credentials

import os
import time
import uuid
import json
import secrets
import requests

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import ResourceIdentityType
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.keyvault import KeyVaultManagementClient
from azure.keyvault import KeyVaultAuthentication, KeyVaultClient, KeyVaultId
from azure.mgmt.resource.resources.models import DeploymentMode
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from msrestazure.azure_exceptions import CloudError


def get_storage_account_key(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    custom_extension_storage_account_resource_group_name,
    custom_extension_storage_account_name
):
    "Fetch Azure Storage Account Key"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    storage_resource = StorageManagementClient(credentials, subscription_id)
    storage_keys = storage_resource.storage_accounts.list_keys(
        custom_extension_storage_account_resource_group_name,
        custom_extension_storage_account_name,
        custom_headers=None,
        raw=False,
    )
    return storage_keys


def create_storage_account_connection_string(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    custom_extension_storage_account_resource_group_name,
    custom_extension_storage_account_name
):
    "Create the Azure Storage Account connection string for a particular Azure Storage Account"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    storage_resource = StorageManagementClient(credentials, subscription_id)
    storage_account_properties = storage_resource.storage_accounts.get_properties(
        custom_extension_storage_account_resource_group_name,
        custom_extension_storage_account_name,
        custom_headers=None,
        raw=False
    )
    storage_account_info = get_storage_account_key(
        azure_tenant_id,
        azure_client_id,
        azure_secret_id,
        subscription_id,
        custom_extension_storage_account_resource_group_name,
        custom_extension_storage_account_name
    )
    storage_account_info = {
        v.key_name: v.value for v in storage_account_info.keys
    }
    storage_account_key = storage_account_info["key1"]
    storage_account_name = storage_account_properties.name
    storage_account_connection_string = "DefaultEndpointsProtocol=https;AccountName=" + \
        storage_account_name + ";AccountKey=" + \
        storage_account_key + ";EndpointSuffix=core.windows.net"
    return storage_account_connection_string


def get_files_from_container(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    custom_extension_storage_account_resource_group_name,
    custom_extension_storage_account_name,
    custom_extension_storage_account_container
):
    "Fetch all file names from the Azure Storage Account blob container"
    custom_extension_storage_account_connection_string = create_storage_account_connection_string(
        azure_tenant_id,
        azure_client_id,
        azure_secret_id,
        subscription_id,
        custom_extension_storage_account_resource_group_name,
        custom_extension_storage_account_name
    )

    blob_service_client = BlobServiceClient.from_connection_string(
        custom_extension_storage_account_connection_string)

    container_client = blob_service_client.get_container_client(
        custom_extension_storage_account_container)
    blob_list = []
    try:
        for blob in container_client.list_blobs():
            blob_list.append(blob.name)
    except Exception as ex:
        print('Exception:')
        print(ex)
        exit()

    return blob_list
