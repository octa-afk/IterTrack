Al agregar un endpoint nuevo a `source/services/`, seguí este checklist:

1. Validación de entrada con esquemas Pydantic (`source/schemas/`), con `Field(ge=..., le=...)` para rangos numéricos.
2. Sesión inyectada: `db: Session = Depends(get_db)`.
3. Si es escritura (POST/PUT/DELETE): proteger con `current_user: models.User = Depends(get_current_user)`.
4. Errores semánticos: `raise HTTPException(status_code=...)` (400/401/404/409/422), nunca dicts con `{"error": ...}`.
5. Tag del router correcto (`tags=["trucks"]`, `tags=["auth"]`, `tags=["devices"]`, ...).
6. Test en `tests/` que cubra el caso feliz y al menos un error (400/404/422).
7. Si el endpoint impacta la UI, actualizá el cliente tipado en `frontend/src/api/` y documentá la fila en la tabla de `README.md`.
8. Correr `make check && make test` antes de dar por terminado; si tocaste `frontend/`, también `npm --prefix frontend run lint` y `npm --prefix frontend run build`.
