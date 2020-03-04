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


def get_azure_credentials(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id
):
    "Fetch Azure Credentials"
    credentials = ServicePrincipalCredentials(
        client_id=azure_client_id, secret=azure_secret_id, tenant=azure_tenant_id
    )
    return credentials
