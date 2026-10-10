# Feature: Multitenancy con código de invitación

Locator: odd/tasks/org-multitenancy.md (repo /home/octa/IterTrack, branch experiment/http)

## Objective

Implementar multitenancy basado en organizaciones con código de invitación:
- Cada usuario pertenece a una organización
- Cada camión pertenece a una organización
- Los usuarios solo ven y gestionan camiones de su organización
- Registro con código de invitación (sin listar empresas existentes)

## Problem

Hoy todos los endpoints de tracking son globales: cualquier usuario autenticado puede ver y modificar todos los camiones. No hay forma de separar flotas por empresa/cliente.

## Why

El MVP requiere que múltiples empresas puedan usar la plataforma de forma aislada. Sin multitenancy, no hay forma de garantizar la privacidad entre clientes.

## Scope

- Nuevo modelo `Organization` con código de invitación único
- `User.organization_id` (FK a organizations)
- `Truck.organization_id` (FK a organizations)
- Registro con `invitation_code` (crear org nueva o unirse a existente)
- Endpoints de tracking filtrados por organización del usuario actual
- Migración de Alembic
- Tests

## Constraints

- No listar empresas existentes (privacidad)
- Código de invitación suficientemente aleatorio para no ser adivinado
- Los endpoints públicos (GET location, GET iter) también deben filtrar por organización
- Mantener compatibilidad con tests existentes (conftest.py usa SQLite en memoria)

## Tasks

- [x] T1: Crear modelo `Organization` + campo `invitation_code` único
- [x] T2: Agregar `organization_id` a `User` y `Truck`
- [x] T3: Modificar esquema de registro para aceptar `invitation_code`
- [x] T4: Modificar servicio de auth para asignar organización al registrarse
- [x] T5: Modificar endpoints de tracking para filtrar por organización
- [x] T6: Crear migración de Alembic
- [x] T7: Actualizar tests (conftest + test_auth + test_tracking)
- [x] T8: Verificar `make check && make test`
- [x] T9: Modificar `UserCreate` para soportar ambos flujos (`org_name` O `invitation_code`)
- [x] T10: Modificar servicio de auth para crear org o unirse según el caso
- [x] T11: Actualizar frontend (`register.html`) para soportar ambos flujos
- [x] T12: Actualizar tests para ambos flujos (crear org + unirse con código)

## Acceptance Criteria

- [ ] Un usuario registrado con código de invitación válido queda asignado a esa organización
- [ ] Un usuario registrado con código inválido recibe error 400
- [ ] `GET /trucks` solo devuelve camiones de la organización del usuario
- [ ] `POST /trucks` asigna automáticamente la organización del usuario
- [ ] `PUT /{truck_id}/location` verifica que el camión pertenece a la organización
- [ ] No existe ningún endpoint que liste organizaciones
- [ ] Tests pasan con `make test`

## Verification

- `make check && make test`
- Migración aplica correctamente con `alembic upgrade head`

## Progress

- Estado: completado
- Tareas completadas: 12/12
- Tests: 34/34 pasando
- Migración: `f08375e32888_add_organizations_and_multitenancy.py`
