import ast
import os
import re
from pathlib import Path

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..models import shopify_connector_job_dispatch
from ..models import shopify_connector_mutation_attempt


RAW_HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete', 'request'}
GRAPHQL_MUTATION_LITERAL = re.compile(
    r'(?:^|[\r\n])\s*mutation\s+[A-Za-z_][A-Za-z0-9_]*\s*[({]'
)
EXCEPTION_SUPERCLASSES = {
    'ValidationError': frozenset({'UserError', 'Exception', 'BaseException'}),
    'AccessError': frozenset({'UserError', 'Exception', 'BaseException'}),
    'UserError': frozenset({'Exception', 'BaseException'}),
    'Exception': frozenset({'BaseException'}),
}
BASE_EXCEPTION_ONLY = frozenset({
    'BaseException', 'GeneratorExit', 'KeyboardInterrupt', 'SystemExit',
})


def _parent_map(tree):
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _owning_method(node, parents):
    owner = parents.get(node)
    while owner and not isinstance(owner, ast.FunctionDef):
        owner = parents.get(owner)
    return owner


# The ONLY accepted prepare/transport production split (Task 013 Track B,
# PR #182 comment 5031833846). The GraphQL mutation operation literal is
# built in the `_prepare_preconditions_*` method, while the single guarded
# `client.execute_business(..., mutation_context=...)` call lives in the
# paired `_transport_*` method of the *same* class. This allowlist is exact
# and narrow -- an unknown file, class, prepare method, or transport sibling
# is never accepted here; it falls through to the default same-method guard
# and is reported as a violation. Keyed by
# (addon-relative file suffix, class name, prepare method)
#   -> the exact transport sibling that must hold the guarded call.
ACCEPTED_PREPARE_TRANSPORT_SPLIT = {
    (
        'shopify_connector_inventory/models/'
        'shopify_connector_inventory_service.py',
        'ShopifyConnectorInventoryService',
        '_prepare_preconditions_set_quantities',
    ): '_transport_set_quantities',
    (
        'shopify_connector_inventory/models/'
        'shopify_connector_inventory_service.py',
        'ShopifyConnectorInventoryService',
        '_prepare_preconditions_activate',
    ): '_transport_activate',
    (
        'shopify_connector_webhook/models/'
        'shopify_connector_webhook_subscription.py',
        'ShopifyConnectorWebhookSubscription',
        '_prepare_subscription_preconditions',
    ): '_transport_subscription_mutation',
    (
        'shopify_connector_fulfillment/models/'
        'shopify_connector_fulfillment_create_strategy.py',
        'ShopifyConnectorFulfillmentCreateStrategy',
        '_prepare_preconditions_fulfillment_create',
    ): '_transport_fulfillment_create',
    (
        'shopify_connector_fulfillment/models/'
        'shopify_connector_fulfillment_tracking_strategy.py',
        'ShopifyConnectorFulfillmentTrackingStrategy',
        '_prepare_preconditions_fulfillment_tracking_update',
    ): '_transport_fulfillment_tracking_update',
    # Task 015 / 015B (2026-07-26 ruling). The export module splits its
    # mutations across four product and three media domains; every one
    # reaches transport ONLY through the single shared guarded helper
    # named in SHARED_GUARDED_TRANSPORT below, which is stricter than
    # eight separate copies of the same `execute_business` call.
    (
        'shopify_connector_product_export/models/'
        'shopify_connector_product_export_service.py',
        'ShopifyConnectorProductExportService',
        '_prepare_preconditions_binding_namespace',
    ): '_transport_binding_namespace',
    (
        'shopify_connector_product_export/models/'
        'shopify_connector_product_export_service.py',
        'ShopifyConnectorProductExportService',
        '_prepare_preconditions_create',
    ): '_transport_create',
    (
        'shopify_connector_product_export/models/'
        'shopify_connector_product_export_service.py',
        'ShopifyConnectorProductExportService',
        '_prepare_preconditions_update',
    ): '_transport_update',
    (
        'shopify_connector_product_export/models/'
        'shopify_connector_product_export_service.py',
        'ShopifyConnectorProductExportService',
        '_prepare_preconditions_variants_update',
    ): '_transport_variants_update',
    (
        'shopify_connector_product_export/models/'
        'shopify_connector_product_export_service.py',
        'ShopifyConnectorProductExportService',
        '_prepare_preconditions_variants_create',
    ): '_transport_variants_create',
    (
        'shopify_connector_product_export/models/'
        'shopify_connector_media_export_service.py',
        'ShopifyConnectorMediaExportService',
        '_prepare_preconditions_media_stage',
    ): '_transport_media_stage',
    (
        'shopify_connector_product_export/models/'
        'shopify_connector_media_export_service.py',
        'ShopifyConnectorMediaExportService',
        '_prepare_preconditions_media_file_create',
    ): '_transport_media_file_create',
    (
        'shopify_connector_product_export/models/'
        'shopify_connector_media_export_service.py',
        'ShopifyConnectorMediaExportService',
        '_prepare_preconditions_media_associate',
    ): '_transport_media_associate',
}


# The ONE shared guarded transport helper an accepted split may delegate to
# instead of holding `execute_business(mutation_context=...)` itself. Naming it
# here — rather than accepting any delegation — keeps the guard exact: a
# `_transport_*` method satisfies the contract only by calling THIS method, and
# this method is itself checked for the guarded call and for forbidden routes.
SHARED_GUARDED_TRANSPORT = (
    'shopify_connector_product_export/models/'
    'shopify_connector_product_export_service.py',
    'ShopifyConnectorProductExportService',
    '_transport',
)


