import unittest

from sqlalchemy import Column, ForeignKey, String, Text, JSON, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

import routes


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    keycloak_user_id = Column(String(255), nullable=True, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(150), nullable=False)
    organization_id = Column(String(36), nullable=True)
    tenant_id = Column(String(100), nullable=True)


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(String(36), primary_key=True, default=lambda: "log-1")
    organization_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    job_id = Column(String(36), nullable=True)
    data_source_id = Column(String(36), nullable=True)
    execution_engine = Column(String(50), nullable=True)
    query_id = Column(String(100), nullable=True)
    stage = Column(String(100), nullable=False, default="backend")
    source = Column(String(50), nullable=False, default="backend")
    status = Column(String(20), nullable=False, default="info")
    message = Column(Text, nullable=False)
    error_details = Column(Text, nullable=True)
    context = Column(JSON, nullable=True)


class ExecutionLogRecordTests(unittest.TestCase):
    def test_record_execution_log_uses_db_user_id_for_keycloak_user(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

        with SessionLocal() as db:
            db.add(User(id="app-user-123", keycloak_user_id=None, email="user@example.com", username="user", organization_id="org-1", tenant_id="org-1"))
            db.commit()

        routes.SessionLocal = SessionLocal
        routes.User = User
        routes.ExecutionLog = ExecutionLog

        routes._record_execution_log(
            organization_id="org-1",
            user_id="kc-user-456",
            job_id="job-123",
            data_source_id="ds-1",
            execution_engine="spark",
            query_id="query-1",
            stage="ui_request",
            source="ui",
            status="info",
            message="Report request received",
            context={"prompt": "sales"},
            email="user@example.com",
            username="user",
        )

        with SessionLocal() as db:
            log = db.query(ExecutionLog).first()
            self.assertIsNotNone(log)
            self.assertEqual(log.user_id, "app-user-123")
            self.assertEqual(log.organization_id, "org-1")


if __name__ == "__main__":
    unittest.main()
