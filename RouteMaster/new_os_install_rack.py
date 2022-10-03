import sys
import json
import time

from pprint import pprint
from typing import Union

import intersight

from intersight.model.server_profile import ServerProfile
#from intersight.api import server_api
from intersight.model.organization_organization_relationship import OrganizationOrganizationRelationship
#from intersight.api import organization_api
#from intersight.api import bulk_api
#from intersight.api import resourcepool_api
from intersight.api import vnic_api,resourcepool_api,bulk_api,organization_api,server_api
from intersight.model.bulk_mo_cloner import BulkMoCloner
from intersight.model.server_profile_template import ServerProfileTemplate
from intersight.model.os_answers import OsAnswers
from intersight.model.os_install import OsInstall
from intersight.model.os_install_target import OsInstallTarget
from intersight.api import os_api
from intersight.model.os_configuration_file_relationship import OsConfigurationFileRelationship
from intersight.model.os_ip_configuration import OsIpConfiguration
from intersight.model.comm_ip_v4_interface import CommIpV4Interface
from intersight.model.firmware_server_configuration_utility_distributable_relationship import \
    FirmwareServerConfigurationUtilityDistributableRelationship
from intersight.model.softwarerepository_operating_system_file_relationship import \
    SoftwarerepositoryOperatingSystemFileRelationship

import credentials

api_client = credentials.config_credentials()

# Create param dict and prompt for all values that haven't been set.
os_params = {
    'ipv4_address': None,
    'gateway': "172.20.60.1",
    'netmask': "255.255.255.0",
    'hostname': None,
    # Required Input for server form factor. options should be limited to "blade" or "rack" and will be used for pool selection. Can this be a LOV or selection?
    'server_type': None
}

for k, v in os_params.items():
    if v is None:
        inp = input(f"{k}: ")
        os_params[k] = inp

def set_organization(orgname: str) -> Union[OrganizationOrganizationRelationship, None]:
    """Set the organization based on the provided org name

    Args:
        orgname(str): The name of the organization we are looking for.

    Returns:
        OrganizationOrganizationRelationship: The org relationship of the org 
            specified by the orgname.
    """
    # Find MOID and returning instance of organization
    api_instance = organization_api.OrganizationApi(api_client)
    query_filter = "Name eq " + orgname
    query_select = "name,moid"

    try:
        org_query = api_instance.get_organization_organization_list(filter=query_filter, select=query_select)
        org_results = str(org_query.results[0]).replace("\'","\"")
        org_dict = json.loads(org_results)
        org_moid = org_dict["moid"]

        return OrganizationOrganizationRelationship(class_id="mo.MoRef",
                                                object_type="organization.Organization",
                                                moid=org_moid)
    except intersight.ApiException as e:
        print("Exception when calling OrganizationApi->get_organization_organization_list: %s\n" % e)
        sys.exit(1)

def set_profile_template(template: str) -> Union[dict, None]:
    """Identify the profile template based on its name.

    Args:
        template (str): The name of the template we are looking for.

    Returns:
        dict: A dict modelling the server.ProfileTemplate object
        None: If the system faile to reach Intersight.
    """
    # Find MOID and returning instance of template
    api_instance = server_api.ServerApi(api_client)
    query_filter = "Name eq '" + template + "'"
    query_select = "name,moid"

    try:
        template_query = api_instance.get_server_profile_template_list(filter=query_filter, select=query_select)
        template_results = str(template_query.results[0]).replace("\'","\"")
    
        template_dict = json.loads(template_results)
        template_moid = template_dict["moid"]
    
        template_map = {
            "object_type" : "server.ProfileTemplate",
            "moid" : template_moid
        }
        
        return template_map
    except intersight.ApiException as e:
        print("Exception when calling ServerApi->get_server_profile_template_list: %s\n" % e)
        sys.exit(1)

