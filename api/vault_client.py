import os
import hvac


VAULT_ADDR = os.getenv(
    "VAULT_ADDR",
    "http://vault:8200"
)

VAULT_TOKEN = os.getenv(
    "VAULT_TOKEN"
)

VAULT_SECRET_PATH = os.getenv(
    "VAULT_SECRET_PATH",
    "secret/data/report-platform"
)


def get_vault_client():

    client = hvac.Client(
        url=VAULT_ADDR,
        token=VAULT_TOKEN
    )

    if not client.is_authenticated():
        raise RuntimeError(
            "Vault authentication failed"
        )

    return client


def get_secrets():

    client = get_vault_client()

    # KV v2
    response = client.secrets.kv.v2.read_secret_version(
        path="report-platform",
        mount_point="secret"
    )

    return response["data"]["data"]