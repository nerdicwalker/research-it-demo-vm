from modules import azm_credentials

import os
import time
import uuid
import json
import secrets
import requests

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import DiskCreateOption
from azure.mgmt.compute.models import ResourceIdentityType
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.keyvault import KeyVaultManagementClient
from azure.keyvault import KeyVaultAuthentication, KeyVaultClient, KeyVaultId
from azure.mgmt.resource.resources.models import DeploymentMode
from msrestazure.azure_exceptions import CloudError


def run_command_in_vm(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    virtual_machine_name,
    script
):
    "Run a (dropped) script in a VM."
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id,
        azure_client_id,
        azure_secret_id
    )
    vm_resource = ComputeManagementClient(credentials, subscription_id)

    run_command_parameters = {
        'command_id': 'RunPowerShellScript',
        'script': [
            script
        ]
    }

    run_command_in_vm = vm_resource.virtual_machines.run_command(
        resource_group_name,
        virtual_machine_name,
        run_command_parameters,
        custom_headers=None,
        raw=False,
        polling=True)

    run_command_in_vm.wait()


def create_virtual_machine_data_disk(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    cost_center_tag,
    service_tag,
    created_by,
    resource_group_name,
    virtual_machine_name,
    virtual_machine_data_disk_location,
    virtual_machine_data_disk_name,
    virtual_machine_data_disk_size
):
    "Create a new data disk."
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    client_resource = ComputeManagementClient(credentials, subscription_id)

    disk_params = {
        'location': virtual_machine_data_disk_location,
        'tags': {
            "costCenter": cost_center_tag,
            "sevice": service_tag,
            "createdBy": created_by
        },
        "sku": {
            "name": "StandardSSD_LRS"
        },
        'disk_size_gb': virtual_machine_data_disk_size,
        'creation_data': {
            'create_option': DiskCreateOption.empty
        }
    }

    async_disk_creation = client_resource.disks.create_or_update(
        resource_group_name,
        virtual_machine_data_disk_name,
        disk_params,
        custom_headers=None,
        raw=False,
        polling=True
    )
    virtual_machine_data_disk_info = async_disk_creation.result()
    return virtual_machine_data_disk_info


def attach_virtual_machine_data_disk(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_location,
    resource_group_name,
    virtual_machine_name,
    virtual_machine_data_disk_name,
    virtual_machine_data_disk_lun,
    virtual_machine_data_disk_id
):
    "Attach a data disk to virtual machine."
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    client_resource = ComputeManagementClient(credentials, subscription_id)

    virtual_machine = client_resource.virtual_machines.get(
        resource_group_name,
        virtual_machine_name
    )

    virtual_machine.storage_profile.data_disks.append({
        'lun': virtual_machine_data_disk_lun,
        'name': virtual_machine_data_disk_name,
        'create_option': DiskCreateOption.attach,
        'managed_disk': {
            'id': virtual_machine_data_disk_id
        }
    })
    async_disk_attach = client_resource.virtual_machines.create_or_update(
        resource_group_name,
        virtual_machine.name,
        virtual_machine
    )
    async_disk_attach.wait()


def get_virtual_machine_info(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    virtual_machine_name
):
    "Get current state of the virtual machine."

    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    client_resource = ComputeManagementClient(credentials, subscription_id)

    try:
        vm_info = client_resource.virtual_machines.get(
            resource_group_name, virtual_machine_name, expand="instanceView",
        )
        return vm_info
    except:
        print(
            f"Virtual Machine: {virtual_machine_name} not found in resource group {resource_group_name}."
        )


