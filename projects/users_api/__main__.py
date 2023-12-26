"""
example_users_microservice

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

# Stack references
vpc = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/vpc/{STACK}")
vpc_id = vpc.require_output("vpc_id")

ecs = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/ecs_fargate/{STACK}")
cluster_arn = ecs.require_output("cluster_arn")
lb_default_target_group = ecs.require_output("cluster_load_balancer_target_group")

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
    context="./api",
    platform="linux/amd64",
)

# ---------------------------------------------------------------------------------------
# ECS task
# https://www.pulumi.com/registry/packages/awsx/api-docs/ecs/fargateservice
# ---------------------------------------------------------------------------------------
# Execution role for task
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

# ECS task + service
service = awsx.ecs.FargateService(
    "fargate-service",
    awsx.ecs.FargateServiceArgs(
        name=PROJECT_NAME,
        cluster=cluster_arn,
        desired_count=1,
        assign_public_ip=True,
        task_definition_args=awsx.ecs.FargateServiceTaskDefinitionArgs(
            task_role=task_execution_role,
            container=awsx.ecs.TaskDefinitionContainerDefinitionArgs(
                name=PROJECT_NAME,
                cpu=2048,
                memory=2048,
                image=app_image.image_uri,
                essential=True,
                port_mappings=[
                    awsx.ecs.TaskDefinitionPortMappingArgs(
                        container_port=80,
                        target_group=lb_default_target_group,
                    )
                ],
            ),
        ),
    ),
)
