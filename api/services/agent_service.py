

from sqlalchemy.orm import Session
from models import Agent  # Import the Agent model

class AgentService:
    def get_agents_for_user(self, db: Session, user_id: int):
        """
        Obtiene todos los agentes disponibles para un usuario:
        - Sus agentes privados
        - Agentes del sistema
        """
        # Consulta que combina agentes propios del usuario y agentes del sistema
        return db.query(Agent).filter(
            # El agente pertenece al usuario O es un agente del sistema
            ((Agent.user_id == user_id) | (Agent.is_system_agent == True))
        ).all()