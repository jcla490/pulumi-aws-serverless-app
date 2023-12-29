"""
ecs

Creates an ECS cluster on AWS Fargate
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

SERVICE_CONNECT_NAMESPACE_NAME = "orangejuice"
SERVICE_CONNECT_NAMESPACE_DESCRIPTION = (
    f"Services supporting {SERVICE_CONNECT_NAMESPACE_NAME}"
)

# Stack references
vpc = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/vpc/{STACK}")
vpc_id = vpc.require_output("vpc_id")

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

pulumi.export("cluster_arn", cluster.arn)
pulumi.export("service_namespace_arn", service_connect_namespace.arn)
