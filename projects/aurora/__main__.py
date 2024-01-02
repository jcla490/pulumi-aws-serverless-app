"""
aurora

Creates a serverless Aurora Postgres cluster

NOTE: We create this db in public subnets with a public ip. It would be better to set this to private sudnets and disable public accessibility on the cluster instances, then use a VPN to interact with the DB locally.
"""
import json
import os

import pulumi
import pulumi_aws as aws
import pulumi_random as random

# ---------------------------------------------------------------------------------------
# Project config
# ---------------------------------------------------------------------------------------
STACK = pulumi.get_stack()
PROJECT_NAME = pulumi.get_project()
TAGS = {
    "environment": STACK,
    "project": PROJECT_NAME,
}

DB_IDENTIFIER = "orangejuicedb"
DB_USERNAME = "db_admin"

# Stack references
vpc = pulumi.StackReference(f"{os.getenv('ORG_NAME')}/vpc/{STACK}")
vpc_id = vpc.require_output("vpc_id")
public_subnet_ids = vpc.require_output("public_subnet_ids")
private_subnet_ids = vpc.require_output("private_subnet_ids")

# Environment specific config
CONFIG = pulumi.Config()
engine_version = CONFIG.require("engine_version")
backup_retention_period = CONFIG.require_int("backup_retention_period")
min_capacity = CONFIG.require("min_capacity")
max_capacity = CONFIG.require("max_capacity")
instance_count = CONFIG.require_int("instance_count")
performance_insights_enabled = CONFIG.require_bool("performance_insights_enabled")
performance_insights_retention_period = CONFIG.require_int(
    "performance_insights_retention_period"
)

# Public access security group
# This is not needed if securing database in VPC
security_group = aws.ec2.SecurityGroup(
    "db-security-group",
    description="Database security group",
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
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
            ipv6_cidr_blocks=["::/0"],
        )
    ],
)


# ---------------------------------------------------------------------------------------
# aurora cluster
# https://www.pulumi.com/registry/packages/aws/api-docs/rds/cluster/
# ---------------------------------------------------------------------------------------
# Create a database password
db_password = random.RandomPassword(
    "db-password", length=32, special=True, override_special="!#$%&*()-_=+[]{}<>:?"
)


# Associate VPC private subnets with database
# private_db_subnet_group = aws.rds.SubnetGroup(
#     "private-db-subnet-group", subnet_ids=private_subnet_ids, tags=TAGS
# )

public_db_subnet_group = aws.rds.SubnetGroup(
    "public-db-subnet-group", subnet_ids=public_subnet_ids, tags=TAGS
)

# Cluster creation
aurora_cluster = aws.rds.Cluster(
    "aurora-cluster",
    apply_immediately=True,
    cluster_identifier=f"{DB_IDENTIFIER}-cluster",
    engine="aurora-postgresql",
    engine_mode="provisioned",
    engine_version=engine_version,
    db_subnet_group_name=public_db_subnet_group.name,
    database_name=DB_IDENTIFIER,
    master_username=DB_USERNAME,
    master_password=db_password.result,
    backup_retention_period=backup_retention_period,
    serverlessv2_scaling_configuration=aws.rds.ClusterServerlessv2ScalingConfigurationArgs(
        min_capacity=min_capacity,
        max_capacity=max_capacity,
    ),
    copy_tags_to_snapshot=True,
    preferred_backup_window="04:00-06:00",
    preferred_maintenance_window="sun:02:00-sun:04:00",
    skip_final_snapshot=False,
    final_snapshot_identifier=f"{DB_IDENTIFIER}-final-snapshot",
    vpc_security_group_ids=[security_group.id],
    tags=TAGS,
)

# Instance creation
for i in range(instance_count):
    aurora_instance = aws.rds.ClusterInstance(
        f"cluster-instance-{i}",
        identifier=f"{DB_IDENTIFIER}-{i}",
        cluster_identifier=aurora_cluster.id,
        instance_class="db.serverless",
        engine=aurora_cluster.engine,
        engine_version=aurora_cluster.engine_version,
        performance_insights_enabled=performance_insights_enabled,
        performance_insights_retention_period=performance_insights_retention_period
        if performance_insights_enabled
        else None,
        publicly_accessible=True,  # set to False if using VPN to access VPC
        tags=TAGS,
    )

# Database credentials secret
db_credentials_payload = pulumi.Output.all(
    aurora_cluster.endpoint, aurora_cluster.reader_endpoint, db_password.result
).apply(
    lambda args: json.dumps(
        {
            "CLUSTER_IDENTIFIER": f"{DB_IDENTIFIER}-cluster",
            "DATABASE_NAME": DB_IDENTIFIER,
            "WRITER_ENDPOINT": args[0],
            "READER_ENDPOINT": args[1],
            "USERNAME": DB_USERNAME,
            "PASSWORD": args[2],
            "ENGINE": "postgres",
            "PORT": 5432,
        }
    )
)

db_creds_secret = aws.secretsmanager.Secret(
    "database-credentials-secret",
    name=f"{DB_IDENTIFIER}-creds",
    opts=pulumi.ResourceOptions(depends_on=aurora_cluster),
)

db_creds_secret_version = aws.secretsmanager.SecretVersion(
    "database-credentials-secret-version",
    secret_id=db_creds_secret.id,
    secret_string=db_credentials_payload,
)

pulumi.export(f"{DB_IDENTIFIER}_credentials_secret_arn", db_creds_secret.arn)
