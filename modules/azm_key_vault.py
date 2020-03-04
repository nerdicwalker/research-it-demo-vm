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
from msrestazure.azure_exceptions import CloudError


def fetch_secret_from_key_vault(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    key_vault_name,
    key_vault_secret_name
):
    "Fetch a secret from an Azure Key Vault"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    key_vault_data_plane_client = KeyVaultClient(credentials)
    key_vault_info = get_key_vault(azure_tenant_id, azure_client_id,
                                   azure_secret_id, subscription_id, resource_group_name, key_vault_name)
    fetch_secret = key_vault_data_plane_client.get_secret(
        key_vault_info.properties.vault_uri,
        key_vault_secret_name,
        secret_version=KeyVaultId.version_none,
    )
    return fetch_secret


def append_access_policy_to_key_vault(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    key_vault_name,
    azure_ad_user_object_id,
):
    "Append access policy to key vault (not overwriting any policy)"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    key_vault_resource = KeyVaultManagementClient(credentials, subscription_id)

    operation_kind = "add"
    properties = {
        'tenant_id': azure_tenant_id,
        'access_policies': [{
            'object_id': azure_ad_user_object_id,
            'tenant_id': azure_tenant_id,
            'permissions': {
                'secrets': ['get', 'list']
            }
        }]
    }

    try:
        append_access_policy = key_vault_resource.vaults.update_access_policy(
            resource_group_name,
            key_vault_name,
            operation_kind,
            properties,
            custom_headers=None,
            raw=False,
            polling=True,
        )
    except CloudError as ex:
        print(ex)


def get_key_vault(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    key_vault_name
):
    ""
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    key_vault_resource = KeyVaultManagementClient(credentials, subscription_id)
    key_vault_result = key_vault_resource.vaults.get(
        resource_group_name, key_vault_name, custom_headers=None, raw=False
    )
    return key_vault_result


def create_secret_in_key_vault(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    key_vault_name,
    key_vault_secret_name,
    key_vault_secret_value
):
    "Create an Azure Key Vault Secret"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    key_vault_data_plane_client = KeyVaultClient(credentials)
    key_vault_info = get_key_vault(azure_tenant_id, azure_client_id,
                                   azure_secret_id, subscription_id, resource_group_name, key_vault_name)

    key_vault_secret_bundle = key_vault_data_plane_client.set_secret(
        key_vault_info.properties.vault_uri,
        key_vault_secret_name,
        key_vault_secret_value,
    )


def create_key_vault(
    resource_group_name,
    key_vault_name,
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    azure_object_id,
    cost_center_tag,
    service_tag,
    created_by,
    resource_location,
):
    "create Azure Key Vault"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    parameters = {
        "location": resource_location,
        "tags": {
            "costCenter": cost_center_tag,
            "service": service_tag,
            "createdBy": created_by,
        },
        "properties": {
            "sku": {"name": "standard"},
            "tenant_id": azure_tenant_id,
            "access_policies": [
                {
                    "object_id": azure_object_id,
                    "tenant_id": azure_tenant_id,
                    "permissions": {"keys": ["all"], "secrets": ["all"]},
                }
            ],
        },
    }
    key_vault_resource = KeyVaultManagementClient(credentials, subscription_id)
    create_the_keyvault = key_vault_resource.vaults.create_or_update(
        resource_group_name,
        key_vault_name,
        parameters,
        custom_headers=None,
        raw=False,
        polling=True,
    )
    create_the_keyvault.result()