# Typed gateways now own the checked-in GraphQL documents while the existing
# Layer-2 services still own admission and guarded transport.  Every document
# is therefore bound here to one exact consumer prepare method; that method's
# exact transport sibling remains governed by ACCEPTED_PREPARE_TRANSPORT_SPLIT.
# A new gateway document, consumer, class or method is rejected until it is
# reviewed and named explicitly.
_INV_SPLIT_FILE = (
    'shopify_connector_inventory/models/'
    'shopify_connector_inventory_service.py'
)
_INV_SPLIT_CLASS = 'ShopifyConnectorInventoryService'
_INVENTORY_GATEWAY = (
    'shopify_connector_inventory/integration/shopify/'
    'inventory_mutation_gateway.py'
)
_FULFILLMENT_GATEWAY = (
    'shopify_connector_fulfillment/integration/shopify/'
    'fulfillment_mutation_gateway.py'
)
_PRODUCT_GATEWAY = (
    'shopify_connector_product_export/integration/shopify/'
    'product_export_mutation_gateway.py'
)
_MEDIA_GATEWAY = (
    'shopify_connector_product_export/integration/shopify/'
    'product_media_mutation_gateway.py'
)
_WEBHOOK_GATEWAY = (
    'shopify_connector_webhook/integration/shopify/'
    'webhook_subscription_mutation_gateway.py'
)
_FULFILLMENT_CREATE_SERVICE = (
    'shopify_connector_fulfillment/models/'
    'shopify_connector_fulfillment_create_strategy.py'
)
_FULFILLMENT_TRACKING_SERVICE = (
    'shopify_connector_fulfillment/models/'
    'shopify_connector_fulfillment_tracking_strategy.py'
)
_PRODUCT_SERVICE = (
    'shopify_connector_product_export/models/'
    'shopify_connector_product_export_service.py'
)
_MEDIA_SERVICE = (
    'shopify_connector_product_export/models/'
    'shopify_connector_media_export_service.py'
)
_WEBHOOK_SERVICE = (
    'shopify_connector_webhook/models/'
    'shopify_connector_webhook_subscription.py'
)

MUTATION_DOCUMENT_CONSUMERS = {
    (_INVENTORY_GATEWAY, 'INVENTORY_SET_QUANTITIES_DOCUMENT'): (
        _INV_SPLIT_FILE, _INV_SPLIT_CLASS,
        '_prepare_preconditions_set_quantities',
    ),
    (_INVENTORY_GATEWAY, 'INVENTORY_ACTIVATE_DOCUMENT'): (
        _INV_SPLIT_FILE, _INV_SPLIT_CLASS, '_prepare_preconditions_activate',
    ),
    (_FULFILLMENT_GATEWAY, 'FULFILLMENT_CREATE_DOCUMENT'): (
        _FULFILLMENT_CREATE_SERVICE,
        'ShopifyConnectorFulfillmentCreateStrategy',
        '_prepare_preconditions_fulfillment_create',
    ),
    (_FULFILLMENT_GATEWAY, 'FULFILLMENT_TRACKING_UPDATE_DOCUMENT'): (
        _FULFILLMENT_TRACKING_SERVICE,
        'ShopifyConnectorFulfillmentTrackingStrategy',
        '_prepare_preconditions_fulfillment_tracking_update',
    ),
    (_PRODUCT_GATEWAY, 'BINDING_NAMESPACE_DOCUMENT'): (
        _PRODUCT_SERVICE, 'ShopifyConnectorProductExportService',
        '_prepare_preconditions_binding_namespace',
    ),
    (_PRODUCT_GATEWAY, 'PRODUCT_CREATE_DOCUMENT'): (
        _PRODUCT_SERVICE, 'ShopifyConnectorProductExportService',
        '_prepare_preconditions_create',
    ),
    (_PRODUCT_GATEWAY, 'PRODUCT_UPDATE_DOCUMENT'): (
        _PRODUCT_SERVICE, 'ShopifyConnectorProductExportService',
        '_prepare_preconditions_update',
    ),
    (_PRODUCT_GATEWAY, 'VARIANTS_UPDATE_DOCUMENT'): (
        _PRODUCT_SERVICE, 'ShopifyConnectorProductExportService',
        '_prepare_preconditions_variants_update',
    ),
    (_PRODUCT_GATEWAY, 'VARIANTS_CREATE_DOCUMENT'): (
        _PRODUCT_SERVICE, 'ShopifyConnectorProductExportService',
        '_prepare_preconditions_variants_create',
    ),
    (_MEDIA_GATEWAY, 'MEDIA_STAGE_DOCUMENT'): (
        _MEDIA_SERVICE, 'ShopifyConnectorMediaExportService',
        '_prepare_preconditions_media_stage',
    ),
    (_MEDIA_GATEWAY, 'MEDIA_FILE_CREATE_DOCUMENT'): (
        _MEDIA_SERVICE, 'ShopifyConnectorMediaExportService',
        '_prepare_preconditions_media_file_create',
    ),
    (_MEDIA_GATEWAY, 'MEDIA_ASSOCIATE_DOCUMENT'): (
        _MEDIA_SERVICE, 'ShopifyConnectorMediaExportService',
        '_prepare_preconditions_media_associate',
    ),
    (_WEBHOOK_GATEWAY, 'WEBHOOK_SUBSCRIPTION_CREATE_DOCUMENT'): (
        _WEBHOOK_SERVICE, 'ShopifyConnectorWebhookSubscription',
        '_prepare_subscription_preconditions',
    ),
    (_WEBHOOK_GATEWAY, 'WEBHOOK_SUBSCRIPTION_DELETE_DOCUMENT'): (
        _WEBHOOK_SERVICE, 'ShopifyConnectorWebhookSubscription',
        '_prepare_subscription_preconditions',
    ),
}

RECONCILIATION_READ_SEND_SURFACE = (
    'shopify_connector_core/models/'
    'shopify_connector_api_client_v2_runtime.py',
    'ShopifyConnectorApiClientV2Runtime',
    '_execute_v2_reconciliation_read',
)


def _shared_guarded_transport_node(addon_root):
    """Return the shared helper's AST node, or None when it is absent."""
    file_suffix, class_name, method_name = SHARED_GUARDED_TRANSPORT
    path = addon_root / file_suffix
    if not path.exists():
        return None
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for member in node.body:
                if (
                    isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and member.name == method_name
                ):
                    return member
    return None


def _method_delegates_to_shared_transport(method_node):
    """True when the method's only transport route is the shared helper."""
    if method_node is None:
        return False
    return any(
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == SHARED_GUARDED_TRANSPORT[2]
        for call in ast.walk(method_node)
    )


def _owning_class(node, parents):
    owner = parents.get(node)
    while owner and not isinstance(owner, ast.ClassDef):
        owner = parents.get(owner)
    return owner


def _method_has_guarded_execute_business(method_node):
    """True when the method contains a `.execute_business(...)` call that
    passes a `mutation_context=` keyword argument."""
    if method_node is None:
        return False
    return any(
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == 'execute_business'
        and any(keyword.arg == 'mutation_context' for keyword in call.keywords)
        for call in ast.walk(method_node)
    )