def deploy_virtual_machine_from_arm_template(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    virtual_machine_location,
    network_interface_name,
    network_security_group_name,
    virtual_network_name,
    virtual_machine_name,
    virtual_machine_size,
    admin_user_name,
    admin_password,
    custom_extension_timestamp,
    custom_extension_command_to_execute,
    custom_extension_file_uris,
    deployment_name,
    public_ip_address_name,
    cost_center_tag,
    service_tag,
    created_by,
    image_publisher,
    image_offer,
    image_sku,
    image_version,
    virtual_machine_deployment_template
):
    "Deploy Azure Virtual Machine with an ARM template file and adjustable parameters"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    client_resource = ResourceManagementClient(credentials, subscription_id)

    with open(virtual_machine_deployment_template, "r") as deployment_template_file:
        deployment_template = json.load(deployment_template_file)

    deployment_parameters = {
        "location": virtual_machine_location,
        "networkInterfaceName": network_interface_name,
        "networkSecurityGroupName": network_security_group_name,
        "networkSecurityGroupRules": [
            {
                "name": "RDP",
                "properties": {
                    "priority": 300,
                    "protocol": "TCP",
                    "access": "Allow",
                    "direction": "Inbound",
                    "sourceAddressPrefix": "*",
                    "sourcePortRange": "*",
                    "destinationAddressPrefix": "*",
                    "destinationPortRange": "3389",
                }
            }
        ],
        "subnetName": "default",
        "publicIpAddressId": "/subscriptions/"
        + subscription_id
        + "/resourceGroups/"
        + resource_group_name
        + "/providers/Microsoft.Network/publicIPAddresses/"
        + public_ip_address_name,
        "virtualNetworkName": virtual_network_name,
        "addressPrefixes": ["10.0.2.0/24"],
        "subnets": [
            {"name": "default", "properties": {"addressPrefix": "10.0.2.0/24"}}
        ],
        "virtualMachineName": virtual_machine_name,
        "osDiskType": "StandardSSD_LRS",
        "virtualMachineSize": virtual_machine_size,
        "adminUsername": admin_user_name,
        "adminPassword": admin_password,
        "costCenter": cost_center_tag,
        "service": service_tag,
        "createdBy": created_by,
        "imagePublisher": image_publisher,
        "imageOffer": image_offer,
        "imageSku": image_sku,
        "imageVersion": image_version,
        "customExtensionTimestamp": custom_extension_timestamp,
        "customExtensionCommandToExecute": custom_extension_command_to_execute,
        "customExtensionFileUris": custom_extension_file_uris

    }

    deployment_parameters = {k: {"value": v}
                             for k, v in deployment_parameters.items()}

    deployment_properties = {
        "mode": DeploymentMode.incremental,
        "template": deployment_template,
        "parameters": deployment_parameters,
    }

    try:
        deployment_async_operation = client_resource.deployments.create_or_update(
            resource_group_name, str(deployment_name), deployment_properties
        )
        deployment_async_operation.wait()
    except CloudError as ex:
        print(ex)


def deploy_virtual_machine_from_arm_template_with_custom_image(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    virtual_machine_location,
    network_interface_name,
    network_security_group_name,
    virtual_network_name,
    virtual_machine_name,
    virtual_machine_size,
    admin_user_name,
    admin_password,
    custom_extension_timestamp,
    custom_extension_command_to_execute,
    custom_extension_file_uris,
    deployment_name,
    public_ip_address_name,
    cost_center_tag,
    service_tag,
    created_by,
    image_reference,
    virtual_machine_deployment_template
):
    "Deploy Azure Virtual Machine with an ARM template file and adjustable parameters"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    client_resource = ResourceManagementClient(credentials, subscription_id)

    with open(virtual_machine_deployment_template, "r") as deployment_template_file:
        deployment_template = json.load(deployment_template_file)

    deployment_parameters = {
        "location": virtual_machine_location,
        "networkInterfaceName": network_interface_name,
        "networkSecurityGroupName": network_security_group_name,
        "networkSecurityGroupRules": [
            {
                "name": "RDP",
                "properties": {
                    "priority": 300,
                    "protocol": "TCP",
                    "access": "Allow",
                    "direction": "Inbound",
                    "sourceAddressPrefix": "*",
                    "sourcePortRange": "*",
                    "destinationAddressPrefix": "*",
                    "destinationPortRange": "3389",
                }
            }
        ],
        "subnetName": "default",
        "publicIpAddressId": "/subscriptions/"
        + subscription_id
        + "/resourceGroups/"
        + resource_group_name
        + "/providers/Microsoft.Network/publicIPAddresses/"
        + public_ip_address_name,
        "virtualNetworkName": virtual_network_name,
        "addressPrefixes": ["10.0.2.0/24"],
        "subnets": [
            {"name": "default", "properties": {"addressPrefix": "10.0.2.0/24"}}
        ],
        "virtualMachineName": virtual_machine_name,
        "osDiskType": "StandardSSD_LRS",
        "virtualMachineSize": virtual_machine_size,
        "adminUsername": admin_user_name,
        "adminPassword": admin_password,
        "costCenter": cost_center_tag,
        "service": service_tag,
        "createdBy": created_by,
        "imageReference": image_reference,
        "customExtensionTimestamp": custom_extension_timestamp,
        "customExtensionCommandToExecute": custom_extension_command_to_execute,
        "customExtensionFileUris": custom_extension_file_uris

    }

    deployment_parameters = {k: {"value": v}
                             for k, v in deployment_parameters.items()}

    deployment_properties = {
        "mode": DeploymentMode.incremental,
        "template": deployment_template,
        "parameters": deployment_parameters,
    }

    try:
        deployment_async_operation = client_resource.deployments.create_or_update(
            resource_group_name, str(deployment_name), deployment_properties
        )
        deployment_async_operation.wait()
    except CloudError as ex:
        print(ex)


