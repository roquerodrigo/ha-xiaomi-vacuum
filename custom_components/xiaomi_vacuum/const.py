"""
Model-agnostic constants for xiaomi_vacuum.

Everything that varies between supported vacuum models (MIoT property/action
mapping, status tables, enumerations) lives in
:mod:`custom_components.xiaomi_vacuum.spec`.
This module holds only the integration-level constants (domain, config keys,
cloud regions) that are independent of which Xiaomi vacuum is connected.
"""

from __future__ import annotations

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "xiaomi_vacuum"

CONF_HOST = "host"
CONF_TOKEN = "token"  # noqa: S105
CONF_NAME = "name"
CONF_CLOUD_COUNTRY = "cloud_country"
CONF_CLOUD_SSECURITY = "cloud_ssecurity"
CONF_CLOUD_SERVICE_TOKEN = "cloud_service_token"  # noqa: S105
CONF_CLOUD_USER_ID = "cloud_user_id"
CONF_DEVICE_INFO = "device_info"

# Xiaomi cloud server regions the account can live in. The device is only found
# on the server matching its region, so the user picks this at setup. Codes map
# to `_api_url` hosts (e.g. "de" -> https://de.api.io.mi.com). Friendly labels
# live in translations under `selector.cloud_country.options`.
CLOUD_REGIONS: tuple[str, ...] = ("de", "us", "cn", "ru", "sg", "i2", "tw")
DEFAULT_CLOUD_REGION = "us"

ISSUE_CANNOT_CONNECT = "cannot_connect"
ISSUE_UNSUPPORTED_MODEL = "unsupported_model"

# Vacuum models discovered in the cloud are matched by this prefix (see
# config_flow); the per-model MIoT spec lives in `spec.MODELS`. Adding a new
# model means adding a `ModelSpec` entry there.
VACUUM_MODEL_PREFIX = "xiaomi.vacuum."

# Fault codes are large device-specific numbers (e.g. 210009) with no published
# code->text table anywhere in Xiaomi's ecosystem. The localized, human-readable
# text is delivered by the Xiaomi cloud as a device message (see
# cloud.XiaomiCloud.async_fault_text); the coordinator resolves it into "fault_text".
