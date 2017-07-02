#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

ANSIBLE_METADATA = {'status': ['stableinterface'],
                    'supported_by': 'committer',
                    'version': '1.0'}

DOCUMENTATION = """
---
module: ec2_lc
short_description: Create or delete AWS Autoscaling Launch Configurations
description:
  - Can create or delete AWS Autoscaling Configurations
  - Works with the ec2_asg module to manage Autoscaling Groups
notes:
  - "Amazon ASG Autoscaling Launch Configurations are immutable once created, so modifying the configuration
    after it is changed will not modify the launch configuration on AWS. You must create a new config and assign
    it to the ASG instead."
version_added: "1.6"
author: "Gareth Rushgrove (@garethr)"
        "Willem van Ketwich (@wilvk)"
options:
  state:
    description:
      - register or deregister the instance
    required: true
    choices: ['present', 'absent']
  name:
    description:
      - Unique name for configuration
    required: true
  instance_type:
    description:
      - instance type to use for the instance
    required: true
    default: null
    aliases: []
  image_id:
    description:
      - The AMI unique identifier to be used for the group
    required: false
  key_name:
    description:
      - The SSH key name to be used for access to managed instances
    required: false
  security_groups:
    description:
      - A list of security groups to apply to the instances. For VPC instances, specify security group IDs. For EC2-Classic, specify either security group names or IDs.
    required: false
  volumes:
    description:
      - a list of volume dicts, each containing device name and optionally ephemeral id or snapshot id. Size and type (and number of iops for io device type) must be specified for a new volume or a root volume, and may be passed for a snapshot volume. For any volume, a volume size less than 1 will be interpreted as a request not to create the volume.
    required: false
  user_data:
    description:
      - opaque blob of data which is made available to the ec2 instance. Mutually exclusive with I(user_data_path).
    required: false
  user_data_path:
    description:
      - Path to the file that contains userdata for the ec2 instances. Mutually exclusive with I(user_data).
    required: false
    version_added: "2.3"
  kernel_id:
    description:
      - Kernel id for the EC2 instance
    required: false
  spot_price:
    description:
      - The spot price you are bidding. Only applies for an autoscaling group with spot instances.
    required: false
  instance_monitoring:
    description:
      - whether instances in group are launched with detailed monitoring.
    default: false
  assign_public_ip:
    description:
      - Used for Auto Scaling groups that launch instances into an Amazon Virtual Private Cloud. Specifies whether to assign a public IP address to each instance launched in a Amazon VPC.
    required: false
    version_added: "1.8"
  ramdisk_id:
    description:
      - A RAM disk id for the instances.
    required: false
    version_added: "1.8"
  instance_profile_name:
    description:
      - The name or the Amazon Resource Name (ARN) of the instance profile associated with the IAM role for the instances.
    required: false
    version_added: "1.8"
  ebs_optimized:
    description:
      - Specifies whether the instance is optimized for EBS I/O (true) or not (false).
    required: false
    default: false
    version_added: "1.8"
  classic_link_vpc_id:
    description:
      - Id of ClassicLink enabled VPC
    required: false
    version_added: "2.0"
  classic_link_vpc_security_groups:
    description:
      - A list of security group id's with which to associate the ClassicLink VPC instances.
    required: false
    version_added: "2.0"
extends_documentation_fragment:
    - aws
    - ec2
requirements:
    - boto >= 3.0.0
    - python >= 2.6
"""

EXAMPLES = '''
- ec2_lc:
    name: special
    image_id: ami-XXX
    key_name: default
    security_groups: ['group', 'group2' ]
    instance_type: t1.micro
    volumes:
    - device_name: /dev/sda1
      volume_size: 100
      device_type: io1
      iops: 3000
      delete_on_termination: true
    - device_name: /dev/sdb
      ephemeral: ephemeral0

'''

import traceback
from ansible.module_utils.ec2 import (get_aws_connection_info,
                                      ec2_argument_spec,
                                      boto3_conn, HAS_BOTO3)
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ec2 import camel_dict_to_snake_dict

try:
    import botocore
except:
    pass