def deploy_virtual_machine_from_arm_template_with_custom_image_and_post_install_script(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    virtual_machine_location,
    network_interface_name,
    network_security_group_name,
    virtual_network_name,
    virtual_machine_name,
    virtual_machine_size,
    admin_user_name,
    admin_password,
    deployment_name,
    public_ip_address_name,
    custom_extension_timestamp,
    custom_extension_command_to_execute,
    custom_extension_storage_account_name,
    custom_extension_storage_account_key,
    image_publisher,
    image_offer,
    image_sku,
    image_version,
    cost_center_tag,
    service_tag,
    created_by,
    virtual_machine_deployment_template
):
    "Deploy Azure Virtual Machine with an ARM template file and adjustable parameters"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    client_resource = ResourceManagementClient(credentials, subscription_id)

    with open(virtual_machine_deployment_template, "r") as deployment_template_file:
        deployment_template = json.load(deployment_template_file)

    deployment_parameters = {
        "location": virtual_machine_location,
        "networkInterfaceName": network_interface_name,
        "networkSecurityGroupName": network_security_group_name,
        "networkSecurityGroupRules": [
            {
                "name": "RDP",
                "properties": {
                    "priority": 300,
                    "protocol": "TCP",
                    "access": "Allow",
                    "direction": "Inbound",
                    "sourceAddressPrefix": "*",
                    "sourcePortRange": "*",
                    "destinationAddressPrefix": "*",
                    "destinationPortRange": "3389",
                },
            }
        ],
        "subnetName": "default",
        "publicIpAddressId": "/subscriptions/"
        + subscription_id
        + "/resourceGroups/"
        + resource_group_name
        + "/providers/Microsoft.Network/publicIPAddresses/"
        + public_ip_address_name,
        "virtualNetworkName": virtual_network_name,
        "addressPrefixes": ["10.0.0.0/24"],
        "subnets": [
            {"name": "default", "properties": {"addressPrefix": "10.0.0.0/24"}}
        ],
        "virtualMachineName": virtual_machine_name,
        "virtualMachineRG": "vre-maxqda-o-rg",
        "osDiskType": "StandardSSD_LRS",
        "virtualMachineSize": virtual_machine_size,
        "adminUsername": admin_user_name,
        "adminPassword": admin_password,
        "storageAccountName": custom_extension_storage_account_name,
        "storageAccountKey": custom_extension_storage_account_key,
        "customExtensionTimestamp": custom_extension_timestamp,
        "commandToExecute": custom_extension_command_to_execute,
        "imagePublisher": image_publisher,
        "imageOffer": image_offer,
        "imageSku": image_sku,
        "imageVersion": image_version,
        "costCenter": cost_center_tag,
        "service": service_tag,
        "createdBy": created_by,
    }

    deployment_parameters = {k: {"value": v}
                             for k, v in deployment_parameters.items()}

    deployment_properties = {
        "mode": DeploymentMode.incremental,
        "template": deployment_template,
        "parameters": deployment_parameters,
    }

    deployment_async_operation = client_resource.deployments.create_or_update(
        resource_group_name, str(deployment_name), deployment_properties
    )
    deployment_async_operation.wait()