def _method_has_forbidden_transport(method_node):
    """True when the method reaches transport by any route other than the
    guarded business surface: a `.execute(...)` / `._send(...)` attribute
    call, or a raw `requests.<verb>(...)` HTTP call."""
    if method_node is None:
        return False
    for call in ast.walk(method_node):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
        ):
            continue
        if call.func.attr in {'execute', '_send'}:
            return True
        if (
            call.func.attr in RAW_HTTP_METHODS
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == 'requests'
        ):
            return True
    return False


def _accepted_split_transport_name(relative, class_name, method_name):
    """Return the exact transport sibling name for an accepted split, or
    None when (file, class, prepare method) is not on the allowlist."""
    for (file_suffix, cls, prepare), transport in (
        ACCEPTED_PREPARE_TRANSPORT_SPLIT.items()
    ):
        if (
            relative.endswith(file_suffix)
            and class_name == cls
            and method_name == prepare
        ):
            return transport
    return None


def _single_paired_transport(owner_class, paired_name):
    """Return the paired transport method of `owner_class` named
    `paired_name`, but only when it exists *exactly once*; else None."""
    if owner_class is None:
        return None
    siblings = [
        member for member in owner_class.body
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        and member.name == paired_name
    ]
    if len(siblings) != 1:
        return None
    return siblings[0]


def _top_level_mutation_documents(tree):
    documents = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            names = [
                target.id for target in statement.targets
                if isinstance(target, ast.Name)
            ]
            value = statement.value
        elif (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
        ):
            names = [statement.target.id]
            value = statement.value
        else:
            continue
        literals = [
            node for node in ast.walk(value)
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and GRAPHQL_MUTATION_LITERAL.search(node.value)
            )
        ] if value is not None else []
        if len(names) == 1 and len(literals) == 1:
            documents[names[0]] = literals[0]
    return documents


def _module_imports_exact_name(tree, module_suffix, name):
    dotted_suffix = module_suffix[:-3].replace('/', '.')
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.endswith(dotted_suffix)
        and any(
            alias.name == name and alias.asname is None
            for alias in node.names
        )
        for node in tree.body
    )


def _validated_document_bindings(
    addon_root, shared_transport=None, source_overrides=None,
):
    source_overrides = source_overrides or {}
    violations = []
    validated = set()
    for key, consumer in MUTATION_DOCUMENT_CONSUMERS.items():
        gateway_suffix, document_name = key
        consumer_suffix, class_name, prepare_name = consumer
        gateway_path = addon_root / gateway_suffix
        consumer_path = addon_root / consumer_suffix
        if not gateway_path.exists() or not consumer_path.exists():
            violations.append(('missing_binding_file',) + key + consumer)
            continue
        gateway_source = source_overrides.get(gateway_suffix)
        if gateway_source is None:
            gateway_source = gateway_path.read_text(encoding='utf-8')
        gateway_tree = ast.parse(gateway_source, filename=str(gateway_path))
        if document_name not in _top_level_mutation_documents(gateway_tree):
            violations.append(('invalid_document',) + key)
            continue
        consumer_source = source_overrides.get(consumer_suffix)
        if consumer_source is None:
            consumer_source = consumer_path.read_text(encoding='utf-8')
        consumer_tree = ast.parse(consumer_source, filename=str(consumer_path))
        classes = [
            node for node in consumer_tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ]
        owner_class = classes[0] if len(classes) == 1 else None
        prepare = _single_paired_transport(owner_class, prepare_name)
        paired_name = _accepted_split_transport_name(
            consumer_suffix, class_name, prepare_name,
        )
        transport = _single_paired_transport(owner_class, paired_name)
        transport_is_guarded = transport is not None and (
            _method_has_guarded_execute_business(transport)
            or (
                shared_transport is not None
                and _method_delegates_to_shared_transport(transport)
                and _method_has_guarded_execute_business(shared_transport)
                and not _method_has_forbidden_transport(shared_transport)
            )
        )
        name_uses = [
            node for node in ast.walk(prepare) if (
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id == document_name
            )
        ] if prepare is not None else []
        if not (
            _module_imports_exact_name(
                consumer_tree, gateway_suffix, document_name,
            )
            and len(name_uses) == 1
            and paired_name is not None
            and transport_is_guarded
            and not _method_has_guarded_execute_business(prepare)
            and not _method_has_forbidden_transport(prepare)
            and not _method_has_forbidden_transport(transport)
        ):
            violations.append(('invalid_consumer',) + key + consumer)
            continue
        validated.add(key)
    return validated, violations


def _mutation_literal_violations(
    source, relative, shared_transport=None, validated_documents=frozenset(),
):
    tree = ast.parse(source, filename=relative)
    parents = _parent_map(tree)
    documents = _top_level_mutation_documents(tree)
    violations = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and GRAPHQL_MUTATION_LITERAL.search(node.value)
        ):
            continue
        owner = _owning_method(node, parents)
        owner_name = owner.name if owner else False
        owner_class = _owning_class(node, parents)
        owner_class_name = owner_class.name if owner_class else False
        document_names = [
            name for name, literal in documents.items() if literal is node
        ]
        document_key = next((
            key for key in validated_documents
            if (
                len(document_names) == 1
                and relative.endswith(key[0])
                and document_names[0] == key[1]
            )
        ), None)
        if document_key in validated_documents:
            continue
        selftest = (
            relative.endswith(
                'shopify_connector_core/models/'
                'shopify_connector_job_dispatch.py'
            )
            and owner_name == '_prepare_preconditions_mutation_selftest'
        )
        if selftest:
            continue

        # Default (unchanged): the guarded `execute_business(
        # mutation_context=...)` call must live in the *same* method that
        # holds the literal, and that method must not reach transport by
        # any forbidden route.
        if (
            _method_has_guarded_execute_business(owner)
            and not _method_has_forbidden_transport(owner)
        ):
            continue

        # Accepted prepare/transport split -- exact, narrow allowlist only.
        # Every one of these must hold, or the literal is a violation:
        #   * (file, class, prepare method) is on the allowlist;
        #   * the paired transport method exists exactly once in the SAME
        #     class;
        #   * the transport method holds `execute_business(mutation_context
        #     =...)`;
        #   * neither the prepare nor the transport method reaches transport
        #     by a forbidden route (`.execute` / `._send` / raw HTTP).
        paired_name = _accepted_split_transport_name(
            relative, owner_class_name, owner_name,
        )
        if paired_name is not None:
            transport = _single_paired_transport(owner_class, paired_name)
            transport_is_guarded = transport is not None and (
                _method_has_guarded_execute_business(transport)
                or (
                    # Delegation to the ONE shared guarded helper, which must
                    # itself hold the guarded call and reach transport by no
                    # other route.
                    shared_transport is not None
                    and _method_delegates_to_shared_transport(transport)
                    and _method_has_guarded_execute_business(shared_transport)
                    and not _method_has_forbidden_transport(shared_transport)
                )
            )
            if (
                transport_is_guarded
                and not _method_has_forbidden_transport(owner)
                and not _method_has_forbidden_transport(transport)
            ):
                continue

        violations.append((relative, node.lineno, owner_name))
    return violations


