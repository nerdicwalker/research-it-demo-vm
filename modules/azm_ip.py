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


def create_public_ip_address(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    public_ip_address_name,
    cost_center_tag,
    service_tag,
    created_by,
    resource_location
):
    "Create an Azure Public IP IP Address"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )

    client_network = NetworkManagementClient(credentials, subscription_id)

    parameters = {
        "location": resource_location,
        "tags": {
            "costCenter": cost_center_tag,
            "service": service_tag,
            "createdBy": created_by,
        },
        "type": "PublicIPAddress",
        "sku": {"name": "Standard"},
        "public_ip_allocation_method": "Static",
        "public_ip_address_version": "IPv4"
    }

    try:
        create_public_ip = client_network.public_ip_addresses.create_or_update(
            resource_group_name,
            public_ip_address_name,
            parameters,
            custom_headers=None,
            raw=False,
            polling=True,
        )
    except CloudError as ex:
        print(ex)
    except:
        print("Error")