def deploy_windows_virtual_machine_from_arm_template_with_custom_image_and_post_install_script(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    virtual_machine_location,
    network_interface_name,
    network_security_group_name,
    virtual_network_name,
    virtual_machine_name,
    virtual_machine_size,
    admin_user_name,
    admin_password,
    deployment_name,
    public_ip_address_name,
    custom_extension_timestamp,
    custom_extension_command_to_execute,
    custom_extension_storage_account_name,
    custom_extension_storage_account_key,
    image_publisher,
    image_offer,
    image_sku,
    image_version,
    cost_center_tag,
    service_tag,
    created_by,
    virtual_machine_deployment_template
):
    "Deploy Azure Virtual Machine with an ARM template file and adjustable parameters"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    client_resource = ResourceManagementClient(credentials, subscription_id)

    with open(virtual_machine_deployment_template, "r") as deployment_template_file:
        deployment_template = json.load(deployment_template_file)

    deployment_parameters = {
        "location": virtual_machine_location,
        "networkInterfaceName": network_interface_name,
        "networkSecurityGroupName": network_security_group_name,
        "networkSecurityGroupRules": [
            {
                "name": "RDP",
                "properties": {
                    "priority": 300,
                    "protocol": "TCP",
                    "access": "Allow",
                    "direction": "Inbound",
                    "sourceAddressPrefix": "*",
                    "sourcePortRange": "*",
                    "destinationAddressPrefix": "*",
                    "destinationPortRange": "3389",
                },
            }
        ],
        "subnetName": "default",
        "publicIpAddressId": "/subscriptions/"
        + subscription_id
        + "/resourceGroups/"
        + resource_group_name
        + "/providers/Microsoft.Network/publicIPAddresses/"
        + public_ip_address_name,
        "virtualNetworkName": virtual_network_name,
        "addressPrefixes": ["10.0.0.0/24"],
        "subnets": [
            {"name": "default", "properties": {"addressPrefix": "10.0.0.0/24"}}
        ],
        "virtualMachineName": virtual_machine_name,
        "virtualMachineRG": "vre-maxqda-o-rg",
        "osDiskType": "StandardSSD_LRS",
        "virtualMachineSize": virtual_machine_size,
        "adminUsername": admin_user_name,
        "adminPassword": admin_password,
        "storageAccountName": custom_extension_storage_account_name,
        "storageAccountKey": custom_extension_storage_account_key,
        "customExtensionTimestamp": custom_extension_timestamp,
        "commandToExecute": custom_extension_command_to_execute,
        "imagePublisher": image_publisher,
        "imageOffer": image_offer,
        "imageSku": image_sku,
        "imageVersion": image_version,
        "costCenter": cost_center_tag,
        "service": service_tag,
        "createdBy": created_by,
    }

    deployment_parameters = {k: {"value": v}
                             for k, v in deployment_parameters.items()}

    deployment_properties = {
        "mode": DeploymentMode.incremental,
        "template": deployment_template,
        "parameters": deployment_parameters,
    }

    deployment_async_operation = client_resource.deployments.create_or_update(
        resource_group_name, str(deployment_name), deployment_properties
    )
    deployment_async_operation.wait()


