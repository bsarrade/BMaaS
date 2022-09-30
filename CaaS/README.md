# CaaS
Collection of code related to automation of the OpenShift Container Platform UPI deployment on Cisco Intersight and UCS.

PoC pre-requistes and assumptions:

- Server Profiles are already assigned and deployed to servers in lab.
- There are no existing Vmedia policies associated with Server Profiles.
- Ansible host workstation has Python 3 with Cryptography module installed and the Intersight appliance is reachable via IP over port 443.

Instructions:
1. Create environment variables with your Intersight API key and Secret file path:
    (example)
    export api_key_id='6164718d7564612d33e6ed3f/...'
    export api_private_key=~/Documents/Intersight/SecretKey.txt
2. Update the inventory file "caas_inventory" using the "list_server_profiles_by_tag" playbook. This will update the inventory with all assigned Server Profiles in Intersight:
    *NOTE* The inventory file will not update if empty. There is a placeholder '.' as a workaround and this must be removed after initial update.
    (example)
    ansible-playbook -i caas_inventory list_server_profiles_by_tag.yml -e group=caas_hosts -e api_uri=https://{FQDN}/api/v1
3. Run the "create_vmedia_policy" playbook to:
    - Create a unique vmedia policy for each host listed in the inventory. 
    - Associated it with the appropriate host.
    - Deploy the Server Profile to mount the vmedia.
    (example)
    ansible-playbook -i caas_inventory create_vmedia_policy.yml -e group=caas_hosts -e api_uri=https://{FQDN}/api/v1
    *NOTE* You will need to update the following vars with the correct values:
          volume
          remote_hostname 
          remote_path
          remote_file
          username
          password
4. Run the "server_actions" playbook to change the desired power state. Options: Policy, PowerOn, PowerOff, PowerCycle, HardReset, Shutdown, Reboot
    *NOTE* Assumption that the current Boot Order policy sets the cimc-mapped-dvd option as first in the boot order. "One Time Boot" option is to be implemented to code in a future release :)
    (example)
    ansible-playbook -i caas_inventory server_actions.yml -e power_state=PowerOn -e group=caas_hosts -e api_uri=https://{FQDN}/api/v1

