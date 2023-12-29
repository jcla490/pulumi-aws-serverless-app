# pulumi-aws-serverless-bootstrap

This repo is a useful template for creating a modern web app on AWS. The premise of the app in this example is silly: a [review site](https://orangejuice.reviews) allowing users to rate and discuss their favorite orange juice brands. We'll use this light-hearted example to create a robust bit of infrastructure that can be reused in your *more serious* applications.

** Features **
- Infrastructure is deployed using [Pulumi](https://www.pulumi.com/), a more modern alternative to Terraform
- AWS resources are serverless (read: cost efficient) where possible and deployed in simple but production-ready forms
- The backend is comprised of Dockerized microservices written in python/[litestar](https://litestar.dev/) and deployed to ECS
- Backend services are load balanced and secured, using [Service Connect](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-connect.html) to communicate
- GitHub Actions is configured for CI/CD

Since the primary focus here is infrastructure, this example leaves out a few things that you should consider on your own:

- Frontend frameworks and styling
- Microservices tooling and testing
- True multi-environment/account deployment (omitted to save me $$$, although I do provide reasonable values for dev/prod in each Pulumi project config)

## Developer setup

## Projects

| Project 	                                      | Description 	                    |
|------------------------------------------------ |------------------------------------ |
| [aurora](projects/aurora/)                      | Aurora Serverless v2 Postgres DB    |
| [certificates](projects/certificates/)          | SSL/TLS certificates for domain     |
| [ecs](projects/ecs)                             | ECS cluster on AWS Fargate          |
| [github](projects/github)                       | GitHub Actions AWS role/provider    |
| [load_balancer](projects/load_balancer/)        | Load balancer for front-end traffic |
| [vpc](projects/vpc)                             | A typical VPC            	        |
