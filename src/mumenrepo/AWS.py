
from .common_imports import *

class AWS:
    @staticmethod
    def get_text(cmd):
        p = subprocess.run(cmd, shell=True, capture_output=True)
        if p.returncode != 0:
            raise Exception(f"command returned {p.returncode} | {cmd}")
        return p.stdout.decode('ascii').strip('\n').strip(' ')

    @staticmethod
    def get_json(cmd):
        p = subprocess.run(cmd, shell=True, capture_output=True)
        if p.returncode != 0:
            raise Exception(f"command returned {p.returncode} | {cmd}")
        return json.loads( p.stdout )

    @staticmethod
    def filter_pair(name, values):
        return {"name":name, "values":values}

    @staticmethod
    def command(command_group, command_str, filters=None, query=None):
        s = f"aws {command_group} {command_str} --output json "
        if filters is not None:
            s += "--filters "
            for fil in filters:
                s += f""" "Name={fil["name"]},Values={fil["values"]}" """
        if query is not None:
            s += f"--query {query} "
        return s

    class EC2(object):
        def describe_instances(key, value, query=None):
            filters = [AWS.filter_pair("instance-state-name","running"), AWS.filter_pair(f'tag:{key}', value)]
            return AWS.command('ec2', 'describe-instances', filters=filters, query=query)

        def iter_instances(instances):
            for reservation in instances["Reservations"]:
                for instance in reservation["Instances"]:
                    yield instance

        def find_recent_ami(out_path):
            os.system(f"""
        aws ec2 describe-images --owners amazon \
            --filters "Name=architecture,Values=x86_64" "Name=description,Values=*Amazon Linux 2 Kernel*gp2" "Name=virtualization-type,Values=hvm" \
            --query "sort_by(Images, &CreationDate)" \
            > {out_path} 
        """)

        spot_template = """
        {
            "IamFleetRole": "",
            "AllocationStrategy": "lowestPrice",
            "TargetCapacity": 1,
            "ValidFrom": "2021-12-24T20:11:30Z",
            "ValidUntil": "2022-12-24T20:11:30Z",
            "TerminateInstancesWithExpiration": true,
            "LaunchSpecifications": [
                {
                    "InstanceRequirements": {
                        "VCpuCount": {
                            "Min": 4,
                            "Max": 4
                        },
                        "MemoryMiB": {
                            "Min": 8192,
                            "Max": 8192
                        }
                    },
                    "ImageId": "",
                    "SubnetId": "",
                    "KeyName": "",
                    "BlockDeviceMappings": [],
                    "SecurityGroups": [
                        {
                            "GroupId": "sg-0ab3487f2566c18a9"
                        }
                    ],
                    "IamInstanceProfile": {
                        "Arn": ""
                    },
                    "TagSpecifications": []
                }
            ],
            "Type": "request",
            "TargetCapacityUnitType": "units",
            "TagSpecifications": [],
            "SpotMaxTotalPrice": "0.07"
        }
        """

        def get_vpc_info():
            vpc_id = AWS.get_text(f"""aws ec2 describe-vpcs --output text \
            --filters "Name=is-default,Values=true" \
            --query "Vpcs[].VpcId" """)
            subnet_ids = AWS.get_text(f"""aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values={vpc_id}" \
            --query "Subnets[].SubnetId"
            """)
            result = {"vpc":vpc_id, "subnets":json.loads(subnet_ids)}
            return result
            
        def create_spot_request(env, paths):
            with open(env['root_dir'] / 'templates' / 'spot-request.json', "r") as f:
                request = json.load(f)
            with open(paths["amis"], "r") as f:
                amis = json.load(f)

            vpc_info = AWS.EC2.get_vpc_info()

            ami = amis[-1]
            request["IamFleetRole"] = f"arn:aws:iam::{env['acct_id']}:role/aws-ec2-spot-fleet-tagging-role"
            request["TagSpecifications"] = [
                {"ResourceType":"spot-fleet-request", "Tags":[{"Key":env.ec2.server_name, "Value":env['instance']}]}
            ]
            request["ClientToken"] = f"{env['id']}-{env['instance']}-{env['request_ordinal']}"

            lspec = request["LaunchSpecifications"][0]
            lspec["KeyName"] = env.ec2.key
            lspec["ImageId"] = ami["ImageId"]
            lspec["SubnetId"] = ", ".join( vpc_info["subnets"] )
            lspec["BlockDeviceMappings"] = ami["BlockDeviceMappings"]
            lspec["IamInstanceProfile"]["Arn"] = f"arn:aws:iam::{env['acct_id']}:instance-profile/mc-{env['instance']}-admin-instance-profile" 
            lspec["TagSpecifications"] = [
                {"ResourceType":"instance", "Tags":[{"Key":env.ec2.server_name, "Value":env['instance']}]} 
            ]

            with open(env['instance_dir'] / 'spot-request.json', "w") as f:
                json.dump(request, f)

        def ec2_up(env):
            AWS.EC2.create_spot_request()
            spot_req_config = env['instance_dir'] / 'spot-request.json'
            spot_req_result = env['instance_dir'] / 'spot-request-result.json'
            os.system(f"aws ec2 request-spot-fleet --spot-fleet-request-config file://{spot_req_config} > {spot_req_result}")

        def ec2_setup(env, ssh_opts, ssh_host):
            script_path = env['instance_dir'] / 'tmp' / 'ec2_setup_script.sh'
            with open(script_path, "w") as f:
                f.write( env.get_template("ec2_setup_script.sh").render(env=env) )

        def ec2_connect(ssh_opts, ssh_host):
            os.system(f"ssh {ssh_opts} {ssh_host}")
            
        def ec2_down(env):
            with open(env['instance_dir'] / 'spot-request-result.json', "r") as f:
                req = json.load(f)
            os.system(f"aws ec2 cancel-spot-fleet-requests --spot-fleet-request-ids {req['SpotFleetRequestId']} --terminate-instances")

    class Route53:
        def change_resource_record_sets(env, hostname, ip_addr):
            command = {
                "Changes": [{"Action": "UPSERT", "ResourceRecordSet": {"Name": hostname, "Type":"A", "ResourceRecords": [{"Value": env.ipaddr}], "TTL": 60}}]
            }
            change_dns_dst = env.tmp_dir / "change_dns.json"
            with open(change_dns_dst, "w") as f:
                json.dump(command, f)

            os.system(f'aws route53 change-resource-record-sets --hosted-zone-id {env["hosted_zone"]} --change-batch file://{change_dns_dst}')