"""Role capability contracts without Odoo/security-framework behavior."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .states import ROLE_ORDER, Role


@dataclass(frozen=True, slots=True)
class RoleCapability:
    """The supported application capabilities for one stable role.

    These booleans describe the public contract only.  Odoo ACLs, record
    rules, active-company checks and service authorization remain separate
    enforcement layers and are intentionally not implemented here.
    """

    role: Role
    can_read: bool
    can_resolve: bool
    can_operate: bool
    can_configure: bool

    def __post_init__(self) -> None:
        if not isinstance(self.role, Role):
            object.__setattr__(self, "role", Role(self.role))
        for name in ("can_read", "can_resolve", "can_operate", "can_configure"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be bool")


ROLE_CAPABILITIES: Mapping[Role, RoleCapability] = MappingProxyType({
    Role.ADMINISTRATOR: RoleCapability(
        Role.ADMINISTRATOR,
        can_read=True,
        can_resolve=True,
        can_operate=True,
        can_configure=True,
    ),
    Role.OPERATOR: RoleCapability(
        Role.OPERATOR,
        can_read=True,
        can_resolve=True,
        can_operate=True,
        can_configure=False,
    ),
    Role.REVIEWER: RoleCapability(
        Role.REVIEWER,
        can_read=True,
        can_resolve=True,
        can_operate=False,
        can_configure=False,
    ),
    Role.AUDITOR: RoleCapability(
        Role.AUDITOR,
        can_read=True,
        can_resolve=False,
        can_operate=False,
        can_configure=False,
    ),
})


def capability_for(role: Role | str) -> RoleCapability:
    """Return a supported capability or fail closed for an unknown role."""

    try:
        return ROLE_CAPABILITIES[role if isinstance(role, Role) else Role(role)]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported role: {role!r}") from exc


__all__ = ["ROLE_CAPABILITIES", "RoleCapability", "capability_for"]
