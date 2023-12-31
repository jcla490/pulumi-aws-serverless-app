"""
ecs

Creates an ECS cluster on AWS Fargate
"""
import json
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

SERVICE_CONNECT_NAMESPACE_NAME = "orangejuice"
SERVICE_CONNECT_NAMESPACE_DESCRIPTION = (
    f"Services supporting {SERVICE_CONNECT_NAMESPACE_NAME}"
)

# Stack references
vpc = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/vpc/{STACK}")
vpc_id = vpc.require_output("vpc_id")

aurora = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/aurora/{STACK}")
db_credentials_secret_arn = aurora.require_output(
    "orangejuicedb_credentials_secret_arn"
)

# Environment specific config
CONFIG = pulumi.Config()
container_insights = CONFIG.require("container_insights")
fargate_base = CONFIG.require_int("fargate_base")
fargate_weight = CONFIG.require_int("fargate_weight")
fargate_spot_weight = CONFIG.require_int("fargate_spot_weight")

# ---------------------------------------------------------------------------------------
# service connect namespace
# https://www.pulumi.com/registry/packages/aws/api-docs/servicediscovery/httpnamespace/
# ---------------------------------------------------------------------------------------
service_connect_namespace = aws.servicediscovery.PrivateDnsNamespace(
    "service-connect-namespace",
    name=SERVICE_CONNECT_NAMESPACE_NAME,
    description=SERVICE_CONNECT_NAMESPACE_DESCRIPTION,
    vpc=vpc_id,
    tags=TAGS,
)

# ---------------------------------------------------------------------------------------
# ecs cluster
# https://www.pulumi.com/registry/packages/aws/api-docs/ecs/cluster/
# ---------------------------------------------------------------------------------------
cluster = aws.ecs.Cluster(
    "ecs-cluster",
    name=f"cluster-{STACK}",
    settings=[
        aws.ecs.ClusterSettingArgs(
            name="containerInsights",
            value=container_insights,
        )
    ]
    if container_insights
    else None,
    service_connect_defaults=aws.ecs.ClusterServiceConnectDefaultsArgs(
        namespace=service_connect_namespace.arn
    ),
    tags=TAGS,
)

# ---------------------------------------------------------------------------------------
# cluster capacity providers
# https://www.pulumi.com/registry/packages/aws/api-docs/ecs/clustercapacityproviders/
# This configuration allows for some cost savings by provisioning capacity as follows:
# for a given task, first create 1 instance of it on FARGATE, then for every 1 FARGATE
# instance, create up to 4 FARGATE_SPOT instances as more capacity is needed
# ---------------------------------------------------------------------------------------
cluster_capacity_providers = aws.ecs.ClusterCapacityProviders(
    "cluster-capacity-providers",
    cluster_name=cluster.name,
    capacity_providers=["FARGATE", "FARGATE_SPOT"],
    default_capacity_provider_strategies=[
        aws.ecs.ClusterCapacityProvidersDefaultCapacityProviderStrategyArgs(
            base=fargate_base,
            weight=fargate_weight,
            capacity_provider="FARGATE",
        ),
        aws.ecs.ClusterCapacityProvidersDefaultCapacityProviderStrategyArgs(
            weight=fargate_spot_weight,
            capacity_provider="FARGATE_SPOT",
        ),
    ],
)

# ---------------------------------------------------------------------------------------
# shared resources for tasks
# ---------------------------------------------------------------------------------------
# Task security group
task_shared_security_group = aws.ec2.SecurityGroup(
    "task-security-group",
    description="Shared security group for tasks in this cluster",
    vpc_id=vpc_id,
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
            ipv6_cidr_blocks=["::/0"],
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="tcp",
            from_port=0,
            to_port=65535,
            cidr_blocks=["0.0.0.0/0"],
            ipv6_cidr_blocks=["::/0"],
        )
    ],
)

# Execution role
# Allows any task that use this role to get Aurora DB creds and create/put cloudwatch logs
task_shared_execution_role = aws.iam.Role(
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
    inline_policies=[
        aws.iam.RoleInlinePolicyArgs(
            name="put-logs",
            policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["logs:CreateLogGroup", "logs:PutLogEvents"],
                            "Effect": "Allow",
                            "Resource": "*",
                        }
                    ],
                }
            ),
        ),
        db_credentials_secret_arn.apply(
            lambda arn: aws.iam.RoleInlinePolicyArgs(
                name="get-db-secrets",
                policy=json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Action": ["secretsmanager:GetSecretValue"],
                                "Effect": "Allow",
                                "Resource": arn,
                            }
                        ],
                    }
                ),
            ),
        ),
    ],
)

rpa = aws.iam.RolePolicyAttachment(
    "task-execution-rpa",
    role=task_shared_execution_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
)

pulumi.export("cluster_arn", cluster.arn)
pulumi.export("service_namespace_arn", service_connect_namespace.arn)
pulumi.export("task_shared_security_group_id", task_shared_security_group.id)
pulumi.export("task_shared_execution_role_arn", task_shared_execution_role.arn)
