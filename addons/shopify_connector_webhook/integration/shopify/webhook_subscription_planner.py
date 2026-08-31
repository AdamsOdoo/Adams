"""Pure P11 desired-state planner for webhook subscriptions.

P07 supplies safe current facts and P08 supplies the mutation operation and
readback contracts.  This module only computes immutable decisions.  It never
uses Odoo, credentials, HTTP, persistence or retry logic.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .webhook_subscription_contract_adapter import (
    adapt_p07_collection,
    adapt_p07_subscription,
)
from .webhook_subscription_planner_contracts import (
    ACTION_ORDER,
    MAX_CURRENT_SUBSCRIPTIONS,
    MAX_GRANTED_SCOPES,
    MAX_TOPIC_SPECS,
    SubscriptionDecision,
    SubscriptionDesiredState,
    SubscriptionObserved,
    SubscriptionPlan,
    SubscriptionTopicSpec,
    WebhookSubscriptionDecision,
    WebhookSubscriptionDesired,
    WebhookSubscriptionObserved,
    WebhookSubscriptionPlan,
    WebhookSubscriptionPlannerError,
    WebhookTopicSpec,
    bounded_items,
    callback_digest,
    decision_sort,
    fail,
    fields_match,
    scopes,
    stale_reason,
    valid_observation,
)


def _topic_specs(value: Any, maximum: int) -> tuple[WebhookTopicSpec, ...]:
    if isinstance(value, Mapping):
        entries = bounded_items(value.items(), "enabled_topics", maximum)
        raw = [
            item if isinstance(item, WebhookTopicSpec)
            else WebhookTopicSpec.from_mapping(key, item)
            for key, item in entries
        ]
        for key, item in entries:
            if isinstance(item, WebhookTopicSpec) and item.topic != key:
                fail("duplicate_topic", "Topic policy key and topic value must match.")
    else:
        raw = bounded_items(value, "enabled_topics", maximum)
    result: dict[str, WebhookTopicSpec] = {}
    for item in raw:
        if isinstance(item, WebhookTopicSpec):
            spec = item
        elif isinstance(item, str):
            spec = WebhookTopicSpec(item)
        elif isinstance(item, Mapping) and "topic" in item:
            spec = WebhookTopicSpec.from_mapping(item.get("topic"), item)
        else:
            fail("invalid_input", "Topic policy contains an unsupported value.")
        if spec.topic in result:
            fail("duplicate_topic", "Each webhook topic may have one desired policy.")
        result[spec.topic] = spec
    return tuple(result[key] for key in sorted(result))


def _observed_value(value: Any) -> WebhookSubscriptionObserved:
    return adapt_p07_subscription(value)


def _observed_values(value: Any, maximum: int) -> tuple[WebhookSubscriptionObserved, ...]:
    if isinstance(value, (str, bytes, Mapping)):
        fail("invalid_observation", "current_subscriptions must be a P07 collection or sequence.")
    # A page cannot prove a complete store read, even when has_next_page is
    # false: its starting cursor and omitted pages are not represented.  A
    # P07 collection carries the explicit complete/checkpoint contract and is
    # adapted through the same seam as a single DTO.
    if hasattr(value, "items") and not isinstance(value, (list, tuple, set, frozenset)):
        return adapt_p07_collection(value, maximum=maximum)
    if hasattr(value, "has_next_page") or hasattr(value, "next_cursor") or getattr(value, "start_cursor", None) is not None:
        fail("partial_read", "A P07 subscription page cannot be planned as complete state.")
    source = getattr(value, "items", value)
    if callable(source):
        fail("partial_read", "A P07 subscription page cannot be planned as complete state.")
    result = tuple(_observed_value(item) for item in bounded_items(source, "current_subscriptions", maximum))
    return result


def _block(
    *,
    key: str,
    topic: str,
    reason: str,
    desired: WebhookSubscriptionDesired | None = None,
    observed: WebhookSubscriptionObserved | None = None,
    ownership: str = "not_applicable",
) -> WebhookSubscriptionDecision:
    return WebhookSubscriptionDecision(key, "block", topic, reason, desired, observed, (), ownership)


def _mutation(
    *,
    key: str,
    action: str,
    topic: str,
    reason: str,
    desired: WebhookSubscriptionDesired | None = None,
    observed: WebhookSubscriptionObserved | None = None,
    depends_on: Iterable[str] = (),
    ownership: str = "not_applicable",
) -> WebhookSubscriptionDecision:
    return WebhookSubscriptionDecision(key, action, topic, reason, desired, observed, tuple(depends_on), ownership)


def _duplicate_blocks(observed: tuple[WebhookSubscriptionObserved, ...]) -> list[WebhookSubscriptionDecision]:
    grouped: dict[str, list[WebhookSubscriptionObserved]] = {}
    for item in observed:
        grouped.setdefault(item.id, []).append(item)
    return [
        _block(
            key=f"__store__:duplicate_subscription_identity:{gid.rsplit('/', 1)[-1]}",
            topic="__STORE__",
            reason="duplicate_subscription_identity",
            observed=rows[0],
            ownership="unknown",
        )
        for gid, rows in sorted(grouped.items())
        if len(rows) > 1
    ]


class WebhookSubscriptionPlanner:
    """Build a deterministic diff while preserving fail-closed ownership."""

    def __init__(
        self,
        *,
        max_topic_specs: int = MAX_TOPIC_SPECS,
        max_current_subscriptions: int = MAX_CURRENT_SUBSCRIPTIONS,
    ) -> None:
        if isinstance(max_topic_specs, bool) or not isinstance(max_topic_specs, int) or not 1 <= max_topic_specs <= MAX_TOPIC_SPECS:
            fail("invalid_bound", "max_topic_specs is outside its safety bound.")
        if isinstance(max_current_subscriptions, bool) or not isinstance(max_current_subscriptions, int) or not 1 <= max_current_subscriptions <= MAX_CURRENT_SUBSCRIPTIONS:
            fail("invalid_bound", "max_current_subscriptions is outside its safety bound.")
        self.max_topic_specs = max_topic_specs
        self.max_current_subscriptions = max_current_subscriptions

    def plan(
        self,
        enabled_topics: Iterable[WebhookTopicSpec | Mapping[str, Any] | str],
        current_subscriptions: Iterable[WebhookSubscriptionObserved | Mapping[str, Any]] | Any,
        *,
        callback_uri: str | None = None,
        callback_uri_digest: str | None = None,
        granted_scopes: Iterable[str] = (),
        current_complete: bool | None = None,
        current_start_cursor: str | None = None,
    ) -> WebhookSubscriptionPlan:
        if current_start_cursor is not None:
            fail("partial_read", "A subscription read with a starting cursor cannot establish complete state.")
        digest = callback_digest(callback_uri=callback_uri, callback_uri_digest=callback_uri_digest)
        specs = _topic_specs(enabled_topics, self.max_topic_specs)
        observed = _observed_values(current_subscriptions, self.max_current_subscriptions)
        if current_complete is None:
            current_complete = getattr(current_subscriptions, "complete", True)
        if not isinstance(current_complete, bool):
            fail("invalid_observation", "current_complete must be a boolean.")
        granted = scopes(granted_scopes, "granted_scopes", maximum=MAX_GRANTED_SCOPES)
        desired = tuple(
            WebhookSubscriptionDesired.from_topic(spec, digest)
            for spec in specs
            if spec.enabled
        )
        if current_complete:
            decisions = self._complete(desired, specs, observed, set(granted), digest)
        else:
            decisions = [_block(
                key="__store__:current_state_uncertain",
                topic="__STORE__",
                reason="current_state_uncertain",
                ownership="unknown",
            )]
        decisions.sort(key=decision_sort)
        return WebhookSubscriptionPlan(
            desired,
            tuple(sorted(observed, key=lambda item: (item.topic, item.id))),
            granted,
            digest,
            tuple(decisions),
            current_complete,
        )

    def _complete(
        self,
        desired: tuple[WebhookSubscriptionDesired, ...],
        specs: tuple[WebhookTopicSpec, ...],
        observed: tuple[WebhookSubscriptionObserved, ...],
        granted: set[str],
        callback_uri_digest: str,
    ) -> list[WebhookSubscriptionDecision]:
        decisions = _duplicate_blocks(observed)
        if decisions:
            return decisions
        by_topic: dict[str, list[WebhookSubscriptionObserved]] = {}
        for item in observed:
            by_topic.setdefault(item.topic, []).append(item)
            if item.topic not in {spec.topic for spec in specs}:
                decisions.append(_block(
                    key=f"{item.topic}:unrecognized:{item.id.rsplit('/', 1)[-1]}",
                    topic=item.topic,
                    reason="unrecognized_topic",
                    observed=item,
                    ownership="unknown",
                ))
        for spec in specs:
            if not spec.enabled:
                decisions.extend(self._disabled(spec.topic, by_topic.get(spec.topic, ()), callback_uri_digest))
        for target in desired:
            decisions.extend(self._desired(target, by_topic.get(target.topic, ()), granted))
        return decisions

    @staticmethod
    def _disabled(
        topic: str,
        rows: Iterable[WebhookSubscriptionObserved],
        callback_uri_digest: str,
    ) -> list[WebhookSubscriptionDecision]:
        rows = tuple(sorted(rows, key=lambda item: item.id))
        unsafe = any(
            item.uri_digest is None
            or item.uri_digest != callback_uri_digest
            or not valid_observation(item)
            for item in rows
        )
        result: list[WebhookSubscriptionDecision] = []
        for item in rows:
            if item.uri_digest is None:
                result.append(_block(
                    key=f"{topic}:unknown-callback:{item.id.rsplit('/', 1)[-1]}",
                    topic=topic,
                    reason="unknown_callback_identity",
                    observed=item,
                    ownership="unknown",
                ))
            elif item.uri_digest != callback_uri_digest:
                result.append(_block(
                    key=f"{topic}:callback-mismatch:{item.id.rsplit('/', 1)[-1]}",
                    topic=topic,
                    reason="callback_mismatch",
                    observed=item,
                    ownership="external",
                ))
            elif not valid_observation(item):
                result.append(_block(
                    key=f"{topic}:malformed:{item.id.rsplit('/', 1)[-1]}",
                    topic=topic,
                    reason="malformed_observation",
                    observed=item,
                    ownership="unknown",
                ))
            elif unsafe:
                result.append(_block(
                    key=f"{topic}:cleanup-blocked:{item.id.rsplit('/', 1)[-1]}",
                    topic=topic,
                    reason="cleanup_blocked_by_drift",
                    observed=item,
                    ownership="connector",
                ))
            else:
                result.append(_mutation(
                    key=f"{topic}:delete:{item.id.rsplit('/', 1)[-1]}",
                    action="delete",
                    topic=topic,
                    reason="no_longer_desired",
                    observed=item,
                    ownership="connector",
                ))
        return result

    @staticmethod
    def _desired(
        target: WebhookSubscriptionDesired,
        rows: Iterable[WebhookSubscriptionObserved],
        granted: set[str],
    ) -> list[WebhookSubscriptionDecision]:
        rows = tuple(sorted(rows, key=lambda item: item.id))
        result: list[WebhookSubscriptionDecision] = []
        missing = [scope for scope in target.required_scopes if scope not in granted]
        unknown = [item for item in rows if item.uri_digest is None]
        external = [item for item in rows if item.uri_digest not in {None, target.callback_uri_digest}]
        owned = [item for item in rows if item.uri_digest == target.callback_uri_digest]
        malformed = [item for item in owned if not valid_observation(item)]
        for item in unknown:
            result.append(_block(
                key=f"{target.topic}:unknown-callback:{item.id.rsplit('/', 1)[-1]}",
                topic=target.topic,
                reason="unknown_callback_identity",
                desired=target,
                observed=item,
                ownership="unknown",
            ))
        for item in external:
            result.append(_block(
                key=f"{target.topic}:callback-mismatch:{item.id.rsplit('/', 1)[-1]}",
                topic=target.topic,
                reason="callback_mismatch",
                desired=target,
                observed=item,
                ownership="external",
            ))
        for item in malformed:
            result.append(_block(
                key=f"{target.topic}:malformed:{item.id.rsplit('/', 1)[-1]}",
                topic=target.topic,
                reason="malformed_observation",
                desired=target,
                observed=item,
                ownership="unknown",
            ))
        unsafe = bool(unknown or external or malformed or missing)
        if missing:
            result.append(_block(
                key=f"{target.topic}:missing-scopes",
                topic=target.topic,
                reason="missing_scopes",
                desired=target,
                observed=rows[0] if rows else None,
                ownership="unknown" if rows else "not_applicable",
            ))
        exact = [
            item for item in owned
            if valid_observation(item)
            and item.observed_api_version == target.expected_api_version
            and item.format == target.expected_format
            and fields_match(target.expected_include_fields, item.include_fields)
        ]
        if exact:
            keeper = exact[0]
            result.append(_mutation(
                key=f"{target.topic}:keep:{keeper.id.rsplit('/', 1)[-1]}",
                action="keep",
                topic=target.topic,
                reason="already_desired",
                desired=target,
                observed=keeper,
                ownership="connector",
            ))
            if not unsafe:
                result.extend(
                    _mutation(
                        key=f"{target.topic}:delete-duplicate:{item.id.rsplit('/', 1)[-1]}",
                        action="delete",
                        topic=target.topic,
                        reason="duplicate_owned_subscription",
                        desired=target,
                        observed=item,
                        ownership="connector",
                    )
                    for item in exact[1:]
                )
                result.extend(
                    _mutation(
                        key=f"{target.topic}:delete-stale:{item.id.rsplit('/', 1)[-1]}",
                        action="delete",
                        topic=target.topic,
                        reason=stale_reason(target, item),
                        desired=target,
                        observed=item,
                        ownership="connector",
                    )
                    for item in owned
                    if item not in exact
                )
            return result
        if unsafe:
            return result
        if not owned:
            result.append(_mutation(
                key=f"{target.topic}:create",
                action="create",
                topic=target.topic,
                reason="missing_desired_subscription",
                desired=target,
            ))
            return result
        deletes = [
            _mutation(
                key=f"{target.topic}:delete-stale:{item.id.rsplit('/', 1)[-1]}",
                action="delete",
                topic=target.topic,
                reason=stale_reason(target, item),
                desired=target,
                observed=item,
                ownership="connector",
            )
            for item in owned
        ]
        result.extend(deletes)
        result.append(_mutation(
            key=f"{target.topic}:create-after-replacement",
            action="create",
            topic=target.topic,
            reason="replace_stale_owned_subscription",
            desired=target,
            depends_on=(item.key for item in deletes),
            ownership="connector",
        ))
        return result


def plan_webhook_subscriptions(
    enabled_topics: Iterable[WebhookTopicSpec | Mapping[str, Any] | str],
    current_subscriptions: Iterable[WebhookSubscriptionObserved | Mapping[str, Any]] | Any,
    *,
    callback_uri: str | None = None,
    callback_uri_digest: str | None = None,
    granted_scopes: Iterable[str] = (),
    current_complete: bool | None = None,
    current_start_cursor: str | None = None,
) -> WebhookSubscriptionPlan:
    return WebhookSubscriptionPlanner().plan(
        enabled_topics,
        current_subscriptions,
        callback_uri=callback_uri,
        callback_uri_digest=callback_uri_digest,
        granted_scopes=granted_scopes,
        current_complete=current_complete,
        current_start_cursor=current_start_cursor,
    )


__all__ = [
    "MAX_CURRENT_SUBSCRIPTIONS",
    "MAX_GRANTED_SCOPES",
    "MAX_TOPIC_SPECS",
    "SubscriptionDecision",
    "SubscriptionDesiredState",
    "SubscriptionObserved",
    "SubscriptionPlan",
    "SubscriptionTopicSpec",
    "WebhookSubscriptionDecision",
    "WebhookSubscriptionDesired",
    "WebhookSubscriptionObserved",
    "WebhookSubscriptionPlan",
    "WebhookSubscriptionPlanner",
    "WebhookSubscriptionPlannerError",
    "WebhookTopicSpec",
    "plan_webhook_subscriptions",
]