def _contains_attempt_env_lookup(node):
    return any(
        isinstance(part, ast.Subscript)
        and isinstance(part.slice, ast.Constant)
        and part.slice.value == 'shopify.connector.mutation.attempt'
        for part in ast.walk(node)
    )


def _class_owns_model(class_node, model_name):
    if class_node is None:
        return False
    for statement in class_node.body:
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        targets = (
            statement.targets if isinstance(statement, ast.Assign)
            else (statement.target,)
        )
        if any(
            isinstance(target, ast.Name)
            and target.id in {'_name', '_inherit'}
            for target in targets
        ) and any(
            isinstance(value, ast.Constant) and value.value == model_name
            for value in ast.walk(statement.value)
        ):
            return True
    return False


def _retention_write_is_closed(tree, node, owner, owner_class, relative):
    if not (
        relative.endswith(
            'shopify_connector_core/models/'
            'shopify_connector_mutation_attempt_retention.py'
        )
        and owner is not None
        and owner.name == '_retention_mark_masked'
        and owner_class is not None
        and owner_class.name == 'ShopifyConnectorMutationAttemptRetention'
        and _class_owns_model(
            owner_class, 'shopify.connector.mutation.attempt',
        )
        and ast.unparse(node) == (
            "records._surface('_mask_terminal_evidence').write("
            "{'evidence_masked_at': fields.Datetime.now()})"
        )
    ):
        return False
    parents = _parent_map(tree)
    calls = [
        call for call in ast.walk(tree)
        if (
            isinstance(call, ast.Call)
            and ast.unparse(call) == 'self._retention_mark_masked(self)'
        )
    ]
    return bool(
        len(calls) == 1
        and _owning_method(calls[0], parents) is not None
        and _owning_method(calls[0], parents).name == '_mask_terminal_evidence'
        and _owning_class(calls[0], parents) is owner_class
    )


def _attempt_write_violations(source, relative):
    tree = ast.parse(source, filename=relative)
    parents = _parent_map(tree)
    allowed = {
        'create', 'write', '_create_attempt_intent',
        '_record_direct_outcome', '_record_recovery_uncertain',
        '_record_reconciliation_result',
        '_record_inconclusive_reconciliation',
        'action_resolve_mutation_attempt', '_mask_terminal_evidence',
    }
    violations = []
    base_attempt_model_file = relative.endswith(
        'shopify_connector_core/models/'
        'shopify_connector_mutation_attempt.py'
    )
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {'create', 'write', 'unlink'}
        ):
            continue
        target = node.func.value
        target_source = ast.unparse(target)
        root_names = {
            part.id.lower() for part in ast.walk(target)
            if isinstance(part, ast.Name)
        }
        owner = _owning_method(node, parents)
        owner_name = owner.name if owner else False
        owner_class = _owning_class(node, parents)
        owning_attempt_model = _class_owns_model(
            owner_class, 'shopify.connector.mutation.attempt',
        )
        is_attempt_target = (
            bool(root_names & {'attempt', 'attempts'})
            or _contains_attempt_env_lookup(target)
            or (
                owning_attempt_model
                and (
                    'self' in root_names
                    or target_source.startswith('super()')
                    or (
                        isinstance(target, ast.Call)
                        and isinstance(target.func, ast.Attribute)
                        and target.func.attr == '_surface'
                    )
                )
            )
        )
        if not is_attempt_target:
            continue
        if node.func.attr == 'create':
            sanctioned = (
                base_attempt_model_file
                and owner_name in {'create', '_create_attempt_intent'}
            )
        elif node.func.attr == 'write':
            sanctioned = (
                (base_attempt_model_file and owner_name in allowed)
                or (
                    relative.endswith(
                        'shopify_connector_core/models/'
                        'shopify_connector_mutation_attempt_v2_runtime.py'
                    )
                    and owning_attempt_model
                    and owner_class.name == (
                        'ShopifyConnectorMutationAttemptV2Runtime'
                    )
                    and owner_name == 'write'
                    and target_source == 'super()'
                    and len(node.args) == 1
                    and isinstance(node.args[0], ast.Name)
                    and node.args[0].id == 'vals'
                    and not node.keywords
                )
                or _retention_write_is_closed(
                    tree, node, owner, owner_class, relative,
                )
            )
        else:
            sanctioned = False
        if not sanctioned:
            violations.append((
                relative, node.lineno, owner_name,
                node.func.attr, target_source,
            ))
    return violations


def _method_calls(method_node, name):
    return [
        node for node in ast.walk(method_node)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == name
        )
    ] if method_node is not None else []


def _nodes_contain(nodes, needle):
    return any(
        candidate is needle
        for node in nodes
        for candidate in ast.walk(node)
    )


def _reconciliation_read_sender_is_closed(method_node):
    validations = _method_calls(method_node, '_validate_graphql_operation')
    admissions = _method_calls(method_node, '_admit_v2_reconciliation_read')
    sends = _method_calls(method_node, '_send')
    normalizations = _method_calls(method_node, '_normalize_response')
    releases = _method_calls(method_node, '_release_lease')
    if not (
        len(validations) == 1
        and any(
            keyword.arg == 'mutation_context'
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is None
            for keyword in validations[0].keywords
        )
        and len(admissions) == 1
        and len(sends) == 1
        and len(normalizations) == 1
        and len(releases) == 2
    ):
        return False
    # Keep the mutation/containment check explicit rather than accepting any
    # preceding validation call as a query-only fence.
    mutation_rejections = [
        node for node in ast.walk(method_node)
        if (
            isinstance(node, ast.If)
            and _method_calls(node.test, '_graphql_contains_mutation')
            and any(isinstance(child, ast.Raise) for child in node.body)
        )
    ]
    if len(mutation_rejections) != 1:
        return False
    if not (
        validations[0].lineno < mutation_rejections[0].lineno
        < admissions[0].lineno < sends[0].lineno
        < normalizations[0].lineno
    ):
        return False
    for try_node in ast.walk(method_node):
        if not isinstance(try_node, (ast.Try, ast.TryStar)):
            continue
        if not _nodes_contain(try_node.body, sends[0]):
            continue
        error_release = any(
            'BaseException' in _exception_handler_names(handler.type)
            and any(
                _nodes_contain(handler.body, call) for call in releases
            )
            for handler in try_node.handlers
        )
        success_release = any(
            _nodes_contain(try_node.orelse, call) for call in releases
        )
        if error_release and success_release:
            return True
    return False


