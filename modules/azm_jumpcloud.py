from modules import azm_key_vault
import json
import requests
import jcapiv2


def add_users_to_system_id(
    jump_cloud_api_key,
    jumpcloud_system_id,
    jumpcloud_users
):
    "Add JumpCloud users to JumpCloud system"
    for user_id in jumpcloud_users:
        data = {"op": "add", "type": "user", "id": user_id}
        jdata = json.dumps(data)
        try:
            response = requests.post(
                "https://console.jumpcloud.com/api/v2/systems/"
                + jumpcloud_system_id
                + "/associations",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "x-api-key": jump_cloud_api_key,
                },
                data=jdata,
            )

            response.raise_for_status()
        except HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"Other error occurred: {err}")
        else:
            ""
            # print("Success!")


def get_jumpcloud_system_id(
    jump_cloud_api_key,
    virtual_machine_name
):
    "Get JumpCloud system id for Virtual Machine Name"
    response = requests.get(
        "https://console.jumpcloud.com/api/systems",
        params={"q": "requests+language:python"},
        headers={
            "Accept": "application/vnd.github.v3.text-match+json",
            "Content-Type": "application/json",
            "x-api-key": jump_cloud_api_key,
        },
    )
    json_response = response.json()
    results = json_response["results"]
    for item in results:
        if item["displayName"] == virtual_machine_name:
            # print(item["displayName"], item["_id"])
            jumpcloud_system_id = item["_id"]
        else:
            continue
    return jumpcloud_system_id


def get_jumpcloud_group_users(
    jump_cloud_api_key,
    jumpcloud_group_id
):
    "Get all JumpCloud group member users"

    # Configure API key authorization: x-api-key
    configuration = jcapiv2.Configuration()
    configuration.api_key["x-api-key"] = jump_cloud_api_key
    # Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
    # configuration.api_key_prefix['x-api-key'] = 'Bearer'

    # create an instance of the API class
    api_instance = jcapiv2.UserGroupMembersMembershipApi(
        jcapiv2.ApiClient(configuration)
    )
    group_id = jumpcloud_group_id  # str | ObjectID of the User Group.
    content_type = "application/json"  # str |  (default to application/json)
    accept = "application/json"  # str |  (default to application/json)
    limit = (
        10
    )  # int | The number of records to return at once. Limited to 100. (optional) (default to 10)
    # int | The offset into the records to return. (optional) (default to 0)
    skip = 0
    x_org_id = ""  # str |  (optional) (default to )

    try:
        # List the members of a User Group
        api_response = api_instance.graph_user_group_members_list(
            group_id, content_type, accept, limit=limit, skip=skip, x_org_id=x_org_id
        )
        return api_response
    except ApiException as e:
        print(
            "Exception when calling UserGroupMembersMembershipApi->graph_user_group_members_list: %s\n"
            % e
        )


def get_jumpcloud_group_id(
    jump_cloud_api_key,
    jumpcloud_group_name
):
    "Get JumpCloud group ID"
    jumpcloud_groups = get_jumpcloud_user_groups(jump_cloud_api_key)
    for item in jumpcloud_groups:
        if item.name == jumpcloud_group_name:
            return item.id


def get_jumpcloud_user_groups(
    jump_cloud_api_key
):
    ""
    API_KEY = jump_cloud_api_key

    CONTENT_TYPE = "application/json"
    ACCEPT = "application/json"

    # Set up the configuration object with your API key for authorization
    CONFIGURATION = jcapiv2.Configuration()
    CONFIGURATION.api_key["x-api-key"] = API_KEY

    # Instantiate the API object for the group of endpoints you need to use,
    # for instance the user groups API
    API_INSTANCE = jcapiv2.UserGroupsApi(jcapiv2.ApiClient(CONFIGURATION))

    # "Make an API call to retrieve all user groups."
    try:
        user_groups = API_INSTANCE.groups_user_list(CONTENT_TYPE, ACCEPT)
        # print(user_groups)
    except ApiException as err:
        print("Exception when calling UserGroupsApi->groups_user_list: %s\n" % err)
    return user_groups


def get_jumpcloud_api_key(
    azure_tenant_id,
    azure_client_id,
    azure_secret_id,
    subscription_id,
    automation_resources_resource_group,
    automation_resources_key_vault_name,
    automation_resources_key_vault_secret_name,
):
    "fetch JumpCloud api key"
    my_secret = azm_key_vault.fetch_secret_from_key_vault(
        azure_tenant_id,
        azure_client_id,
        azure_secret_id,
        subscription_id,
        automation_resources_resource_group,
        automation_resources_key_vault_name,
        automation_resources_key_vault_secret_name,
    )
    jumpcloud_api_key = my_secret.value
    return jumpcloud_api_key