def deploy_linux_virtual_machine_from_arm_template_with_custom_image_and_post_install_script(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    virtual_machine_location,
    network_interface_name,
    network_security_group_name,
    virtual_network_name,
    virtual_machine_name,
    virtual_machine_size,
    admin_user_name,
    admin_password,
    deployment_name,
    public_ip_address_name,
    custom_extension_timestamp,
    custom_extension_command_to_execute,
    custom_extension_storage_account_name,
    custom_extension_storage_account_key,
    image_publisher,
    image_offer,
    image_sku,
    image_version,
    cost_center_tag,
    service_tag,
    created_by,
    virtual_machine_deployment_template
):
    "Deploy Azure Virtual Machine with an ARM template file and adjustable parameters"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    client_resource = ResourceManagementClient(credentials, subscription_id)

    with open(virtual_machine_deployment_template, "r") as deployment_template_file:
        deployment_template = json.load(deployment_template_file)

    deployment_parameters = {
        "location": virtual_machine_location,
        "networkInterfaceName": network_interface_name,
        "networkSecurityGroupName": network_security_group_name,
        "networkSecurityGroupRules": [
            {
                "name": "RDP",
                "properties": {
                    "priority": 300,
                    "protocol": "TCP",
                    "access": "Allow",
                    "direction": "Inbound",
                    "sourceAddressPrefix": "*",
                    "sourcePortRange": "*",
                    "destinationAddressPrefix": "*",
                    "destinationPortRange": "22",
                },
            }
        ],
        "subnetName": "default",
        "publicIpAddressId": "/subscriptions/"
        + subscription_id
        + "/resourceGroups/"
        + resource_group_name
        + "/providers/Microsoft.Network/publicIPAddresses/"
        + public_ip_address_name,
        "virtualNetworkName": virtual_network_name,
        "addressPrefixes": ["10.0.0.0/24"],
        "subnets": [
            {"name": "default", "properties": {"addressPrefix": "10.0.0.0/24"}}
        ],
        "virtualMachineName": virtual_machine_name,
        "osDiskType": "StandardSSD_LRS",
        "virtualMachineSize": virtual_machine_size,
        "adminUsername": admin_user_name,
        "adminPassword": admin_password,
        "storageAccountName": custom_extension_storage_account_name,
        "storageAccountKey": custom_extension_storage_account_key,
        "customExtensionTimestamp": custom_extension_timestamp,
        "commandToExecute": custom_extension_command_to_execute,
        "imagePublisher": image_publisher,
        "imageOffer": image_offer,
        "imageSku": image_sku,
        "imageVersion": image_version,
        "costCenter": cost_center_tag,
        "service": service_tag,
        "createdBy": created_by,
    }

    deployment_parameters = {k: {"value": v}
                             for k, v in deployment_parameters.items()}

    deployment_properties = {
        "mode": DeploymentMode.incremental,
        "template": deployment_template,
        "parameters": deployment_parameters,
    }

    deployment_async_operation = client_resource.deployments.create_or_update(
        resource_group_name, str(deployment_name), deployment_properties
    )
    deployment_async_operation.wait()


def deploy_linux_virtual_machine_from_arm_template_with_custom_image_and_post_install_script_file_uris(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    virtual_machine_location,
    network_interface_name,
    network_security_group_name,
    virtual_network_name,
    virtual_machine_name,
    virtual_machine_size,
    admin_user_name,
    admin_password,
    deployment_name,
    public_ip_address_name,
    custom_extension_timestamp,
    custom_extension_command_to_execute,
    custom_extension_storage_account_name,
    custom_extension_storage_account_key,
    image_publisher,
    image_offer,
    image_sku,
    image_version,
    cost_center_tag,
    service_tag,
    created_by,
    virtual_machine_deployment_template,
    file_uris
):
    "Deploy Azure Virtual Machine with an ARM template file and adjustable parameters"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    client_resource = ResourceManagementClient(credentials, subscription_id)

    with open(virtual_machine_deployment_template, "r") as deployment_template_file:
        deployment_template = json.load(deployment_template_file)

    deployment_parameters = {
        "location": virtual_machine_location,
        "networkInterfaceName": network_interface_name,
        "networkSecurityGroupName": network_security_group_name,
        "networkSecurityGroupRules": [
            {
                "name": "RDP",
                "properties": {
                    "priority": 300,
                    "protocol": "TCP",
                    "access": "Allow",
                    "direction": "Inbound",
                    "sourceAddressPrefix": "*",
                    "sourcePortRange": "*",
                    "destinationAddressPrefix": "*",
                    "destinationPortRange": "22",
                },
            }
        ],
        "subnetName": "default",
        "publicIpAddressId": "/subscriptions/"
        + subscription_id
        + "/resourceGroups/"
        + resource_group_name
        + "/providers/Microsoft.Network/publicIPAddresses/"
        + public_ip_address_name,
        "virtualNetworkName": virtual_network_name,
        "addressPrefixes": ["10.0.0.0/24"],
        "subnets": [
            {"name": "default", "properties": {"addressPrefix": "10.0.0.0/24"}}
        ],
        "virtualMachineName": virtual_machine_name,
        "osDiskType": "StandardSSD_LRS",
        "virtualMachineSize": virtual_machine_size,
        "adminUsername": admin_user_name,
        "adminPassword": admin_password,
        "storageAccountName": custom_extension_storage_account_name,
        "storageAccountKey": custom_extension_storage_account_key,
        "customExtensionTimestamp": custom_extension_timestamp,
        "commandToExecute": custom_extension_command_to_execute,
        "imagePublisher": image_publisher,
        "imageOffer": image_offer,
        "imageSku": image_sku,
        "imageVersion": image_version,
        "costCenter": cost_center_tag,
        "service": service_tag,
        "createdBy": created_by,
        "fileUris": file_uris
    }

    deployment_parameters = {k: {"value": v}
                             for k, v in deployment_parameters.items()}

    deployment_properties = {
        "mode": DeploymentMode.incremental,
        "template": deployment_template,
        "parameters": deployment_parameters,
    }

    deployment_async_operation = client_resource.deployments.create_or_update(
        resource_group_name, str(deployment_name), deployment_properties
    )
    deployment_async_operation.wait()