def _direct_send_violations(source, relative):
    tree = ast.parse(source, filename=relative)
    parents = _parent_map(tree)
    violations = []
    base_client = relative.endswith(
        'shopify_connector_core/models/shopify_connector_api_client.py'
    )
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == '_send'
        ):
            continue
        if base_client:
            continue
        owner = _owning_method(node, parents)
        owner_class = _owning_class(node, parents)
        exact_sender = (
            relative.endswith(RECONCILIATION_READ_SEND_SURFACE[0])
            and owner_class is not None
            and owner_class.name == RECONCILIATION_READ_SEND_SURFACE[1]
            and owner is not None
            and owner.name == RECONCILIATION_READ_SEND_SURFACE[2]
            and _reconciliation_read_sender_is_closed(owner)
        )
        if not exact_sender:
            violations.append((relative, node.lineno))
    return violations


def _exception_handler_names(handler_type):
    if handler_type is None:
        return ('BaseException',)
    if isinstance(handler_type, ast.Tuple):
        return tuple(
            name
            for item in handler_type.elts
            for name in _exception_handler_names(item)
        )
    return (ast.unparse(handler_type),)


def _exception_handler_shadows(earlier, later):
    if earlier == later or earlier == 'BaseException':
        return True
    if earlier == 'Exception' and later not in BASE_EXCEPTION_ONLY:
        return True
    return earlier in EXCEPTION_SUPERCLASSES.get(later, frozenset())


def _exception_shadowing_violations(source, relative):
    tree = ast.parse(source, filename=relative)
    violations = []
    for try_node in ast.walk(tree):
        if not isinstance(try_node, (ast.Try, ast.TryStar)):
            continue
        earlier_names = []
        for handler in try_node.handlers:
            later_names = _exception_handler_names(handler.type)
            for later in later_names:
                for earlier in earlier_names:
                    if _exception_handler_shadows(earlier, later):
                        violations.append((
                            relative, handler.lineno, earlier, later,
                        ))
            earlier_names.extend(later_names)
    return violations


# --- Synthetic-source builders for the accepted-split adversarial tests ---


