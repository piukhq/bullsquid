# Auth0 Terraform Configuration

This directory contains the Terraform configuration for the Portal Auth0 tenant.

> [!IMPORTANT]
> As of 2023-09-26 there are some outstanding issues with the Auth0 Terraform provider. As such this configuration cannot completely configure a new tenant. It serves as a way to get 90% of the way there, but manual changes are required to complete the configuration. The primary changes required are configuring the tenant's custom domain, and configuring roles for the API.