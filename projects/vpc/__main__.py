"""
vpc

Creates a VPC, cool
"""
import pulumi
import pulumi_awsx as awsx

# ---------------------------------------------------------------------------------------
# Project config
# ---------------------------------------------------------------------------------------
STACK = pulumi.get_stack()
PROJECT_NAME = pulumi.get_project()
TAGS = {
    "environment": STACK,
    "project": PROJECT_NAME,
}

# Environment specific config
CONFIG = pulumi.Config()
cidr_block = CONFIG.require("cidr_block")
number_of_availability_zones = CONFIG.require_int("number_of_availability_zones")
nat_gateway_strategy = CONFIG.require("nat_gateway_strategy")

# ---------------------------------------------------------------------------------------
# vpc
# https://www.pulumi.com/docs/clouds/aws/guides/vpc/
# Note, a default security group is created that disallows all ingress and permits all egress
# ---------------------------------------------------------------------------------------
vpc = awsx.ec2.Vpc(
    f"vpc-{STACK}",
    cidr_block=cidr_block,
    enable_dns_hostnames=True,
    number_of_availability_zones=number_of_availability_zones,
    nat_gateways=awsx.ec2.NatGatewayConfigurationArgs(strategy=nat_gateway_strategy),
    tags=TAGS,
)

pulumi.export("vpc_id", vpc.vpc_id)
pulumi.export("public_subnet_ids", vpc.public_subnet_ids)
pulumi.export("private_subnet_ids", vpc.private_subnet_ids)
pulumi.export("cidr_block", cidr_block)
