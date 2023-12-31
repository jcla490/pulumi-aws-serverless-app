"""
certificates

Creates needed SSL/TLS certificates
"""

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

# Environment specific config
CONFIG = pulumi.Config()
domain_name = CONFIG.require("domain")
hosted_zone_id = CONFIG.require("hosted_zone_id")

# ---------------------------------------------------------------------------------------
# Certificate
# https://www.pulumi.com/registry/packages/aws/api-docs/acm/certificate/
# ---------------------------------------------------------------------------------------
certificate = aws.acm.Certificate(
    "certificate",
    domain_name=domain_name,
    subject_alternative_names=[f"*.{domain_name}"],
    validation_method="DNS",
    tags=TAGS,
)

# Validation record
wildcard_validation_record = aws.route53.Record(
    "wildcard-validation-record",
    name=certificate.domain_validation_options[0].resource_record_name,
    records=[certificate.domain_validation_options[0].resource_record_value],
    ttl=300,
    type=certificate.domain_validation_options[0].resource_record_type,
    zone_id=hosted_zone_id,
    opts=pulumi.ResourceOptions(parent=certificate),
)

# Validation object
cert_validation = aws.acm.CertificateValidation(
    "domain-cert-validation",
    certificate_arn=certificate.arn,
    validation_record_fqdns=[wildcard_validation_record.fqdn],
    opts=pulumi.ResourceOptions(
        parent=certificate,
    ),
)

pulumi.export("root_domain_certificate_arn", cert_validation.certificate_arn)
