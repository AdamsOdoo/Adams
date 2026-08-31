"""Immutable contracts used by the unwired P11 subscription planner.

This module contains values and validation only.  It has no Odoo, transport,
credential, persistence or retry dependency.  Callback URLs are accepted by
the planner only long enough to calculate a digest; these contracts never
store one.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from shopify_connector_core.integration.shopify.mutation_contracts import MAX_MUTATION_TEXT

from .webhook_subscription_mutation_gateway import (
    SHOPIFY_API_VERSION,
    WEBHOOK_SUBSCRIPTION_CREATE_OPERATION,
    WEBHOOK_SUBSCRIPTION_DELETE_OPERATION,
    WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY,
)


MAX_TOPIC_SPECS = 128
MAX_CURRENT_SUBSCRIPTIONS = 2_000
MAX_GRANTED_SCOPES = 256
MAX_REQUIRED_SCOPES = 64
MAX_INCLUDE_FIELDS = 128
MAX_SCOPE_LENGTH = 128
MAX_TOPIC_LENGTH = 128
MAX_FORMAT_LENGTH = 32
MAX_API_VERSION_LENGTH = 32
MAX_GID_LENGTH = 256
MAX_URI_LENGTH = 4_096

_TOPIC = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_API_VERSION = re.compile(r"^[0-9]{4}-[0-9]{2}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_GID = re.compile(r"^gid://shopify/WebhookSubscription/[1-9][0-9]*$")
_SCOPE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:/-]{0,127}$")
_FIELD = re.compile(r"^[^\s]{1,128}$")
# Shopify currently expects the JSON format, but a read can legitimately
# report another enum value (for example a legacy XML subscription).  Keep
# the observation structurally inspectable so the planner can replace an
# owned unsupported value; malformed/whitespace values remain blocked.
_FORMAT = re.compile(r"^[A-Z][A-Z0-9_]{0,31}$")
_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
ACTION_ORDER = {"block": 0, "keep": 1, "delete": 2, "create": 3}


class WebhookSubscriptionPlannerError(ValueError):
    """A desired/current value cannot be safely used by the planner."""

    def __init__(self, code: str, message: str) -> None:
        if not isinstance(code, str) or not _ERROR_CODE.fullmatch(code):
            raise ValueError("planner error code must be a safe lowercase token")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("planner error message must be non-empty")
        self.code = code
        self.message = message[:MAX_MUTATION_TEXT]
        super().__init__(self.message)


def fail(code: str, message: str) -> None:
    raise WebhookSubscriptionPlannerError(code, message)


def bounded_items(value: Any, field_name: str, maximum: int) -> list[Any]:
    if isinstance(value, (str, bytes, Mapping)):
        fail("invalid_input", f"{field_name} must be a bounded sequence.")
    try:
        iterator = iter(value)
    except TypeError as exc:
        raise WebhookSubscriptionPlannerError(
            "invalid_input", f"{field_name} must be a bounded sequence."
        ) from exc
    result: list[Any] = []
    for item in iterator:
        if len(result) >= maximum:
            fail("input_too_large", f"{field_name} exceeds its safety bound.")
        result.append(item)
    return result


def strings(
    value: Iterable[str] | None,
    field_name: str,
    *,
    maximum: int,
    max_length: int,
    pattern: re.Pattern[str] | None = None,
) -> tuple[str, ...]:
    if value is None:
        return ()
    result: set[str] = set()
    for item in bounded_items(value, field_name, maximum):
        if not isinstance(item, str) or not item or len(item) > max_length:
            fail("invalid_input", f"{field_name} contains an invalid value.")
        if item != item.strip() or (pattern is not None and not pattern.fullmatch(item)):
            fail("invalid_input", f"{field_name} contains an invalid value.")
        result.add(item)
    return tuple(sorted(result))


def fields(value: Iterable[str] | None, field_name: str = "include_fields") -> tuple[str, ...]:
    return strings(value, field_name, maximum=MAX_INCLUDE_FIELDS, max_length=128, pattern=_FIELD)


def scopes(
    value: Iterable[str] | None,
    field_name: str = "scopes",
    *,
    maximum: int = MAX_REQUIRED_SCOPES,
) -> tuple[str, ...]:
    return strings(value, field_name, maximum=maximum, max_length=MAX_SCOPE_LENGTH, pattern=_SCOPE)


def topic(value: Any, field_name: str = "topic") -> str:
    if not isinstance(value, str) or not _TOPIC.fullmatch(value):
        fail("invalid_topic", f"{field_name} must be a Shopify webhook topic enum.")
    return value


def api_version(value: Any, field_name: str = "api_version") -> str:
    if not isinstance(value, str) or not _API_VERSION.fullmatch(value):
        fail("invalid_api_version", f"{field_name} must use YYYY-MM.")
    return value


def digest(value: Any, field_name: str = "callback_uri_digest") -> str:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        fail("invalid_callback_identity", f"{field_name} must be lowercase SHA-256.")
    return value


def gid(value: Any, field_name: str = "subscription_gid") -> str:
    if not isinstance(value, str) or len(value) > MAX_GID_LENGTH or not _GID.fullmatch(value):
        fail("invalid_subscription_identity", f"{field_name} must be a canonical Shopify GID.")
    return value


def safe_api(value: Any, field_name: str = "observed_api_version") -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_API_VERSION_LENGTH:
        fail("invalid_observation", f"{field_name} must be a bounded value.")
    return value


def safe_format(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_FORMAT_LENGTH:
        fail("invalid_observation", "observed format must be a bounded value.")
    return value


def callback_digest(*, callback_uri: str | None, callback_uri_digest: str | None) -> str:
    if callback_uri is None and callback_uri_digest is None:
        fail("missing_callback_identity", "A callback URI or its digest is required.")
    computed: str | None = None
    if callback_uri is not None:
        if (
            not isinstance(callback_uri, str)
            or not callback_uri
            or len(callback_uri) > MAX_URI_LENGTH
            or not callback_uri.startswith("https://")
        ):
            fail("invalid_callback_identity", "The callback identity must be an HTTPS URI.")
        computed = hashlib.sha256(callback_uri.encode("utf-8")).hexdigest()
    if callback_uri_digest is not None:
        supplied = digest(callback_uri_digest)
        if computed is not None and supplied != computed:
            fail("callback_identity_mismatch", "The callback URI and digest do not match.")
        return supplied
    return computed or ""


def fields_match(expected: tuple[str, ...], observed: tuple[str, ...]) -> bool:
    # Empty Shopify includeFields means unfiltered and satisfies V1's
    # required-field contract; a non-empty filter must contain every required
    # field.  Spaced/malformed values are rejected before this is called.
    return not expected or not observed or set(expected).issubset(observed)


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise WebhookSubscriptionPlannerError(
            "invalid_plan", "The planner could not canonicalize its safe output."
        ) from exc


@dataclass(frozen=True, slots=True)
class WebhookTopicSpec:
    topic: str
    required_scopes: tuple[str, ...] = ()
    include_fields: tuple[str, ...] = ()
    enabled: bool = True
    api_version: str = SHOPIFY_API_VERSION
    format: str = "JSON"

    def __post_init__(self) -> None:
        object.__setattr__(self, "topic", topic(self.topic))
        object.__setattr__(self, "required_scopes", scopes(self.required_scopes, "required_scopes"))
        object.__setattr__(self, "include_fields", fields(self.include_fields))
        if not isinstance(self.enabled, bool):
            fail("invalid_input", "enabled must be a boolean.")
        object.__setattr__(self, "api_version", api_version(self.api_version))
        if self.api_version != SHOPIFY_API_VERSION:
            fail("unsupported_api_version", "Webhook subscriptions use the pinned API version.")
        if self.format != "JSON":
            fail("unsupported_format", "Webhook subscriptions use JSON format.")

    @classmethod
    def from_mapping(cls, topic_name: str, value: Mapping[str, Any]) -> "WebhookTopicSpec":
        if not isinstance(value, Mapping):
            fail("invalid_input", "Topic policy must be an object.")
        return cls(
            topic_name,
            required_scopes=value.get("required_scopes", value.get("scopes", ())),
            include_fields=value.get("include_fields", ()),
            enabled=value.get("enabled", True),
            api_version=value.get("api_version", SHOPIFY_API_VERSION),
            format=value.get("format", "JSON"),
        )


@dataclass(frozen=True, slots=True)
class WebhookSubscriptionDesired:
    topic: str
    callback_uri_digest: str
    expected_api_version: str = SHOPIFY_API_VERSION
    expected_format: str = "JSON"
    expected_include_fields: tuple[str, ...] = ()
    required_scopes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "topic", topic(self.topic))
        object.__setattr__(self, "callback_uri_digest", digest(self.callback_uri_digest))
        object.__setattr__(self, "expected_api_version", api_version(self.expected_api_version))
        if self.expected_api_version != SHOPIFY_API_VERSION:
            fail("unsupported_api_version", "Webhook subscriptions use the pinned API version.")
        if self.expected_format != "JSON":
            fail("unsupported_format", "Webhook subscriptions use JSON format.")
        object.__setattr__(self, "expected_include_fields", fields(self.expected_include_fields))
        object.__setattr__(self, "required_scopes", scopes(self.required_scopes, "required_scopes"))

    @classmethod
    def from_topic(cls, spec: WebhookTopicSpec, callback_uri_digest: str) -> "WebhookSubscriptionDesired":
        return cls(
            spec.topic,
            callback_uri_digest,
            spec.api_version,
            spec.format,
            spec.include_fields,
            spec.required_scopes,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "callback_uri_digest": self.callback_uri_digest,
            "expected_api_version": self.expected_api_version,
            "expected_format": self.expected_format,
            "expected_include_fields": list(self.expected_include_fields),
            "required_scopes": list(self.required_scopes),
        }


@dataclass(frozen=True, slots=True)
class WebhookSubscriptionObserved:
    id: str
    topic: str
    uri_digest: str | None
    observed_api_version: str
    format: str
    include_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", gid(self.id))
        if not isinstance(self.topic, str) or not self.topic or len(self.topic) > MAX_TOPIC_LENGTH:
            fail("invalid_observation", "observed topic must be a bounded value.")
        if self.uri_digest is not None:
            object.__setattr__(self, "uri_digest", digest(self.uri_digest, "observed uri_digest"))
        object.__setattr__(self, "observed_api_version", safe_api(self.observed_api_version))
        object.__setattr__(self, "format", safe_format(self.format))
        object.__setattr__(self, "include_fields", fields(self.include_fields, "observed include_fields"))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WebhookSubscriptionObserved":
        if not isinstance(value, Mapping):
            fail("invalid_observation", "Observed subscription must be an object.")
        if any(
            name in value
            for name in (
                "uri",
                "callbackUrl",
                "callback_uri",
                "callback_url",
                "callbackURL",
                "callbackUri",
                "url",
            )
        ):
            fail("raw_uri_forbidden", "Observed subscription input must contain only a URI digest.")
        uri_digest = value.get("uri_digest")
        # ``to_legacy_dict`` uses False for the absent digest.  It is an
        # unknown identity, never a valid/empty digest and never ownership.
        if uri_digest is False:
            uri_digest = None
        return cls(
            value.get("id"),
            value.get("topic"),
            uri_digest,
            value.get("observed_api_version", value.get("api_version")),
            value.get("format"),
            value.get("include_fields", ()),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "uri_digest": self.uri_digest,
            "observed_api_version": self.observed_api_version,
            "format": self.format,
            "include_fields": list(self.include_fields),
        }


@dataclass(frozen=True, slots=True)
class WebhookSubscriptionDecision:
    key: str
    action: str
    topic: str
    reason_code: str
    desired: WebhookSubscriptionDesired | None = None
    observed: WebhookSubscriptionObserved | None = None
    depends_on: tuple[str, ...] = ()
    ownership: str = "not_applicable"

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key or len(self.key) > 512:
            fail("invalid_plan", "Decision key must be a bounded string.")
        if self.action not in ACTION_ORDER:
            fail("invalid_plan", "Decision action is not supported.")
        if not isinstance(self.topic, str) or not self.topic or len(self.topic) > MAX_TOPIC_LENGTH:
            fail("invalid_plan", "Decision topic must be a bounded string.")
        if not isinstance(self.reason_code, str) or not _ERROR_CODE.fullmatch(self.reason_code):
            fail("invalid_plan", "Decision reason is not a safe code.")
        if self.action == "create" and not isinstance(self.desired, WebhookSubscriptionDesired):
            fail("invalid_plan", "Create decisions require desired state.")
        if self.action == "delete" and not isinstance(self.observed, WebhookSubscriptionObserved):
            fail("invalid_plan", "Delete decisions require observed state.")
        if self.action == "keep" and not isinstance(self.observed, WebhookSubscriptionObserved):
            fail("invalid_plan", "Keep decisions require observed state.")
        if self.desired is not None and not isinstance(self.desired, WebhookSubscriptionDesired):
            fail("invalid_plan", "Decision desired state is malformed.")
        if self.observed is not None and not isinstance(self.observed, WebhookSubscriptionObserved):
            fail("invalid_plan", "Decision observed state is malformed.")
        dependency_values = bounded_items(self.depends_on, "depends_on", MAX_CURRENT_SUBSCRIPTIONS)
        if any(not isinstance(value, str) or not value or len(value) > 512 for value in dependency_values):
            fail("invalid_plan", "Decision dependencies are malformed.")
        object.__setattr__(self, "depends_on", tuple(sorted(set(dependency_values))))
        if self.ownership not in {"connector", "external", "unknown", "not_applicable"}:
            fail("invalid_plan", "Decision ownership is unsupported.")

    @property
    def operation_key(self) -> str | None:
        return {
            "create": WEBHOOK_SUBSCRIPTION_CREATE_OPERATION,
            "delete": WEBHOOK_SUBSCRIPTION_DELETE_OPERATION,
        }.get(self.action)

    @property
    def subscription_gid(self) -> str | None:
        return self.observed.id if self.observed else None

    @property
    def callback_uri_digest(self) -> str | None:
        return self.desired.callback_uri_digest if self.desired else self.observed.uri_digest if self.observed else None

    @property
    def expected_api_version(self) -> str | None:
        return self.desired.expected_api_version if self.desired else None

    @property
    def expected_format(self) -> str | None:
        return self.desired.expected_format if self.desired else None

    @property
    def expected_include_fields(self) -> tuple[str, ...]:
        return self.desired.expected_include_fields if self.desired else ()

    @property
    def observed_api_version(self) -> str | None:
        return self.observed.observed_api_version if self.observed else None

    @property
    def observed_uri_digest(self) -> str | None:
        return self.observed.uri_digest if self.observed else None

    @property
    def observed_format(self) -> str | None:
        return self.observed.format if self.observed else None

    @property
    def observed_include_fields(self) -> tuple[str, ...]:
        return self.observed.include_fields if self.observed else ()

    @property
    def requires_readback(self) -> bool:
        return self.action in {"create", "delete"}

    @property
    def target(self) -> dict[str, Any]:
        if self.action == "create":
            return {
                "topic": self.topic,
                "callback_uri_digest": self.callback_uri_digest,
                "expected_api_version": self.expected_api_version,
                "expected_format": self.expected_format,
                "expected_include_fields": list(self.expected_include_fields),
            }
        if self.action == "delete":
            return {
                "subscription_gid": self.subscription_gid,
                "topic": self.topic,
                "observed_uri_digest": self.observed_uri_digest,
            }
        return {"topic": self.topic}

    @property
    def readback(self) -> dict[str, Any] | None:
        if not self.requires_readback:
            return None
        metadata = WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY.require_operation(self.operation_key or "").readback
        return {
            "operation_key": metadata.operation_key,
            "strategy": metadata.strategy,
            "summary": metadata.summary,
            "max_reads": 3,
            "outcomes": list(metadata.outcomes),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "action": self.action,
            "topic": self.topic,
            "reason_code": self.reason_code,
            "operation_key": self.operation_key,
            "subscription_gid": self.subscription_gid,
            "callback_uri_digest": self.callback_uri_digest,
            "expected_api_version": self.expected_api_version,
            "expected_format": self.expected_format,
            "expected_include_fields": list(self.expected_include_fields),
            "observed_api_version": self.observed_api_version,
            "observed_uri_digest": self.observed_uri_digest,
            "observed_format": self.observed_format,
            "observed_include_fields": list(self.observed_include_fields),
            "depends_on": list(self.depends_on),
            "ownership": self.ownership,
            "requires_readback": self.requires_readback,
            "target": self.target,
            "readback": self.readback,
        }


@dataclass(frozen=True, slots=True)
class WebhookSubscriptionPlan:
    desired: tuple[WebhookSubscriptionDesired, ...]
    observed: tuple[WebhookSubscriptionObserved, ...]
    granted_scopes: tuple[str, ...]
    callback_uri_digest: str
    decisions: tuple[WebhookSubscriptionDecision, ...]
    current_complete: bool = True
    fingerprint: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "desired", tuple(self.desired))
        object.__setattr__(self, "observed", tuple(self.observed))
        object.__setattr__(self, "granted_scopes", scopes(self.granted_scopes, "granted_scopes", maximum=MAX_GRANTED_SCOPES))
        object.__setattr__(self, "callback_uri_digest", digest(self.callback_uri_digest))
        object.__setattr__(self, "decisions", tuple(self.decisions))
        if any(not isinstance(value, WebhookSubscriptionDesired) for value in self.desired):
            fail("invalid_plan", "Plan desired values are malformed.")
        if any(not isinstance(value, WebhookSubscriptionObserved) for value in self.observed):
            fail("invalid_plan", "Plan observed values are malformed.")
        if any(not isinstance(value, WebhookSubscriptionDecision) for value in self.decisions):
            fail("invalid_plan", "Plan decisions are malformed.")
        decision_keys = [value.key for value in self.decisions]
        if len(decision_keys) != len(set(decision_keys)):
            fail("invalid_plan", "Plan decision keys must be unique.")
        if not isinstance(self.current_complete, bool):
            fail("invalid_plan", "current_complete must be a boolean.")
        computed = self._compute_fingerprint()
        if self.fingerprint:
            if not isinstance(self.fingerprint, str) or not _DIGEST.fullmatch(self.fingerprint) or self.fingerprint != computed:
                fail("invalid_plan", "Plan fingerprint is not the canonical digest.")
        else:
            object.__setattr__(self, "fingerprint", computed)

    def _safe_dict(self) -> dict[str, Any]:
        return {
            "desired": [value.as_dict() for value in self.desired],
            "observed": [value.as_dict() for value in self.observed],
            "granted_scopes": list(self.granted_scopes),
            "callback_uri_digest": self.callback_uri_digest,
            "decisions": [value.as_dict() for value in self.decisions],
            "current_complete": self.current_complete,
        }

    def _compute_fingerprint(self) -> str:
        return hashlib.sha256(canonical_json(self._safe_dict()).encode("utf-8")).hexdigest()

    @property
    def blocked(self) -> bool:
        return not self.current_complete or any(item.action == "block" for item in self.decisions)

    @property
    def execution_guard(self) -> str:
        return "blocked" if self.blocked else "open"

    @property
    def executable(self) -> bool:
        return not self.blocked

    @property
    def mutations(self) -> tuple[WebhookSubscriptionDecision, ...]:
        if self.blocked:
            return ()
        return tuple(item for item in self.decisions if item.action in {"create", "delete"})

    @property
    def status(self) -> str:
        if self.blocked:
            return "blocked"
        return "planned" if self.mutations else "converged"

    def require_executable(self) -> tuple[WebhookSubscriptionDecision, ...]:
        if self.blocked:
            fail("plan_blocked", "Webhook subscription plan is blocked by unresolved drift.")
        return self.mutations

    def as_dict(self) -> dict[str, Any]:
        result = self._safe_dict()
        result.update({
            "blocked": self.blocked,
            "execution_guard": self.execution_guard,
            "status": self.status,
            "fingerprint": self.fingerprint,
        })
        return result


def valid_observation(value: WebhookSubscriptionObserved) -> bool:
    """Whether safe facts are structurally usable for owned cleanup.

    This deliberately does not require the desired JSON format.  A valid
    unsupported enum such as ``XML`` is evidence of an owned stale record and
    can be replaced safely.  The exact JSON/API/filter comparison happens in
    the planner after this structural gate.
    """

    if not isinstance(value, WebhookSubscriptionObserved):
        return False
    return bool(
        _TOPIC.fullmatch(value.topic)
        and _API_VERSION.fullmatch(value.observed_api_version)
        and _FORMAT.fullmatch(value.format)
    )


def stale_reason(target: WebhookSubscriptionDesired, value: WebhookSubscriptionObserved) -> str:
    if value.observed_api_version != target.expected_api_version:
        return "stale_api_version"
    if value.format != target.expected_format:
        return "stale_format"
    return "stale_include_fields"


def decision_sort(value: WebhookSubscriptionDecision) -> tuple[str, int, str]:
    return value.topic, ACTION_ORDER[value.action], value.key


# Compatibility aliases make the seam discoverable without introducing a
# second set of value classes.
SubscriptionTopicSpec = WebhookTopicSpec
SubscriptionDesiredState = WebhookSubscriptionDesired
SubscriptionObserved = WebhookSubscriptionObserved
SubscriptionDecision = WebhookSubscriptionDecision
SubscriptionPlan = WebhookSubscriptionPlan


__all__ = [
    "ACTION_ORDER",
    "MAX_CURRENT_SUBSCRIPTIONS",
    "MAX_GRANTED_SCOPES",
    "MAX_INCLUDE_FIELDS",
    "MAX_TOPIC_SPECS",
    "SHOPIFY_API_VERSION",
    "SubscriptionDecision",
    "SubscriptionDesiredState",
    "SubscriptionObserved",
    "SubscriptionPlan",
    "SubscriptionTopicSpec",
    "WebhookSubscriptionDecision",
    "WebhookSubscriptionDesired",
    "WebhookSubscriptionObserved",
    "WebhookSubscriptionPlan",
    "WebhookSubscriptionPlannerError",
    "WebhookTopicSpec",
    "api_version",
    "bounded_items",
    "callback_digest",
    "canonical_json",
    "decision_sort",
    "digest",
    "fail",
    "fields",
    "fields_match",
    "gid",
    "scopes",
    "safe_api",
    "safe_format",
    "stale_reason",
    "strings",
    "topic",
    "valid_observation",
]
