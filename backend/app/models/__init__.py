"""Modelos SQLAlchemy 2 (ORM). Fonte da verdade do schema é o Postgres via
Alembic (`backend/alembic/versions/`) — estes modelos apenas espelham o
schema já criado pelas migrations (colunas `server_default`, enums com
`create_type=False`, etc).
"""

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.cliente import Cliente
from app.models.company import Company
from app.models.consumed_token import ConsumedToken
from app.models.documento import Documento
from app.models.invitation import Invitation
from app.models.obra import Obra
from app.models.obra_membro import ObraMembro
from app.models.ticket import Ticket
from app.models.ticket_mensagem import TicketMensagem
from app.models.user import User
from app.models.user_company_role import UserCompanyRole

__all__ = [
    "AuditLog",
    "Base",
    "Cliente",
    "Company",
    "ConsumedToken",
    "Documento",
    "Invitation",
    "Obra",
    "ObraMembro",
    "Ticket",
    "TicketMensagem",
    "User",
    "UserCompanyRole",
]
