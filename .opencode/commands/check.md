Ejecutá los chequeos de calidad del proyecto:

1. `make check` (sintaxis/imports de los módulos clave).
2. `make test` (suite de pytest).
3. Si tocaste `frontend/`: `npm --prefix frontend run lint` (oxlint) y
   `npm --prefix frontend run build` (typecheck + build).

Los tests de servido de la SPA y de regresiones de CSS requieren `frontend/dist`;
si falta, corré `make frontend` o se saltean.

Reportá qué falló y proponé fix. No commitees nada sin confirmación.
