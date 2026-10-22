# odd/tasks/admin-truck-lifecycle.md

## Objetivo
Agregar endpoints administrativos para gestionar el ciclo de vida de camiones (alta, desactivar, reasignar organización) restringidos a usuarios con rol admin, y diferenciar permisos entre administradores y clientes.

## Rama
develop → feature/admin-truck-lifecycle

## Estrategia de entrega
ask-on-risk (default)

## Runner de tests
make test

## Specs
S1: Agregar campo `role` al modelo `User` (valores "admin" y "cliente", default "cliente").
S2: Migración de Alembic que agrega la columna `role` a la tabla `users`.
S3: Dependencia `get_current_admin_user` que requiere `current_user.role == "admin"`, de lo contrario 403.
S4: Endpoint PATCH `/trucks/{truck_id}/activate` que cambia `active` a true o false. Solo admin. Rechaza 404 si el camión no pertenece a la organización del admin.
S5: Endpoint PATCH `/trucks/{truck_id}/organization` que reasigna el camión a otra organización. Solo admin. Rechaza 404 si el camión no pertenece a la organización del admin o si la organización destino no existe.
S6: Restringir `POST /trucks` (alta de camión) solo a usuarios admin.
S7: Restringir `DELETE /trucks/{truck_id}/iter` (borrar historial) solo a usuarios admin.
S8: Los endpoints GET (`/trucks`, `/trucks/{id}/location`, `/trucks/{id}/iter`) permanecen disponibles para usuarios autenticados (consulta), filtrados por organización.
S9: Tests que cubren: cliente no puede activar/desactivar, cliente no puede reasignar, cliente no puede crear camión, cliente no puede borrar historial, admin sí puede hacer todas esas operaciones, aislamiento entre organizaciones (admin de org A no toca camiones de org B), historial retenido al desactivar, camión inactivo rechaza nuevas ubicaciones.

## Tasks
T1 — S1, S2 — inline — commit f0ea281 (agregado en este branch)
T2 — S3 — inline — commit 79ed01f (anterior en este branch)
T3 — S4 — inline — commit 79ed01f (anterior en este branch)
T4 — S5 — inline — commit 5282094 (anterior en este branch)
T5 — S6, S7 — inline — commit 25f363c (anterior en este branch)
T6 — S8, S9 — inline — commit 5d0f61b (anterior en este branch)

## Log
L1: usuario pidió implementar endpoints administrativos de camiones (alta, desactivar, reasignar organización) restringidos a admin, diferenciando permisos admin/cliente.