class Ec2LaunchConfigurationServiceManager(object):
    """Handles EC2 Launch Config Services"""

    def __init__(self, module):
        self.client = {}
        self.module = module
        self.create_client('autoscaling')
        self.create_client('ec2')

    def create_client(self, resource):
        try:
            region, ec2_url, aws_connect_kwargs = get_aws_connection_info(
                self.module, boto3=True)
            self.client[resource] = boto3_conn(self.module, conn_type='client',
                                               resource=resource, region=region,
                                               endpoint=ec2_url, **aws_connect_kwargs)
        except botocore.exceptions.NoRegionError:
            self.module.fail_json(
                msg=("region must be specified as a parameter in "
                     "AWS_DEFAULT_REGION environment variable or in "
                     "boto configuration file"))
        except botocore.exceptions.ClientError as e:
            self.module.fail_json(
                msg="unable to establish connection - " + str(e),
                exception=traceback.format_exc(),
                **camel_dict_to_snake_dict(e.response))

    def create_block_device(self, module, volume):
        MAX_IOPS_TO_SIZE_RATIO = 30
        if 'snapshot' not in volume and 'ephemeral' not in volume:
            if 'volume_size' not in volume:
                module.fail_json(msg='Size must be specified when creating a new volume or modifying the root volume')
        if 'snapshot' in volume:
            if 'device_type' in volume and volume.get('device_type') == 'io1' and 'iops' not in volume:
                module.fail_json(msg='io1 volumes must have an iops value set')
        if 'ephemeral' in volume:
            if 'snapshot' in volume:
                module.fail_json(msg='Cannot set both ephemeral and snapshot')

        return_object = {}

        if 'ephemeral' in volume:
            return_object['VirtualName'] = volume.get('ephemeral')

        if 'device_name' in volume:
            return_object['DeviceName'] = volume.get('device_name')

        if 'no_device' is volume:
            return_object['NoDevice'] = volume.get('no_device')

        if any(key in volume for key in ['snapshot', 'volume_size',
               'volume_type', 'delete_on_termination', 'ips', 'encrypted']):
            return_object['Ebs'] = {}

        if 'snapshot' in volume:
            return_object['Ebs']['SnapshotId'] = volume.get('snapshot')

        if 'volume_size' in volume:
            return_object['Ebs']['VolumeSize'] = volume.get('volume_size')

        if 'volume_type' in volume:
            return_object['Ebs']['VolumeType'] = volume.get('volume_type')

        if 'delete_on_termination' in volume:
            return_object['Ebs']['DeleteOnTermination'] = volume.get('delete_on_termination', False)

        if 'iops' in volume:
            return_object['Ebs']['Iops'] = volume.get('iops')

        if 'encrypted' in volume:
            return_object['Ebs']['Encrypted'] = volume.get('encrypted')

        return return_object

    def create_launch_config(self, module):
        name = module.params.get('name')
        image_id = module.params.get('image_id')
        key_name = module.params.get('key_name')
        security_groups = module.params['security_groups']
        user_data = module.params.get('user_data')
        instance_id = module.params.get('instance_id')
        user_data_path = module.params.get('user_data_path')
        volumes = module.params['volumes']
        instance_type = module.params.get('instance_type')
        spot_price = module.params.get('spot_price')
        instance_monitoring = module.params.get('instance_monitoring')
        advanced_instance_monitoring = module.params.get('advanced_instance_monitoring')
        assign_public_ip = module.params.get('assign_public_ip')
        kernel_id = module.params.get('kernel_id')
        ramdisk_id = module.params.get('ramdisk_id')
        instance_profile_name = module.params.get('instance_profile_name')
        ebs_optimized = module.params.get('ebs_optimized')
        classic_link_vpc_id = module.params.get('classic_link_vpc_id')
        classic_link_vpc_security_groups = module.params.get('classic_link_vpc_security_groups')
        associate_public_ip_address = module.params.get('associate_public_ip_address')
        placement_tenancy = module.params.get('placement_tenancy')

        bdm = {}

        connection = self.client["autoscaling"]

        if user_data_path:
            try:
                with open(user_data_path, 'r') as user_data_file:
                    user_data = user_data_file.read()
            except IOError as e:
                module.fail_json(msg=str(e), exception=traceback.format_exc())

        if volumes:
            for volume in volumes:
                if 'device_name' not in volume:
                    module.fail_json(msg='Device name must be set for volume')
                # Minimum volume size is 1GB. We'll use volume size explicitly set to 0
                # to be a signal not to create this volume
                if 'volume_size' not in volume or int(volume['volume_size']) > 0:
                    bdm.update(self.create_block_device(module, volume))

        launch_configs = connection.describe_launch_configurations(LaunchConfigurationNames=[name]).get('LaunchConfigurations')
        changed = False
        result = {}

        launch_config = {
            'LaunchConfigurationName': name,
            'ImageId': image_id,
            'InstanceType': instance_type,
            'EbsOptimized': ebs_optimized,
        }

        if instance_id is not None:
            launch_config['InstanceId'] = instance_id

        if classic_link_vpc_id is not None:
            launch_config['ClassicLinkVPCId'] = classic_link_vpc_id

        if instance_monitoring:
            launch_config['InstanceMonitoring'] = {'Enabled': advanced_instance_monitoring}

        if placement_tenancy is not None:
            launch_config['PlacementTenancy'] = placement_tenancy

        if classic_link_vpc_security_groups is not None:
            launch_config['ClassicLinkVPCSecurityGroups'] = classic_link_vpc_security_groups

        if key_name is not None:
            launch_config['KeyName'] = key_name

        if bdm is not None:
            launch_config['BlockDeviceMappings'] = [bdm]

        if security_groups is not None:
            launch_config['SecurityGroups'] = security_groups

        if kernel_id is not None:
            launch_config['KernelId'] = kernel_id

        if ramdisk_id is not None:
            launch_config['RamdiskId'] = ramdisk_id

        if instance_profile_name is not None:
            launch_config['IamInstanceProfile'] = instance_profile_name

        if spot_price is not None:
            launch_config['SpotPrice'] = str(spot_price)

        if assign_public_ip is not None:
            launch_config['AssociatePublicIpAddress'] = assign_public_ip

        if user_data is not None:
            launch_config['UserData'] = user_data

        if len(launch_configs) == 0:
            try:
                connection.create_launch_configuration(**launch_config)
                launch_configs = connection.describe_launch_configurations(LaunchConfigurationNames=[name]).get('LaunchConfigurations')
                changed = True
            except botocore.exceptions.ClientError as e:
                module.fail_json(msg=str(e))

        if len(launch_configs) > 0:
            result = dict(
                         ((a[0], a[1]) for a in launch_configs[0].items()
                          if a[0] not in ('connection', 'created_time', 'instance_monitoring', 'block_device_mappings'))
            )

        result['CreatedTime'] = str(launch_configs[0].get('CreatedTime'))

        if launch_configs[0].get('InstanceMonitoring') is True:
            result['InstanceMonitoring'] = True
        else:
            try:
                result['InstanceMonitoring'] = module.boolean(launch_configs[0].get('InstanceMonitoring').get('Enabled'))
            except AttributeError:
                result['InstanceMonitoring'] = False
        if launch_configs[0].get('BlockDeviceMappings') is not None:
            result['BlockDeviceMappings'] = []
            for bdm in launch_configs[0].get('BlockDeviceMappings'):
                result['BlockDeviceMappings'].append(dict(device_name=bdm.get('DeviceName'), virtual_name=bdm.get('VirtualName')))
                if bdm.get('Ebs') is not None:
                    result['BlockDeviceMappings'][-1]['ebs'] = dict(snapshot_id=bdm.get('Ebs').get('SnapshotId'), volume_size=bdm.get('Ebs').get('VolumeSize'))

        if user_data_path:
            result['UserData'] = "hidden"

        return_object = {
            'Name': result.get('LaunchConfigurationName'),
            'created_time': result.get('CreatedTime'),
            'ImageId': result.get('ImageId'),
            'Arn': result.get('LaunchConfigurationARN'),
            'SecurityGroups': result.get('SecurityGroups'),
            'InstanceType': result.get('InstanceType'),
            'Result': result
        }

        module.exit_json(changed=changed, **camel_dict_to_snake_dict(return_object))

    def delete_launch_config(self, module):
        name = module.params.get('name')
        connection = self.client['autoscaling']
        launch_configs = connection.describe_launch_configurations(LaunchConfigurationNames=[name]).get('LaunchConfigurations')
        if launch_configs and len(launch_configs) > 0:
            connection.delete_launch_configuration(
                LaunchConfigurationName=launch_configs[0].get('LaunchConfigurationName'))
            module.exit_json(changed=True)
        else:
            module.exit_json(changed=False)