def _make_split_source(
    *,
    class_name=_INV_SPLIT_CLASS,
    prepare_name='_prepare_preconditions_set_quantities',
    transport_name='_transport_set_quantities',
    include_transport=True,
    transport_call='execute_business',
    context_keyword='mutation_context',
    prepare_forbidden=None,
    transport_forbidden=None,
):
    """Build a minimal, syntactically valid module source that mirrors the
    real accepted prepare/transport split, with exactly one knob varied per
    adversarial case. Defaults produce a *valid* accepted split."""
    prepare_extra = (
        '        %s\n' % prepare_forbidden if prepare_forbidden else ''
    )
    src = (
        'class %s:\n'
        '    def %s(self, local_snapshot, owner_context):\n'
        "        operation = 'mutation InventorySetQuantities($input: X!)"
        " { x }'\n"
        '%s'
        "        return {'operation': operation}\n"
    ) % (class_name, prepare_name, prepare_extra)
    if include_transport:
        transport_extra = (
            '        %s\n' % transport_forbidden if transport_forbidden else ''
        )
        if transport_call == 'execute_business':
            call_block = (
                '        with client.execute_business(\n'
                "            attempt_context['job_id'], store,\n"
                "            request['operation'], request['variables'],\n"
                '            %s=attempt_context,\n'
                '        ) as result:\n'
                '            return result\n'
            ) % (context_keyword,)
        else:
            call_block = (
                '        return client.%s(store, request)\n' % transport_call
            )
        src += (
            '    def %s(self, request, attempt_context):\n'
            "        client = self.env['shopify.connector.api.client']\n"
            '        store = client\n'
            '%s'
            '%s'
        ) % (transport_name, transport_extra, call_block)
    return src


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestMutationSourceGuards(TransactionCase):

    def _addon_root(self):
        return Path(__file__).resolve().parents[2]

    def _python_files(self):
        return sorted(
            path for path in self._addon_root().glob(
                'shopify_connector_*/**/*.py'
            )
            if 'tests' not in path.parts
        )

    def _document_bindings(self):
        shared = _shared_guarded_transport_node(self._addon_root())
        self.assertIsNotNone(shared)
        validated, violations = _validated_document_bindings(
            self._addon_root(), shared,
        )
        self.assertFalse(violations, violations)
        return shared, validated

    def test_repo_wide_raw_transport_guard(self):
        violations = []
        for path in self._python_files():
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            parents = {}
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parents[child] = parent
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (
                    isinstance(func, ast.Attribute)
                    and func.attr in RAW_HTTP_METHODS
                    and isinstance(func.value, ast.Name)
                    and func.value.id == 'requests'
                ):
                    continue
                relative = str(path.relative_to(self._addon_root()))
                owner = parents.get(node)
                while owner and not isinstance(owner, ast.FunctionDef):
                    owner = parents.get(owner)
                owner_name = owner.name if owner else False
                allowed = (
                    relative.endswith(
                        'shopify_connector_core/models/'
                        'shopify_connector_api_client.py'
                    )
                    and func.attr == 'post'
                    and owner_name == '_send'
                ) or (
                    # Wave 5: the client-credentials token exchange. It is a
                    # POST to the shop's own `/admin/oauth/access_token`, not a
                    # GraphQL call -- there is no operation to admit, no
                    # mutation to confirm and no lease to hold, so it cannot go
                    # through `execute_business`. Narrowed to the same one
                    # file, one verb and one owning function every other entry
                    # here uses, and that function does nothing but build and
                    # post the request.
                    relative.endswith(
                        'shopify_connector_core/models/'
                        'shopify_connector_api_client.py'
                    )
                    and func.attr == 'post'
                    and owner_name == '_send_token_exchange'
                ) or (
                    relative.endswith(
                        'shopify_connector_product/models/'
                        'shopify_connector_product_importer.py'
                    )
                    and func.attr == 'get'
                ) or (
                    # Task 015B: the staged-upload PUT/POST is a plain HTTPS
                    # upload to the object-store target `stagedUploadsCreate`
                    # returned. It is NOT a Shopify GraphQL call, changes no
                    # Shopify resource, and writes to a write-once key, so it
                    # cannot go through `execute_business` -- there is no
                    # GraphQL operation to admit. Narrowed to one file, one
                    # verb and one method so nothing else in that module can
                    # reach raw HTTP.
                    relative.endswith(
                        'shopify_connector_product_export/models/'
                        'shopify_connector_media_export_service.py'
                    )
                    and func.attr == 'post'
                    and owner_name == '_handle_product_export_media_upload'
                )
                if not allowed:
                    violations.append((relative, node.lineno, func.attr))
        self.assertFalse(violations, violations)

    def test_mutation_literals_require_guarded_transport_or_selftest(self):
        shared, validated_documents = self._document_bindings()
        violations = []
        for path in self._python_files():
            relative = str(path.relative_to(self._addon_root()))
            violations.extend(_mutation_literal_violations(
                path.read_text(encoding='utf-8'), relative, shared,
                validated_documents,
            ))
        self.assertFalse(violations, violations)

    def test_mutation_literal_detector_rejects_unguarded_paths(self):
        for call in (
            "return self.execute(store, operation)",
            "return self._send(store, {'query': operation})",
            'return operation',
        ):
            source = (
                'def unsafe(self, store):\n'
                "    operation = 'mutation Unsafe($id: ID!) { x }'\n"
                '    %s\n' % call
            )
            self.assertTrue(_mutation_literal_violations(
                source, 'shopify_connector_core/models/unsafe.py',
            ))
        guarded = (
            'def guarded(self, client, job, store, context):\n'
            "    operation = 'mutation Guarded($id: ID!) { x }'\n"
            '    with client.execute_business(\n'
            '        job, store, operation, {}, mutation_context=context,\n'
            '    ):\n'
            '        pass\n'
        )
        self.assertFalse(_mutation_literal_violations(
            guarded, 'shopify_connector_domain/models/exporter.py',
        ))

    # --- Accepted prepare/transport split: adversarial guard self-tests ---

    def test_accepted_split_allowlist_is_exactly_the_declared_pairs(self):
        # The allowlist must stay EXACT and NARROW: every entry is named here
        # explicitly, so widening it (e.g. to every `_prepare_preconditions_*`,
        # or to a whole file) fails this test rather than passing quietly.
        #
        # Thirteen entries: inventory (two), webhook subscription (one),
        # fulfillment (two), product export (five), and media export (three).
        export_service = (
            'shopify_connector_product_export/models/'
            'shopify_connector_product_export_service.py'
        )
        export_class = 'ShopifyConnectorProductExportService'
        media_service = (
            'shopify_connector_product_export/models/'
            'shopify_connector_media_export_service.py'
        )
        media_class = 'ShopifyConnectorMediaExportService'
        self.assertEqual(
            ACCEPTED_PREPARE_TRANSPORT_SPLIT,
            {
                (
                    _INV_SPLIT_FILE, _INV_SPLIT_CLASS,
                    '_prepare_preconditions_set_quantities',
                ): '_transport_set_quantities',
                (
                    _INV_SPLIT_FILE, _INV_SPLIT_CLASS,
                    '_prepare_preconditions_activate',
                ): '_transport_activate',
                (
                    'shopify_connector_webhook/models/'
                    'shopify_connector_webhook_subscription.py',
                    'ShopifyConnectorWebhookSubscription',
                    '_prepare_subscription_preconditions',
                ): '_transport_subscription_mutation',
                (
                    'shopify_connector_fulfillment/models/'
                    'shopify_connector_fulfillment_create_strategy.py',
                    'ShopifyConnectorFulfillmentCreateStrategy',
                    '_prepare_preconditions_fulfillment_create',
                ): '_transport_fulfillment_create',
                (
                    'shopify_connector_fulfillment/models/'
                    'shopify_connector_fulfillment_tracking_strategy.py',
                    'ShopifyConnectorFulfillmentTrackingStrategy',
                    '_prepare_preconditions_fulfillment_tracking_update',
                ): '_transport_fulfillment_tracking_update',
                (
                    export_service, export_class,
                    '_prepare_preconditions_binding_namespace',
                ): '_transport_binding_namespace',
                (
                    export_service, export_class,
                    '_prepare_preconditions_create',
                ): '_transport_create',
                (
                    export_service, export_class,
                    '_prepare_preconditions_update',
                ): '_transport_update',
                (
                    export_service, export_class,
                    '_prepare_preconditions_variants_update',
                ): '_transport_variants_update',
                (
                    export_service, export_class,
                    '_prepare_preconditions_variants_create',
                ): '_transport_variants_create',
                (
                    media_service, media_class,
                    '_prepare_preconditions_media_stage',
                ): '_transport_media_stage',
                (
                    media_service, media_class,
                    '_prepare_preconditions_media_file_create',
                ): '_transport_media_file_create',
                (
                    media_service, media_class,
                    '_prepare_preconditions_media_associate',
                ): '_transport_media_associate',
            },
        )

    def test_the_shared_guarded_transport_helper_is_genuinely_guarded(self):
        """Guard against vacuity in the shared-helper allowance.

        The eight export entries above are accepted only because ONE named
        helper holds the guarded `execute_business(mutation_context=...)` call
        and reaches transport by no other route. If that stopped being true,
        every one of those entries would be accepting an unguarded delegation,
        so it is asserted here directly rather than inferred.
        """
        shared = _shared_guarded_transport_node(self._addon_root())
        self.assertIsNotNone(shared, 'the shared guarded helper must exist')
        self.assertTrue(_method_has_guarded_execute_business(shared))
        self.assertFalse(_method_has_forbidden_transport(shared))
        # And a `_transport_*` method that does NOT delegate to it is still a
        # violation -- the allowance is delegation-specific, not blanket.
        self.assertFalse(_method_delegates_to_shared_transport(None))

    def test_accepted_split_real_inventory_service_passes(self):
        _, validated = self._document_bindings()
        self.assertTrue({
            (_INVENTORY_GATEWAY, 'INVENTORY_SET_QUANTITIES_DOCUMENT'),
            (_INVENTORY_GATEWAY, 'INVENTORY_ACTIVATE_DOCUMENT'),
        } <= validated)

    def test_typed_gateway_binding_rejects_wrong_consumer_import(self):
        source = (self._addon_root() / _INV_SPLIT_FILE).read_text(
            encoding='utf-8',
        ).replace(
            '    INVENTORY_SET_QUANTITIES_DOCUMENT,',
            '    UNKNOWN_INVENTORY_DOCUMENT,',
            1,
        )
        shared = _shared_guarded_transport_node(self._addon_root())
        validated, violations = _validated_document_bindings(
            self._addon_root(), shared, {_INV_SPLIT_FILE: source},
        )
        key = (_INVENTORY_GATEWAY, 'INVENTORY_SET_QUANTITIES_DOCUMENT')
        self.assertNotIn(key, validated)
        self.assertTrue(any(
            violation[0] == 'invalid_consumer'
            and violation[1:3] == key
            for violation in violations
        ))

    def test_accepted_split_real_webhook_subscription_service_passes(self):
        _, validated = self._document_bindings()
        self.assertTrue({
            (_WEBHOOK_GATEWAY, 'WEBHOOK_SUBSCRIPTION_CREATE_DOCUMENT'),
            (_WEBHOOK_GATEWAY, 'WEBHOOK_SUBSCRIPTION_DELETE_DOCUMENT'),
        } <= validated)

    def test_accepted_split_both_synthetic_pairs_pass(self):
        for prepare, transport, literal in (
            ('_prepare_preconditions_set_quantities',
             '_transport_set_quantities', 'InventorySetQuantities'),
            ('_prepare_preconditions_activate',
             '_transport_activate', 'InventoryActivate'),
        ):
            source = _make_split_source(
                prepare_name=prepare, transport_name=transport,
            ).replace('InventorySetQuantities', literal)
            self.assertEqual(
                _mutation_literal_violations(source, _INV_SPLIT_FILE), [],
                (prepare, transport),
            )

    def test_split_missing_transport_sibling_fails(self):
        source = _make_split_source(include_transport=False)
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_wrong_transport_sibling_name_fails(self):
        # prepare_set_quantities paired only with the WRONG sibling
        # (_transport_activate) -- the expected _transport_set_quantities
        # is absent.
        source = _make_split_source(
            prepare_name='_prepare_preconditions_set_quantities',
            transport_name='_transport_activate',
        )
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_wrong_class_fails(self):
        source = _make_split_source(class_name='SomeOtherModel')
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_unlisted_file_fails(self):
        # Same-shaped valid split, but in a file that is not on the
        # allowlist.
        source = _make_split_source()
        self.assertTrue(_mutation_literal_violations(
            source, 'shopify_connector_other/models/external.py',
        ))

    def test_split_transport_without_execute_business_fails(self):
        source = _make_split_source(transport_call='dispatch')
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_transport_missing_mutation_context_fails(self):
        source = _make_split_source(context_keyword='business_context')
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_transport_using_execute_fails(self):
        # Guarded call present, but the transport also reaches raw
        # `.execute(...)` -- forbidden route.
        source = _make_split_source(
            transport_forbidden='client.execute(store, request)',
        )
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_transport_using_send_fails(self):
        source = _make_split_source(
            transport_forbidden='client._send(store, request)',
        )
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_prepare_using_forbidden_transport_fails(self):
        # The prepare method itself must not reach transport.
        source = _make_split_source(
            prepare_forbidden='self.env["x"]._send(store, operation)',
        )
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_transport_using_raw_http_fails(self):
        source = _make_split_source(
            transport_forbidden='requests.post(url, json=request)',
        )
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_no_production_direct_send_caller(self):
        violations = []
        for path in self._python_files():
            relative = str(path.relative_to(self._addon_root()))
            violations.extend(_direct_send_violations(
                path.read_text(encoding='utf-8'), relative,
            ))
        self.assertFalse(violations, violations)

    def test_reconciliation_read_sender_requires_mutation_and_lease_fences(self):
        relative, class_name, method_name = RECONCILIATION_READ_SEND_SURFACE
        valid = '''
class %s:
    def %s(self, job, attempt, store, query, variables):
        self._validate_graphql_operation(
            query, variables, mutation_context=None,
        )
        if self._graphql_contains_mutation(query):
            raise ValidationError('queries only')
        lease_key, token, transport_store = (
            self._admit_v2_reconciliation_read(job.id, attempt.id, store.id)
        )
        try:
            response = self._send(
                transport_store, {'query': query}, token,
            )
            yield self._normalize_response(transport_store, response)
        except BaseException:
            self._release_lease(lease_key)
            raise
        else:
            self._release_lease(lease_key)
''' % (class_name, method_name)
        self.assertFalse(_direct_send_violations(valid, relative))
        missing_mutation_rejection = valid.replace(
            "        if self._graphql_contains_mutation(query):\n"
            "            raise ValidationError('queries only')\n",
            '',
        )
        missing_error_release = valid.replace(
            '        except BaseException:\n'
            '            self._release_lease(lease_key)\n'
            '            raise\n',
            '        except BaseException:\n'
            '            raise\n',
        )
        unknown_sender = valid.replace(method_name, 'other_sender', 1)
        for source in (
            missing_mutation_rejection, missing_error_release, unknown_sender,
        ):
            self.assertTrue(_direct_send_violations(source, relative), source)

    def test_attempt_write_surface_is_closed_and_unlink_forbidden(self):
        source = Path(
            shopify_connector_mutation_attempt.__file__
        ).read_text(encoding='utf-8')
        tree = ast.parse(source)
        class_node = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == 'ShopifyConnectorMutationAttempt'
        )
        methods = {
            node.name for node in class_node.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        required = {
            '_create_attempt_intent',
            '_record_direct_outcome',
            '_record_recovery_uncertain',
            '_record_reconciliation_result',
            '_record_inconclusive_reconciliation',
            'action_resolve_mutation_attempt',
            '_mask_terminal_evidence',
        }
        self.assertTrue(required <= methods)
        self.assertIn('unlink', methods)
        self.assertIn('can never be deleted', source)

    def test_no_attempt_direct_write_call_outside_closed_surface(self):
        violations = []
        for path in self._python_files():
            relative = str(path.relative_to(self._addon_root()))
            violations.extend(_attempt_write_violations(
                path.read_text(encoding='utf-8'), relative,
            ))
        self.assertFalse(violations, violations)

    def test_attempt_write_detector_distinguishes_real_targets(self):
        bad_sources = (
            "def bad(self, attempt):\n    attempt.write({'x': 1})\n",
            "def bad(self, attempts):\n    attempts.unlink()\n",
            "def bad(self):\n"
            "    self.env['shopify.connector.mutation.attempt'].create({})\n",
            "def bad(self, attempt):\n"
            "    attempt._surface('forged').write({'x': 1})\n",
        )
        for source in bad_sources:
            self.assertTrue(_attempt_write_violations(
                source, 'shopify_connector_core/models/unsafe.py',
            ))
        unrelated = (
            "def ok(self):\n"
            "    self.write({'state': 'connected'})\n"
        )
        self.assertFalse(_attempt_write_violations(
            unrelated, 'shopify_connector_core/models/store.py',
        ))
        unrelated_surface = (
            "class Run:\n"
            "    _name = 'shopify.connector.run'\n"
            "    def ok(self):\n"
            "        self._surface('finalize').write({'name': 'run'})\n"
        )
        self.assertFalse(_attempt_write_violations(
            unrelated_surface, 'shopify_connector_core/models/run.py',
        ))

    def test_attempt_write_detector_rejects_rogue_inherited_override(self):
        source = (
            "class Rogue:\n"
            "    _inherit = 'shopify.connector.mutation.attempt'\n"
            "    def write(self, vals):\n"
            "        return super().write(vals)\n"
        )
        self.assertTrue(_attempt_write_violations(
            source,
            'shopify_connector_other/models/mutation_attempt_extension.py',
        ))

    def test_retention_write_requires_exact_surface_payload_and_caller(self):
        relative = (
            'shopify_connector_core/models/'
            'shopify_connector_mutation_attempt_retention.py'
        )
        path = self._addon_root() / relative
        source = path.read_text(encoding='utf-8')
        self.assertFalse(_attempt_write_violations(source, relative))
        wrong_surface = source.replace(
            "records._surface('_mask_terminal_evidence')",
            "records._surface('forged')",
            1,
        )
        extra_field = source.replace(
            "'evidence_masked_at': fields.Datetime.now(),",
            "'evidence_masked_at': fields.Datetime.now(),\n"
            "                'observed_outcome': 'succeeded',",
            1,
        )
        wrong_caller = source.replace(
            'self._retention_mark_masked(self)',
            'other._retention_mark_masked(self)',
            1,
        )
        for invalid in (wrong_surface, extra_field, wrong_caller):
            self.assertTrue(_attempt_write_violations(invalid, relative))

    def test_attempt_write_detector_rejects_external_same_named_methods(self):
        external = (
            "def _record_direct_outcome(self, attempt):\n"
            "    attempt.write({'observed_outcome': 'succeeded'})\n",
            "def action_resolve_mutation_attempt(self, attempt):\n"
            "    attempt._surface('forged').write({'resolved_at': None})\n",
            "def _create_attempt_intent(self):\n"
            "    return self.env[\n"
            "        'shopify.connector.mutation.attempt'\n"
            "    ].create({})\n",
        )
        for source in external:
            violations = _attempt_write_violations(
                source, 'shopify_connector_other/models/external.py',
            )
            self.assertTrue(violations, source)

    def test_write_surface_inventory_is_exact(self):
        self.assertEqual(
            shopify_connector_mutation_attempt.WRITE_SURFACES,
            frozenset({
                '_record_direct_outcome',
                '_record_recovery_uncertain',
                '_record_reconciliation_result',
                '_record_inconclusive_reconciliation',
                'action_resolve_mutation_attempt',
                '_mask_terminal_evidence',
            }),
        )

    def test_reconciliation_admission_has_only_uncertain_owners(self):
        source = Path(
            shopify_connector_job_dispatch.__file__
        ).read_text(encoding='utf-8')
        tree = ast.parse(source)
        parents = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent
        owners = set()
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == '_ensure_reconciliation_job'
            ):
                continue
            owner = parents.get(node)
            while owner and not isinstance(owner, ast.FunctionDef):
                owner = parents.get(owner)
            owners.add(owner.name if owner else False)
        self.assertEqual(owners, {
            '_apply_validated_consequence',
            '_recover_committed_attempt_to_reconciliation',
        })

    def test_dispatch_exception_handlers_are_not_shadowed(self):
        path = Path(shopify_connector_job_dispatch.__file__)
        self.assertFalse(_exception_shadowing_violations(
            path.read_text(encoding='utf-8'), str(path),
        ))

    def test_exception_shadowing_detector_rejects_superclass_first(self):
        self.assertTrue(issubclass(ValidationError, UserError))
        self.assertTrue(issubclass(AccessError, UserError))
        invalid = '''
try:
    recover()
except UserError:
    refuse_owner()
except ValidationError:
    block_invalid_state()
'''
        violations = _exception_shadowing_violations(
            invalid, 'synthetic_invalid_recovery.py',
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0][2:], ('UserError', 'ValidationError'))

    def test_exception_shadowing_detector_accepts_specific_first(self):
        valid = '''
try:
    recover()
except (ValidationError, AccessError):
    block_invalid_state()
except UserError:
    refuse_owner()
except Exception:
    fail_closed()
'''
        self.assertFalse(_exception_shadowing_violations(
            valid, 'synthetic_valid_recovery.py',
        ))

    def test_zero_real_mutation_domain_and_calls(self):
        source = Path(
            shopify_connector_job_dispatch.__file__
        ).read_text(encoding='utf-8')
        self.assertNotIn('inventorySetQuantities', source)
        self.assertNotIn('inventoryActivate', source)
        self.assertNotIn('fulfillmentCreate', source)
        self.assertIn("'transport': 'synthetic_stub'", source)
        self.assertNotIn('_get_access_token', source)
        self.assertNotIn('requests.', source)

    def test_exact_strategy_shape_and_process_death_escape(self):
        source = Path(
            shopify_connector_job_dispatch.__file__
        ).read_text(encoding='utf-8')
        tree = ast.parse(source)
        expected = {
            'reconciliation_job_type', 'prepare_local',
            'prepare_preconditions', 'transport',
            'classify_direct_result', 'reconcile', 'apply_consequence',
        }
        self.assertEqual(
            shopify_connector_job_dispatch.MUTATION_STRATEGY_KEYS,
            frozenset(expected),
        )
        wrapper = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_drain_mutation_one'
        )
        caught = {
            ast.unparse(handler.type)
            for handler in ast.walk(wrapper)
            if isinstance(handler, ast.ExceptHandler) and handler.type
        }
        self.assertNotIn('BaseException', caught)
        precondition = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_prepare_preconditions_mutation_selftest'
        )
        precondition_source = ast.unparse(precondition)
        self.assertNotIn('self.env', precondition_source)
        self.assertNotIn('_send', precondition_source)
