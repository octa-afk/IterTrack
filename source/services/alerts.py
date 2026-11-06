"""Alertas operativas: rechazos de ingesta agrupados por equipo y problema.

Un rechazo de telemetría no es un error del cliente HTTP: es un equipo que está
mal aprovisionado, sin asignación vigente o con el reloj corrido. Agrupado, el
operador ve "equipo X, 40 puntos rechazados por falta de asignación" en lugar de
tener que leer la tabla de evidencia.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from source import models
from source.database.database import get_db
from source.models.user import ROLE_PLATFORM_ADMIN
from source.services.auth import get_current_user, require_org_admin

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _summary(alert: models.Alert) -> dict:
    return {
        "id": alert.id,
        "device": alert.device.identifier if alert.device is not None else None,
        "problem_type": alert.problem_type,
        "organization_id": alert.organization_id,
        "created_at": alert.created_at,
        "latest_occurrence_at": alert.latest_occurrence_at,
        "occurrences": len(alert.occurrences),
    }


@router.get("")
def list_alerts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Alertas abiertas, la ocurrencia más reciente primero."""
    query = db.query(models.Alert).filter(models.Alert.status == "open")
    if current_user.role != ROLE_PLATFORM_ADMIN:
        query = query.filter(models.Alert.organization_id == current_user.organization_id)
    alerts = query.order_by(models.Alert.latest_occurrence_at.desc()).all()
    return [_summary(alert) for alert in alerts]


@router.post("/{alert_id}/close")
def close_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_org_admin),
):
    """Cierra una alerta abierta. Si el problema vuelve, se abre otra enlazada."""
    alert = db.get(models.Alert, alert_id)
    # Una alerta ajena responde 404, igual que en organizaciones: no se filtra
    # la existencia de datos de otra empresa.
    if alert is None or (
        current_user.role != ROLE_PLATFORM_ADMIN
        and alert.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="alerta no encontrada"
        )
    if alert.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La alerta ya está cerrada",
        )
    alert.status = "closed"
    alert.closed_at = datetime.now(UTC)
    db.commit()
    return {"mensaje": "Alerta cerrada"}