def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(
        dict(
            name=dict(required=True, type='str'),
            image_id=dict(type='str'),
            instance_id=dict(type='str'),
            key_name=dict(type='str'),
            security_groups=dict(type='list'),
            user_data=dict(type='str'),
            user_data_path=dict(type='path'),
            kernel_id=dict(type='str'),
            volumes=dict(type='list'),
            instance_type=dict(type='str'),
            state=dict(default='present', choices=['present', 'absent']),
            spot_price=dict(type='float'),
            ramdisk_id=dict(type='str'),
            instance_profile_name=dict(type='str'),
            ebs_optimized=dict(default=False, type='bool'),
            associate_public_ip_address=dict(type='bool'),
            instance_monitoring=dict(default=False, type='bool'),
            advanced_instance_monitoring=dict(default=False, type='bool'),
            assign_public_ip=dict(type='bool'),
            classic_link_vpc_security_groups=dict(type='list'),
            classic_link_vpc_id=dict(type='str'),
            placement_tenancy=dict(type='str')
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[['user_data', 'user_data_path']]
    )

    service_mgr = Ec2LaunchConfigurationServiceManager(module)

    state = module.params.get('state')
    result = {}

    if state == 'present':
        result = service_mgr.create_launch_config(module)
    elif state == 'absent':
        service_mgr.delete_launch_config(module)


if __name__ == '__main__':
    main()
