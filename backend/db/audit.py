"""Decorador @audited para persistir cambios en audit_log."""

import functools
from typing import Any, Callable

from backend.db.models import AuditLog


def audited(entity: str) -> Callable[..., Any]:
    """Decora métodos de repo que reciben (self, *args, **kwargs).

    Espera que `self.session` sea una SQLAlchemy Session activa.
    Registra un AuditLog después de ejecutar la función.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            result = fn(self, *args, **kwargs)
            payload: dict[str, Any] = {}
            if args:
                first = args[0]
                try:
                    payload = (
                        first.model_dump()
                        if hasattr(first, "model_dump")
                        else {"value": str(first)}
                    )
                except Exception:
                    payload = {}
            scenario_id = kwargs.get("scenario_id") or (
                args[0] if args and isinstance(args[0], int) else None
            )
            if not isinstance(scenario_id, int):
                scenario_id = None
            self.session.add(
                AuditLog(
                    scenario_id=scenario_id,
                    entity=entity,
                    payload=payload,
                )
            )
            self.session.flush()
            return result

        return wrapper

    return decorator
