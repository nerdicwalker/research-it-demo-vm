from modules import azm_resource_group
from modules import azm_virtual_machine
from modules import azm_key_vault
from modules import azm_general
from modules import azm_ip
from modules import azm_credentials
from modules import azm_storage_account
from modules import azm_jumpcloud

import os
import sys
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

azure_tenant_id = os.environ.get("AZURE_TENANT_ID")
azure_object_id = os.environ.get("AZURE_OBJECT_ID")
azure_client_id = os.environ.get("AZURE_CLIENT_ID")
azure_secret_id = os.environ.get("AZURE_SECRET_ID")
subscription_id = os.environ.get("AZURE_SUBSCR_ID")
cost_center_tag = os.environ.get("COST_CENTER_TAG")
service_tag = os.environ.get("SERVICE_TAG")
created_by = os.environ.get("CREATED_BY_TAG")
admin_of_the_virtual_machine = os.environ.get("ADMIN_OF_THE_VIRTUAL_MACHINE")


def main():
    ""
    resource_group_name = os.environ.get("RESOURCE_GROUP_NAME")
    resource_group_name_prefix = os.environ.get("RESOURCE_GROUP_NAME_PREFIX")
    resource_location = os.environ.get("RESOURCE_LOCATION")
    virtual_machine_size = os.environ.get("VIRTUAL_MACHINE_SIZE")
    custom_extension_storage_account_name = os.environ.get(
        "SCRIPT_STORAGE_ACCOUNT_NAME")
    custom_extension_storage_account_container = os.environ.get(
        "SCRIPT_STORAGE_ACCOUNT_CONTAINER")
    custom_extension_storage_account_resource_group_name = os.environ.get(
        "SCRIPT_RESOURCE_GROUP_STORAGE_ACCOUNT_NAME")
    automation_resources_resource_group = os.environ.get(
        "AUTOMATION_RESOURCES_RESOURCE_GROUP_NAME")
    automation_resources_key_vault_name = os.environ.get(
        "AUTOMATION_RESOURCES_KEY_VAULT_NAME")
    automation_resources_key_vault_secret_name = os.environ.get(
        "AUTOMATION_RESOURCES_KEY_VAULT_SECRET_NAME")
    jumpcloud_agent_key_vault_name = os.environ.get(
        "JUMPCLOUD_AGENT_KEY_VAULT_NAME")
    jumpcloud_agent_key_vault_secret_name = os.environ.get(
        "JUMPCLOUD_AGENT_KEY_VAULT_SECRET_NAME")
    jumpcloud_group_name = os.environ.get(
        "JUMP_CLOUD_GROUP_NAME")
    unique_number = azm_general.create_unique_number()
    unique_id = str(azm_general.create_uuid())

    if azure_tenant_id is None:
        exit(print("Missing environment variable 'AZURE_TENANT_ID'. Can't continue. Sorry. Can't continue. Sorry."))

    if azure_object_id is None:
        exit(print("Missing environment variable 'AZURE_OBJECT_ID. Can't continue. Sorry. Can't continue. Sorry."))

    if azure_client_id is None:
        exit(print("Missing environment variable 'AZURE_CLIENT_ID'. Can't continue. Sorry. Can't continue. Sorry."))

    if azure_secret_id is None:
        exit(print("Missing environment variable 'AZURE_SECRET_ID'. Can't continue. Sorry. Can't continue. Sorry."))

    if subscription_id is None:
        exit(print("Missing environment variable 'AZURE_SUBSCR_ID'. Can't continue. Sorry. Can't continue. Sorry."))

    if cost_center_tag is None:
        exit(print("Missing environment variable 'COST_CENTER_TAG'. Can't continue. Sorry. Can't continue. Sorry."))

    if service_tag is None:
        exit(print("Missing  environment variable 'SERVICE_TAG'. Can't continue. Sorry. Can't continue. Sorry."))

    if created_by is None:
        exit(print("Missing environment variable 'CREATED_BY_TAG'. Can't continue. Sorry. Can't continue. Sorry."))

    if custom_extension_storage_account_name is None:
        exit(print("Missing environment variable 'SCRIPT_STORAGE_ACCOUNT_NAME'. Can't continue. Sorry. Can't continue. Sorry."))

    if custom_extension_storage_account_container is None:
        exit(print("Missing environment variable 'SCRIPT_STORAGE_ACCOUNT_CONTAINER'. Can't continue. Sorry. Can't continue. Sorry."))

    if custom_extension_storage_account_resource_group_name is None:
        exit(print("Missing environment variable 'SCRIPT_RESOURCE_GROUP_STORAGE_ACCOUNT_NAME'. Can't continue. Sorry. Can't continue. Sorry."))

    if automation_resources_resource_group is None:
        exit(print("Missing environment variable 'AUTOMATION_RESOURCES_RESOURCE_GROUP_NAME'. Can't continue. Sorry. Can't continue. Sorry."))

    if automation_resources_key_vault_name is None:
        exit(print("Missing environment variable 'AUTOMATION_RESOURCES_KEY_VAULT_NAME'. Can't continue. Sorry. Can't continue. Sorry."))

    if automation_resources_key_vault_secret_name is None:
        exit(print("Missing environment variable 'AUTOMATION_RESOURCES_KEY_VAULT_SECRET_NAME'. Can't continue. Sorry. Can't continue. Sorry."))

    if jumpcloud_group_name is None:
        exit(print("Missing environment variable 'JUMP_CLOUD_GROUP_NAME'. Can't continue. Sorry. Can't continue. Sorry."))

    if resource_location is None:
        resource_location = "westeurope"

    if resource_group_name is None:
        if resource_group_name_prefix is None:
            exit(print("Missing RESOURCE_GROUP_NAME_PREFIX"))
        # create Azure Resource Group
        resource_group_name = (
            resource_group_name_prefix + "-" + unique_number + "-" + unique_id + "-rg"
        )

        print(f"Creating Azure Resource Group {resource_group_name}.")
        azm_resource_group.create_azure_resource_group(azure_tenant_id, azure_client_id, azure_secret_id,
                                                       subscription_id, resource_location, cost_center_tag, service_tag, created_by, resource_group_name)

    # create Azure Key Vault
    key_vault_name = "kv" + unique_number
    print(
        f"Creating an Azure Key Vault {key_vault_name} in resource group {resource_group_name}.")
    azm_key_vault.create_key_vault(
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
    )

    # append access policy to Azure Key Vault for Azure AD user object id (f.e. admin of the Virtual Machine)
    if admin_of_the_virtual_machine is None:
        print("Missing ADMIN_OF_THE_VIRTUAL_MACHINE. You will need to add the key vault access policy manually in order to fetch the VM credentials.")
    else:
        print(
            f"Appending access policy with object id {admin_of_the_virtual_machine} to key vault {key_vault_name}.")
        # here the code to check if the admin_of_the_virtual_machine is a valid object id.. #
        azure_ad_user_object_id = admin_of_the_virtual_machine
        azm_key_vault.append_access_policy_to_key_vault(
            azure_tenant_id,
            azure_client_id,
            azure_secret_id,
            subscription_id,
            resource_group_name,
            key_vault_name,
            azure_ad_user_object_id
        )

    # create Azure Public IP Address
    public_ip_address_name = "pip" + unique_number
    print(
        f"Creating an Azure Public IP address."
    )
    azm_ip.create_public_ip_address(
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
    )

    virtual_machine_location = resource_location
    network_interface_name = "nic" + unique_number
    network_security_group_name = "nsg" + unique_number
    virtual_network_name = "vnet" + unique_number
    virtual_machine_name = "vm" + unique_number
    if virtual_machine_size is None:
        print("No environment variable 'VIRTUAL_MACHINE_SIZE' found, defaulting to a Standard_D2s_v3 size VM.")
        virtual_machine_size = "Standard_D2s_v3"
    deployment_name = "deployment" + unique_number
    admin_user_name = "admin" + unique_number
    admin_password = azm_general.generate_safe_password(32)
    custom_extension_timestamp = unique_number
    custom_extension_storage_account_info = azm_storage_account.get_storage_account_key(
        azure_tenant_id,
        azure_client_id,
        azure_secret_id,
        subscription_id,
        custom_extension_storage_account_resource_group_name,
        custom_extension_storage_account_name,
    )
    custom_extension_storage_account_info = {
        v.key_name: v.value for v in custom_extension_storage_account_info.keys
    }
    custom_extension_storage_account_key = custom_extension_storage_account_info["key1"]

    # add virtual machine credentials (username/password) to key vault
    print(
        f"Adding virtual machine {virtual_machine_name} credentials to the key vault {key_vault_name}."
    )
    azm_key_vault.create_secret_in_key_vault(
        azure_tenant_id,
        azure_client_id,
        azure_secret_id,
        subscription_id,
        resource_group_name,
        key_vault_name,
        admin_user_name,
        admin_password
    )

    # deploy Azure Virtual Machine
    #image_publisher = "microsoft-dsvm"
    #image_offer = "dsvm-windows"
    #image_sku = "server-2016"
    #image_version = "latest"
    image_publisher = "MicrosoftWindowsServer"
    image_offer = "WindowsServer"
    image_sku = "2019-Datacenter"
    image_version = "latest"
    virtual_machine_deployment_template = "./templates/create-windows-vm-from-marketplace-image-custom-script-extension-file-uris.json"

    file_uris = []
    # fetch script names
    file_uris_scripts = azm_storage_account.get_files_from_container(
        azure_tenant_id,
        azure_client_id,
        azure_secret_id,
        subscription_id,
        custom_extension_storage_account_resource_group_name,
        custom_extension_storage_account_name,
        custom_extension_storage_account_container
    )
    for script in file_uris_scripts:
        if script.startswith('windows'):
            file_uris.append(
                f"https://{custom_extension_storage_account_name}.blob.core.windows.net/{custom_extension_storage_account_container}/{script}")
        else:
            continue

    custom_extension_command_to_execute = (
        f"powershell -ExecutionPolicy Unrestricted -File windows\post-install-script.ps1"
    )

    # deploy windows virtual machine
    print(f"Deploying virtual machine {virtual_machine_name}.")
    azm_virtual_machine.deploy_windows_virtual_machine_from_arm_template_with_custom_image_and_post_install_script_file_uris(
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
    )

    # create additional (data) disk
    virtual_machine_data_disk_location = resource_location
    virtual_machine_data_disk_size = 30
    virtual_machine_data_disk_name = f"{virtual_machine_name}_DataDisk_1"
    print(f"Creating additional (data) disk.")
    virtual_machine_data_disk_info = azm_virtual_machine.create_virtual_machine_data_disk(
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
    )

    # attach additional (data) disk
    virtual_machine_data_disk_lun = 9
    virtual_machine_data_disk_id = virtual_machine_data_disk_info.id
    print(
        f"Attaching additional data disk {virtual_machine_data_disk_name} to virtual machine {virtual_machine_name}.")
    azm_virtual_machine.attach_virtual_machine_data_disk(
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
    )

    # initialize and format data disk
    print(
        f"Initializing and formatting additional data disk {virtual_machine_data_disk_name}.")
    script = "powershell -ExecutionPolicy Unrestricted -File 'c:\installation-sources\scripts\init-and-format-data-disk.ps1'"
    azm_virtual_machine.run_command_in_vm(
        azure_tenant_id,
        azure_client_id,
        azure_secret_id,
        subscription_id,
        resource_group_name,
        virtual_machine_name,
        script
    )

    # install JumpCloud agent software into virtual machine
    print(
        f"Fetching Azure Virtual Machine {virtual_machine_name} system identity.")
    virtual_machine_system_info = azm_virtual_machine.get_virtual_machine_info(
        azure_tenant_id,
        azure_client_id,
        azure_secret_id,
        subscription_id,
        resource_group_name,
        virtual_machine_name
    )
    virtual_machine_system_id = virtual_machine_system_info.identity.principal_id

    print(
        f"Appending Azure Virtual Machine {virtual_machine_name} system identity to Azure Key Vault {jumpcloud_agent_key_vault_name}.")
    azm_key_vault.append_access_policy_to_key_vault(
        azure_tenant_id,
        azure_client_id,
        azure_secret_id,
        subscription_id,
        automation_resources_resource_group,
        jumpcloud_agent_key_vault_name,
        virtual_machine_system_id
    )

    print(
        f"Installing JumpCloud agent on Azure Virtual Machine {virtual_machine_name}.")
    command = f"c:\installation-sources\scripts\install-jumpcloud-agent.ps1 -azureKeyVaultName {jumpcloud_agent_key_vault_name} -azureKeyVaultSecret {jumpcloud_agent_key_vault_secret_name}"
    script = f"powershell -ExecutionPolicy Unrestricted -File {command}"
    azm_virtual_machine.run_command_in_vm(
        azure_tenant_id,
        azure_client_id,
        azure_secret_id,
        subscription_id,
        resource_group_name,
        virtual_machine_name,
        script
    )

    # jumpcloud stuff
    print(
        f"Adding JumpCloud users to JumpCloud system {virtual_machine_name}.")
    try:
        jump_cloud_api_key = azm_jumpcloud.get_jumpcloud_api_key(
            azure_tenant_id,
            azure_client_id,
            azure_secret_id,
            subscription_id,
            automation_resources_resource_group,
            automation_resources_key_vault_name,
            automation_resources_key_vault_secret_name,
        )
        jumpcloud_group_id = azm_jumpcloud.get_jumpcloud_group_id(
            jump_cloud_api_key,
            jumpcloud_group_name
        )
        jumpcloud_system_id = azm_jumpcloud.get_jumpcloud_system_id(
            jump_cloud_api_key,
            virtual_machine_name
        )
        jumpcloud_user_list = azm_jumpcloud.get_jumpcloud_group_users(
            jump_cloud_api_key,
            jumpcloud_group_id
        )
        jumpcloud_users = []
        for item_mess in jumpcloud_user_list:
            jumpcloud_users.append(item_mess.to.id)
        azm_jumpcloud.add_users_to_system_id(
            jump_cloud_api_key,
            jumpcloud_system_id,
            jumpcloud_users
        )
    except Exception as ex:
        print('Exception:')
        print(ex)
        # exit()

    print(
        f"Removing Azure Virtual Machine {virtual_machine_name} system identity from Azure Key Vault {jumpcloud_agent_key_vault_name}.")
    azm_key_vault.append_access_policy_to_key_vault(
        azure_tenant_id,
        azure_client_id,
        azure_secret_id,
        subscription_id,
        automation_resources_resource_group,
        jumpcloud_agent_key_vault_name,
        virtual_machine_system_id
    )

    print(f"Azure Virtual Machine {virtual_machine_name} ready.")


if __name__ == "__main__":
    main()
