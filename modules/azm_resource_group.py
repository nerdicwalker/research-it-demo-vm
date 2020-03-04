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


def create_azure_resource_group(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_location,
    cost_center_tag,
    service_tag,
    created_by,
    resource_group_name
):
    "create an azure resource group"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    client_resource = ResourceManagementClient(credentials, subscription_id)

    resource_group_parameters = {
        "location": resource_location,
        "tags": {
            "costCenter": cost_center_tag,
            "service": service_tag,
            "createdBy": created_by,
        },
    }

    try:
        client_resource.resource_groups.create_or_update(
            resource_group_name, resource_group_parameters
        )
    except CloudError as ex:
        print(ex)
    return resource_group_name


def get_resources_in_resource_group(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name
):
    "Get list of images."

    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    client_resource = ResourceManagementClient(credentials, subscription_id)

    resource_list = client_resource.resources.list_by_resource_group(
        resource_group_name)

    return resource_list
