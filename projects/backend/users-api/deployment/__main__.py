"""
users_api

Creates ECS tasks and services for a basic CRUD users service
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
AWS_REGION = aws.get_region().name

# Stack references
vpc = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/vpc/{STACK}")
vpc_id = vpc.require_output("vpc_id")
public_subnet_ids = vpc.require_output("public_subnet_ids")

ecs = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/ecs/{STACK}")
cluster_arn = ecs.require_output("cluster_arn")
task_shared_security_group_id = ecs.require_output("task_shared_security_group_id")
task_shared_execution_role_arn = ecs.require_output("task_shared_execution_role_arn")

load_balancer = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/load_balancer/{STACK}")
target_group_arn = load_balancer.require_output("target_group_arn")

aurora = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/aurora/{STACK}")
db_credentials_secret_arn = aurora.require_output(
    "orangejuicedb_credentials_secret_arn"
)

# Environment specific config
CONFIG = pulumi.Config()

# ---------------------------------------------------------------------------------------
# ECR
# https://www.pulumi.com/registry/packages/aws/api-docs/ecr/
# ---------------------------------------------------------------------------------------
# Create repo
image_repo = aws.ecr.Repository("repo", force_delete=True)

# Add lifecycle policies to each repo
aws.ecr.LifecyclePolicy(
    "repo-lifecycle-policy",
    repository=image_repo.name,
    policy="""{
    "rules": [
        {
            "rulePriority": 1,
            "description": "Keep only the last 3 images",
            "selection": {
                "tagStatus": "any",
                "countType": "imageCountMoreThan",
                "countNumber": 3
            },
            "action": {
                "type": "expire"
            }
        }
    ]
}
""",
)

# App image
app_image = awsx.ecr.Image(
    "app-image",
    repository_url=image_repo.repository_url,
    context="../",
    platform="linux/amd64",
)

# ---------------------------------------------------------------------------------------
# ECS task definition
# https://www.pulumi.com/registry/packages/aws/api-docs/ecs/taskdefinition/
# ---------------------------------------------------------------------------------------
task_definition = aws.ecs.TaskDefinition(
    "task-definition",
    container_definitions=pulumi.Output.all(
        app_image.image_uri, db_credentials_secret_arn
    ).apply(
        lambda args: json.dumps(
            [
                {
                    "name": PROJECT_NAME,
                    "image": args[0],
                    "essential": True,
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": f"/ecs/{PROJECT_NAME}",
                            "awslogs-region": AWS_REGION,
                            "awslogs-stream-prefix": "ecs",
                            "awslogs-create-group": "true",
                        },
                    },
                    "secrets": [
                        {
                            "valueFrom": args[1],
                            "name": "DATABASE_CREDENTIALS",
                        }
                    ],
                    "portMappings": [{"containerPort": 80, "protocol": "tcp"}],
                }
            ]
        )
    ),
    cpu=256,
    memory=512,
    execution_role_arn=task_shared_execution_role_arn,
    family="users_api",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    runtime_platform=aws.ecs.TaskDefinitionRuntimePlatformArgs(
        cpu_architecture="X86_64", operating_system_family="LINUX"
    ),
    tags=TAGS,
)

# ---------------------------------------------------------------------------------------
# ECS service
# https://www.pulumi.com/registry/packages/aws/api-docs/ecs/service/
# ---------------------------------------------------------------------------------------
service = aws.ecs.Service(
    "service",
    name=PROJECT_NAME,
    cluster=cluster_arn,
    task_definition=task_definition.arn,
    desired_count=2,
    launch_type="FARGATE",
    health_check_grace_period_seconds=60,
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
        subnets=public_subnet_ids,
        assign_public_ip=True,
        security_groups=[task_shared_security_group_id],
    ),
    load_balancers=[
        aws.ecs.ServiceLoadBalancerArgs(
            target_group_arn=target_group_arn,
            container_name=PROJECT_NAME,
            container_port=80,
        )
    ],
    tags=TAGS,
)
