"""
github

Creates an OIDC provider/role for GitHub Actions
"""
import json
import os

import pulumi
import pulumi_aws as aws
import pulumi_github as github

# ---------------------------------------------------------------------------------------
# Project config
# ---------------------------------------------------------------------------------------
STACK = pulumi.get_stack()
PROJECT_NAME = pulumi.get_project()
TAGS = {
    "environment": STACK,
    "project": PROJECT_NAME,
}

ORG_NAME = os.getenv("ORG_NAME")

# Environment specific config
CONFIG = pulumi.Config()

# ---------------------------------------------------------------------------------------
# IAM OIDC provider
# https://www.pulumi.com/registry/packages/aws-native/api-docs/iam/oidcprovider/
# ---------------------------------------------------------------------------------------
github_oidc_provider = aws.iam.OpenIdConnectProvider(
    "github",
    thumbprint_lists=["6938fd4d98bab03faadb97b34396831e3780aea1"],
    client_id_lists=[
        "sts.amazonaws.com",
        f"https://github.com/{ORG_NAME}/",
    ],
    url="https://token.actions.githubusercontent.com",
    tags=TAGS,
)

# ---------------------------------------------------------------------------------------
# IAM role
# https://www.pulumi.com/registry/packages/aws-native/api-docs/iam/role/
# ---------------------------------------------------------------------------------------
role = aws.iam.Role(
    "github-actions-role",
    description="Pulumi continuous delivery via GitHub Actions",
    assume_role_policy=github_oidc_provider.arn.apply(
        lambda arn: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": ["sts:AssumeRoleWithWebIdentity"],
                        "Effect": "Allow",
                        "Condition": {
                            "ForAllValues:StringLike": {
                                "token.actions.githubusercontent.com:sub": f"repo:{ORG_NAME}/*"  # allow access from all repos
                            }
                        },
                        "Principal": {"Federated": [arn]},
                    }
                ],
            }
        )
    ),
    managed_policy_arns=[
        aws.iam.ManagedPolicy.ADMINISTRATOR_ACCESS,  # pulumi needs full access
    ],
    max_session_duration=7200,
    tags=TAGS,
)

# ---------------------------------------------------------------------------------------
# GitHub organization secrets
# https://www.pulumi.com/registry/packages/github/api-docs/actionsorganizationsecret/
# ---------------------------------------------------------------------------------------

# USE THIS RESOURCE ONLY IF CONFIGURING AN ORG-WIDE SECRET
# aws_role_access_secret = github.ActionsOrganizationSecret(
#     "aws-oidc-role-secret",
#     secret_name=f"AWS_OIDC_{STACK}_ACCESS_ROLE",
#     plaintext_value=role.arn,
#     visibility="all",
#     opts=pulumi.ResourceOptions(delete_before_replace=True),
# )

# Use for a specific repo or individual user config
public_key = github.get_actions_public_key(repository="pulumi-aws-serverless-bootstrap")

aws_role_access_secret = github.ActionsSecret(
    "aws-oidc-role-secret",
    repository="pulumi-aws-serverless-bootstrap",
    secret_name=f"AWS_OIDC_{STACK}_ACCESS_ROLE",
    plaintext_value=role.arn,
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)