def deploy_windows_virtual_machine_from_arm_template_with_custom_image_and_post_install_script_file_uris(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    resource_group_name,
    virtual_machine_location,
    network_interface_name,
    network_security_group_name,
    virtual_network_name,
    virtual_machine_name,
    virtual_machine_size,
    admin_user_name,
    admin_password,
    deployment_name,
    public_ip_address_name,
    custom_extension_timestamp,
    custom_extension_command_to_execute,
    custom_extension_storage_account_name,
    custom_extension_storage_account_key,
    image_publisher,
    image_offer,
    image_sku,
    image_version,
    cost_center_tag,
    service_tag,
    created_by,
    virtual_machine_deployment_template,
    file_uris
):
    "Deploy Azure Virtual Machine with an ARM template file and adjustable parameters"
    credentials = azm_credentials.get_azure_credentials(
        azure_tenant_id, azure_client_id, azure_secret_id
    )
    client_resource = ResourceManagementClient(credentials, subscription_id)

    with open(virtual_machine_deployment_template, "r") as deployment_template_file:
        deployment_template = json.load(deployment_template_file)

    deployment_parameters = {
        "location": virtual_machine_location,
        "networkInterfaceName": network_interface_name,
        "networkSecurityGroupName": network_security_group_name,
        "networkSecurityGroupRules": [
            {
                "name": "RDP",
                "properties": {
                    "priority": 300,
                    "protocol": "TCP",
                    "access": "Allow",
                    "direction": "Inbound",
                    "sourceAddressPrefix": "*",
                    "sourcePortRange": "*",
                    "destinationAddressPrefix": "*",
                    "destinationPortRange": "3389",
                },
            }
        ],
        "subnetName": "default",
        "publicIpAddressId": "/subscriptions/"
        + subscription_id
        + "/resourceGroups/"
        + resource_group_name
        + "/providers/Microsoft.Network/publicIPAddresses/"
        + public_ip_address_name,
        "virtualNetworkName": virtual_network_name,
        "addressPrefixes": ["10.0.0.0/24"],
        "subnets": [
            {"name": "default", "properties": {"addressPrefix": "10.0.0.0/24"}}
        ],
        "virtualMachineName": virtual_machine_name,
        "virtualMachineRG": "vre-maxqda-o-rg",
        "osDiskType": "StandardSSD_LRS",
        "virtualMachineSize": virtual_machine_size,
        "adminUsername": admin_user_name,
        "adminPassword": admin_password,
        "storageAccountName": custom_extension_storage_account_name,
        "storageAccountKey": custom_extension_storage_account_key,
        "customExtensionTimestamp": custom_extension_timestamp,
        "commandToExecute": custom_extension_command_to_execute,
        "imagePublisher": image_publisher,
        "imageOffer": image_offer,
        "imageSku": image_sku,
        "imageVersion": image_version,
        "costCenter": cost_center_tag,
        "service": service_tag,
        "createdBy": created_by,
        "fileUris": file_uris
    }

    deployment_parameters = {k: {"value": v}
                             for k, v in deployment_parameters.items()}

    deployment_properties = {
        "mode": DeploymentMode.incremental,
        "template": deployment_template,
        "parameters": deployment_parameters,
    }

    deployment_async_operation = client_resource.deployments.create_or_update(
        resource_group_name, str(deployment_name), deployment_properties
    )
    deployment_async_operation.wait()