def set_resource_pool(pool: str):
    """Identify the resource pool based on its name.

    Args:
        pool (str): The name of the resource pool we are looking for.

    Returns:
        dict: A dict modelling the resourcepool.Pool object
        None: If the system failed to reach Intersight.
    """
    # Find MOID and returning instance of pool
    api_instance = resourcepool_api.ResourcepoolApi(api_client)
    query_filter = "Name eq '" + pool + "'"
    query_select = "name,moid,ClassId,ObjectType"

    try:
        pool_query = api_instance.get_resourcepool_pool_list(filter=query_filter, select=query_select)
        pool_results = str(pool_query.results[0]).replace("\'","\"")
    
        pool_dict = json.loads(pool_results)
        pool_moid = pool_dict["moid"]
    
        pool_map = {
            "object_type" : "server.ProfileTemplate",
            "moid" : pool_moid
        }
        
        #return pool_map
        return pool_dict
    except intersight.ApiException as e:
        print("Exception when calling ServerApi->get_server_profile_template_list: %s\n" % e)
        sys.exit(1)

def create_server_profile(hostname: str = os_params['hostname'], 
                          organization_name: str = "default",
                          template_name: str = "CaaS-Master",
                          pool = set_resource_pool('blades')
                          ) -> Union[str, None]:
    """Create a new server profile from template. 
    
    Based on the provided organization and template names, 
    create a server profile with the provided hostname.

    Args:
        hostname (str, optional): The hostname for the server.
            Defaults to 'BMaaS-4'.
        organization_name (str, optional): The name of the org
            under which the server profile will be created. 
            Defaults to 'default'.
        template_name (str, optional): The name of the template
            we want to use for our server profile. Defaults to
            'RackMount'.
    
    Returns:
        str: The moid of our newly created server profile.
        None: If the system is unable to create the server profile.
    """
    api_instance = bulk_api.BulkApi(api_client)
    kwargs_mo_cloner = {
        "sources": [],
        "targets": []
    }
    # Select an instance of organization.
    organization = set_organization(organization_name)

    # Select an instance of server template to derive profiles from.
    template = set_profile_template(template_name)

    org = {
        "class_id" : organization.class_id,
        "Moid" : organization.moid,
        "object_type" : organization.object_type
    }

    kwargs_mo_cloner["sources"].append(ServerProfileTemplate(**template))

    target_profile = {
            "Name" : hostname,
            "ObjectType" : "server.Profile",
            "Organization" : org,
            "SrcTemplate": {
                "ClassId": "mo.MoRef",
                "Moid": template["moid"],
                "ObjectType": template["object_type"]
            },
            "ServerAssignmentMode": "Pool",
            "ServerPool": pool
        }
    
    kwargs_mo_cloner["targets"].append(ServerProfile(**target_profile))
    mo_cloner = BulkMoCloner(**kwargs_mo_cloner)

    try:
        payload = api_instance.create_bulk_mo_cloner(mo_cloner)
        #server_profile_moid = (payload.responses[0].body.moid)
        #pprint(payload.responses[0].body)

        #return server_profile_moid
        return payload
    except intersight.ApiException as e:
        print("Exception when calling ServerApi->create_server_profile: %s\n" % e)
        sys.exit(1)

def deploy_server_profile(server_profile_moid: str) -> Union[str, None]:
    """ Deploy a previously created server profile. 

    Args:
        server_profile_moid (str): The moid of the server profile
            we want to deploy.
        
    Returns:
        dict: The deployed server profile response.
        None: If the system was unable to deploy the resource.
    """

    api_instance = server_api.ServerApi(api_client)

    # Creation of server profile model instance.
    server_profile = ServerProfile()

    # Setting the attribute for server profile with the action and server profile moid.
    server_profile.action = "Deploy"
    # example passing only required values which don't have defaults set
    try:
        # Patching a 'Server.Profile' resource.
        resp_server_profile = api_instance.patch_server_profile(moid=server_profile_moid,
                                                                server_profile=server_profile)
        print("The assigned server MOID is: %s\n" % resp_server_profile.assigned_server.moid)
        return resp_server_profile.assigned_server
    except intersight.ApiException as e:
        print("Exception when calling ServerApi->patch_server_profile: %s\n" % e)
        sys.exit(1)

