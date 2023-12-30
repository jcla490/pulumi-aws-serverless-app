"""
load_balancer

Creates an application load balancer
"""
import os

import pulumi
import pulumi_aws as aws

# ---------------------------------------------------------------------------------------
# Project config
# ---------------------------------------------------------------------------------------
STACK = pulumi.get_stack()
PROJECT_NAME = pulumi.get_project()
TAGS = {
    "environment": STACK,
    "project": PROJECT_NAME,
}

# Stack references
vpc = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/vpc/{STACK}")
vpc_id = vpc.require_output("vpc_id")
public_subnet_ids = vpc.require_output("public_subnet_ids")

certificates = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/certificates/{STACK}")
root_domain_certificate_arn = certificates.require_output("root_domain_certificate_arn")

# Environment specific config
CONFIG = pulumi.Config()
domain_name = CONFIG.require("domain")
hosted_zone_id = CONFIG.require("hosted_zone_id")

# ---------------------------------------------------------------------------------------
# application load balancer
# https://www.pulumi.com/registry/packages/aws/api-docs/lb/loadbalancer/
# ---------------------------------------------------------------------------------------
security_group = aws.ec2.SecurityGroup(
    "load-balancer-security-group",
    description="Security group for application load balancer",
    vpc_id=vpc_id,
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
        )
    ],
)

load_balancer = aws.lb.LoadBalancer(
    "load-balancer",
    internal=False,
    load_balancer_type="application",
    subnets=public_subnet_ids,
    security_groups=[security_group.id],
)

target_group = aws.lb.TargetGroup(
    "load-balancer-tg",
    protocol="HTTP",
    target_type="ip",
    vpc_id=vpc_id,
    port=80,
    health_check=aws.lb.TargetGroupHealthCheckArgs(
        matcher="200-302", interval=300, path="/health"
    ),
    opts=pulumi.ResourceOptions(parent=load_balancer),
)

# Redirects to HTTPS
http_listener = aws.lb.Listener(
    "http-listener",
    load_balancer_arn=load_balancer.arn,
    port=80,
    default_actions=[
        aws.lb.ListenerDefaultActionArgs(
            type="redirect",
            redirect=aws.lb.ListenerDefaultActionRedirectArgs(
                port="443",
                protocol="HTTPS",
                status_code="HTTP_301",
            ),
        )
    ],
    opts=pulumi.ResourceOptions(parent=load_balancer),
)

https_listener = aws.lb.Listener(
    "https-listener",
    load_balancer_arn=load_balancer.arn,
    port=443,
    protocol="HTTPS",
    certificate_arn=root_domain_certificate_arn,
    default_actions=[
        aws.lb.ListenerDefaultActionArgs(
            type="forward",
            target_group_arn=target_group.arn,
        )
    ],
)

load_balancer_record = aws.route53.Record(
    "load-balancer-a-record",
    zone_id=hosted_zone_id,
    name=f"api.{domain_name}",
    type="A",
    aliases=[
        aws.route53.RecordAliasArgs(
            name=load_balancer.dns_name,
            zone_id=load_balancer.zone_id,
            evaluate_target_health=True,
        )
    ],
)

pulumi.export("load_balancer_arn", load_balancer.arn)
pulumi.export("load_balancer_dns_name", load_balancer.dns_name)
pulumi.export("load_balancer_zone_id", load_balancer.zone_id)
pulumi.export("load_balancer_security_group_id", security_group.id)
pulumi.export("http_listener_arn", http_listener.arn)
pulumi.export("https_listener_arn", https_listener.arn)
pulumi.export("target_group_arn", target_group.arn)
