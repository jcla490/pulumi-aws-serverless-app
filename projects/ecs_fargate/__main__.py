"""
ecs_fargate

Creates an ECS cluster on AWS Fargate
"""
import json
import os
import pulumi
import pulumi_aws as aws
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

# Stack references
vpc = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/vpc/{STACK}")
vpc_id = vpc.require_output("vpc_id")
web_security_group_id = vpc.require_output("web_security_group_id")
public_subnet_ids = vpc.require_output("public_subnet_ids")

# Environment specific config
CONFIG = pulumi.Config()

# ---------------------------------------------------------------------------------------
# ECS cluster
# https://www.pulumi.com/registry/packages/aws/api-docs/ecs/cluster/
# ---------------------------------------------------------------------------------------
cluster = aws.ecs.Cluster(
    f"cluster-{STACK}",
    name=f"cluster-{STACK}",
    settings=[
        aws.ecs.ClusterSettingArgs(
            name="containerInsights",
            value="enabled",
        )
    ],
    tags=TAGS,
)

# Probably not needed but useful if you want to also config FARGATE_SPOT
cluster_capacity_providers = aws.ecs.ClusterCapacityProviders(
    f"cluster-capacity-providers",
    cluster_name=cluster.name,
    capacity_providers=["FARGATE"],
    default_capacity_provider_strategies=[
        aws.ecs.ClusterCapacityProvidersDefaultCapacityProviderStrategyArgs(
            base=1,
            weight=100,
            capacity_provider="FARGATE",
        )
    ],
)

# Create an execution role that can be used by tasks on this cluster
task_execution_role = aws.iam.Role(
    "task-execution-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2008-10-17",
            "Statement": [
                {
                    "Sid": "TaskAssumeRole",
                    "Effect": "Allow",
                    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    ),
)

rpa = aws.iam.RolePolicyAttachment(
    "task-execution-rpa",
    role=task_execution_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
)

# Cluster load balancer
# Target group/listener resources will be co-located with apps
load_balancer = awsx.lb.ApplicationLoadBalancer(
    "cluster-load-balancer",
    security_groups=[web_security_group_id],
    subnet_ids=public_subnet_ids,
    tags=TAGS,
)

pulumi.export("cluster_arn", cluster.arn)
pulumi.export("cluster_task_execution_role_arn", task_execution_role.arn)
pulumi.export("cluster_load_balancer", load_balancer.load_balancer)
