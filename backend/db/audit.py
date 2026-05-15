"""
Archivo: audit.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Implementa la lógica de interceptación para auditoría. Utiliza decoradores 
para registrar automáticamente los cambios en las entidades del sistema en 
la tabla de `audit_log`.

Acciones Principales:
    - Decoración de métodos de repositorio para captura de payloads.
    - Persistencia automática de registros de auditoría post-ejecución.

Estructura Interna:
    - `audited`: Decorador principal que gestiona el rastro de auditoría.

Ejemplo de Integración:
    from backend.db.audit import audited
    
    class MyRepo:
        @audited(entity="my_entity")
        def update(self, data): ...
"""

import functools
from typing import Any, Callable

from backend.db.models import AuditLog


def audited(entity: str) -> Callable[..., Any]:
    """
    Decorador para automatizar el registro de auditoría en métodos de repositorio.

    Args:
        entity (str): Nombre de la entidad afectada (ej. 'scenario', 'rules').

    Returns:
        Callable: Decorador configurado para la entidad especificada.
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
