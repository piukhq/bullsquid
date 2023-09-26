terraform {
  required_providers {
    auth0 = {
      source  = "auth0/auth0"
      version = "~> 0.50.0"
    }
  }
}

# tenant domain, client ID, and secret should be provided with env vars
provider "auth0" {}

# TODO: manage tenant details?
# https://registry.terraform.io/providers/auth0/auth0/latest/docs/resources/tenant

# TODO: figure out roles/permissions per-organization

resource "auth0_custom_domain" "bink" {
    domain = "auth.gb.bink.com"
    type = "auth0_managed_certs"
}

resource "auth0_organization" "bink" {
    name = "bink"
    display_name = "Bink"
    branding {
        logo_url = "https://res.cloudinary.com/dj6h2yjtf/image/upload/v1687422219/logo-primary_gyev44-2_pvsupa.png"
        colors = {
            primary = "#5BE0CA"
            page_background = "#EBFFFD"
        }
    }
}

resource "auth0_connection" "aad" {
    name = "AzureAD-Bink"
    strategy = "waad"
    display_name = "Bink"
    show_as_button = true
    options {
        client_id = "TODO"
        client_secret = "TODO"
        domain = "bink.com"
        domain_aliases = ["bink.com"]
        tenant_domain = "bink.com"
        identity_api = "microsoft-identity-platform-v2.0"
        set_user_root_attributes = "on_each_login"
        should_trust_email_verified_connection = "always_set_emails_as_verified"
        waad_protocol = "openid-connect"
    }
}

resource "auth0_organization_connections" "bink" {
    organization_id = auth0_organization.bink.id
    enabled_connections {
        connection_id = auth0_connection.aad.id
        assign_membership_on_login = true
    }
}

resource "auth0_resource_server" "bullsquid" {
    identifier = "https://portal.bink.com"
    allow_offline_access = true
    enforce_policies = true
    name = "Portal"
    signing_alg = "RS256"
    skip_consent_for_verifiable_first_party_clients = true
    token_dialect = "access_token_authz"
    token_lifetime = 86400
    token_lifetime_for_web = 86400
}

resource "auth0_resource_server_scopes" "bullsquid_scopes" {
  resource_server_identifier = auth0_resource_server.bullsquid.identifier

  scopes {
    name = "merchant_data:ro"
    description = "Read Merchant Data"
  }
  scopes {
    name = "merchant_data:rw"
    description = "Create, Read, and Update Merchant Data"
  }
  scopes {
    name = "merchant_data:rwd"
    description = "Create, Read, Update, and Delete Merchant Data"
  }
  scopes {
    name = "customer_wallet:ro"
    description = "Read Customer Wallet"
  }
  scopes {
    name = "customer_wallet:rw"
    description = "Create, Read, and Update Customer Wallet"
  }
  scopes {
    name = "customer_wallet:rwd"
    description = "Create, Read, Update, and Delete Customer Wallet"
  }
}

resource "auth0_role" "bullsquid_role_cw_admin" {
  name = "Admin (Customer Wallet)"
  description = "Read, edit, and delete customer wallet data."
}

resource "auth0_role_permissions" "bullsquid_role_cw_admin_permissions" {
    role_id = auth0_role.bullsquid_role_cw_admin.id
    permissions {
        name = "customer_wallet:ro"
        resource_server_identifier = auth0_resource_server.bullsquid.identifier
    }
    permissions {
        name = "customer_wallet:rw"
        resource_server_identifier = auth0_resource_server.bullsquid.identifier
    }
    permissions {
        name = "customer_wallet:rwd"
        resource_server_identifier = auth0_resource_server.bullsquid.identifier
    }
}

resource "auth0_role" "bullsquid_role_md_admin" {
    name = "Admin (Merchant Data)"
    description = "Read, edit, and delete merchant data."
}

resource "auth0_role_permissions" "bullsquid_role_md_admin_permissions" {
    role_id = auth0_role.bullsquid_role_md_admin.id
    permissions {
        name = "merchant_data:ro"
        resource_server_identifier = auth0_resource_server.bullsquid.identifier
    }
    permissions {
        name = "merchant_data:rw"
        resource_server_identifier = auth0_resource_server.bullsquid.identifier
    }
    permissions {
        name = "merchant_data:rwd"
        resource_server_identifier = auth0_resource_server.bullsquid.identifier
    }
}

resource "auth0_role" "bullsquid_role_cw_editor" {
  name = "Editor (Customer Wallet)"
  description = "Read and edit customer wallet data."
}

resource "auth0_role_permissions" "bullsquid_role_cw_editor_permissions" {
    role_id = auth0_role.bullsquid_role_cw_editor.id
    permissions {
        name = "customer_wallet:ro"
        resource_server_identifier = auth0_resource_server.bullsquid.identifier
    }
    permissions {
        name = "customer_wallet:rw"
        resource_server_identifier = auth0_resource_server.bullsquid.identifier
    }
}

resource "auth0_role" "bullsquid_role_md_editor" {
    name = "Editor (Merchant Data)"
    description = "Read and edit merchant data."
}

resource "auth0_role_permissions" "bullsquid_role_md_editor_permissions" {
    role_id = auth0_role.bullsquid_role_md_editor.id
    permissions {
        name = "merchant_data:ro"
        resource_server_identifier = auth0_resource_server.bullsquid.identifier
    }
    permissions {
        name = "merchant_data:rw"
        resource_server_identifier = auth0_resource_server.bullsquid.identifier
    }
}

resource "auth0_role" "bullsquid_role_cw_reader" {
  name = "Reader (Customer Wallet)"
  description = "Read customer wallet data without modifying it."
}

resource "auth0_role_permissions" "bullsquid_role_cw_reader_permissions" {
    role_id = auth0_role.bullsquid_role_cw_reader.id
    permissions {
        name = "customer_wallet:ro"
        resource_server_identifier = auth0_resource_server.bullsquid.identifier
    }
}

resource "auth0_role" "bullsquid_role_md_reader" {
    name = "Reader (Merchant Data)"
    description = "Read merchant data without modifying it."
}

resource "auth0_role_permissions" "bullsquid_role_md_reader_permissions" {
    role_id = auth0_role.bullsquid_role_md_reader.id
    permissions {
        name = "merchant_data:ro"
        resource_server_identifier = auth0_resource_server.bullsquid.identifier
    }
}

resource "auth0_client" "aperture" {
    name = "Aperture"
    description = "Portal frontend application"
    app_type = "spa"
    allowed_logout_urls = [
        "http://localhost:3000",
        "https://portal.dev.gb.bink.com",
        "https://portal.staging.gb.bink.com",
        "https://oauth.pstmn.io/v1/callback",
    ]
    web_origins = [
        "http://localhost:3000",
        "https://portal.dev.gb.bink.com",
        "https://portal.staging.gb.bink.com",
        "https://oauth.pstmn.io",
        "http://aperture.portal",
    ]
    callbacks = [
        "http://localhost:3000/api/auth/callback",
        "https://portal.dev.gb.bink.com/api/auth/callback",
        "https://portal.staging.gb.bink.com/api/auth/callback",
        "https://oauth.pstmn.io/v1/callback",
    ]
    grant_types = [
        "authorization_code",
        "implicit",
        "refresh_token",
    ]
    organization_usage = "require"
    organization_require_behavior = "pre_login_prompt"
    custom_login_page_on = true
    is_first_party = true
    jwt_configuration {
        alg = "RS256"
        lifetime_in_seconds = 36000
        secret_encoded = false
        scopes = {}
    }
    oidc_conformant = true
}