def get_macs(sp_moid: str):
    """Identify the MAC addresses of vnics associated with a specific server profile.

    Args:
        server_profile (str): The moid of the profile to query vnics from.

    Returns:
        dict: A dict with all defined vnics
        None: If the system failed to reach Intersight.
    """

    api_instance = vnic_api.VnicApi(api_client)
    query_filter = "Profile.Moid eq '" + sp_moid + "'"
    query_select = "Name,MacAddress"

    try:
        vnic_query = api_instance.get_vnic_eth_if_list(filter=query_filter, select=query_select)
        for vnic in vnic_query.results:
            print("The MAC address for %s is %s" %(vnic.name, vnic.mac_address))
            
        return vnic_query
    except intersight.ApiException as e:
        print("Exception when calling ServerApi->get_server_profile_template_list: %s\n" % e)
        sys.exit(1)

def os_install(server_param: dict, 
               ipv4_address: str,
               gateway: str, 
               netmask: str,
               hostname: str):
    """Kick off a os install on the specified server.
    
    Args:
        server_param(dict): The server profile previously created.
        ipv4_address (str): The IPv4 address of the server.
        gateway (str): The gateway for the interface.
        netmask (str): The netmask in dotted-decimal notation.
        hostname (str): The hostname for the new server.
    """
    api_instance = os_api.OsApi(api_client)

    # Creation of OsInstall model instance.
    os_install = OsInstall()

    os_install.name = "RHEL_install_from_api"
    os_install.description = "OS Install Demo"
    os_install.install_method = "vMedia"
    os_install.server = server_param
    os_install.organization = OrganizationOrganizationRelationship(
        class_id="mo.MoRef",
        object_type="organization.Organization",
        moid="6164798e6972652d33749d75"
    )
    os_install.image = SoftwarerepositoryOperatingSystemFileRelationship(
        class_id="mo.MoRef",
        object_type="softwarerepository.OperatingSystemFile",
        moid="624761646567612d31626049"
    )
    os_install.osdu_image = FirmwareServerConfigurationUtilityDistributableRelationship(
        class_id="mo.MoRef",
        object_type="firmware.ServerConfigurationUtilityDistributable",
        moid="620286c76567612d3167c743"
    )
    os_install.install_target = OsInstallTarget(object_typ="os.PhysicalDisk",
                                         name="Disk 1",
                                         serialnumber="78H0A0BCTSCE",
                                         StorageControllerSlotId="MRAID",
                                         class_id="os.PhysicalDisk"
                                         )

    ip_configuration = OsIpConfiguration(object_type="os.Ipv4Configuration",
                                         class_id="os.Ipv4Configuration",
                                         ip_v4_config=CommIpV4Interface(
                                             ip_address=ipv4_address,
                                             netmask=netmask,
                                             gateway=gateway
                                         ))
    answers = OsAnswers(source="Template",
                        hostname=hostname,
                        ip_config_type="static",
                        root_password="Cisco.12345",
                        is_root_password_crypted=False,
                        nameserver="172.20.50.5",
                        NetworkDevice="eno5",
                        ip_configuration=ip_configuration,
                        )
    os_install.answers = answers

    #fetch_os_config_file_list = fetch_os_config_file(api_client,config_file="ESXi6.7ConfigFile")
    os_config_file_moid = "5ea23e69025f8bcd6592c4b2" #fetch_os_config_file_list.results[0].moid

    os_install.configuration_file = OsConfigurationFileRelationship(
        object_type="os.ConfigurationFile",
        class_id="mo.MoRef",
        moid=os_config_file_moid
    )

    # example passing only required values which don't have defaults set
    try:
        # Create a 'os.Install' resource.
        resp_os_install = api_instance.create_os_install(os_install)
        pprint(resp_os_install)
        return resp_os_install
    except intersight.ApiException as e:
        print("Exception when calling OsApi->:create_os_install %s\n" % e)
        sys.exit(1)

if __name__ == "__main__":
    #server_profile_moid = create_server_profile()
    server_profile = create_server_profile()
    sp_moid = server_profile.responses[0].body.moid
    server_param = deploy_server_profile(sp_moid)
    print("Gathering Network Information...")
    time.sleep(5)
    mac_addresses = get_macs(sp_moid)
    #pprint("Sleeping for 10 minutes while server deploys.")
    #time.sleep(600) # Wait 10 min for Profile to deploy
    #pprint("Initiating RHEL 7.9 installation.")

    #os_params['server_param'] = server_param
    #os_install(**os_params)

    # Placeholder for ICO integration
    