import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

import store
from deps import redis_client

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://admin:postgres-dev-password@localhost:5432/report_platform",
)


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Import here to avoid circular dependencies and keep the model layer lazy.
    from models import Base as ModelsBase, Organization, Role, User, UserRole

    ModelsBase.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if db.query(Organization).count() == 0:
            demo_orgs = store.get_organizations(redis_client)
            if not demo_orgs:
                demo_orgs = [
                    {
                        "id": "org-spartexai",
                        "name": "Spartexai",
                        "plan": "starter",
                        "status": "active",
                        "region": "us-east",
                        "contactEmail": "admin@spartexai.com",
                    }
                ]
                store.save_organizations(redis_client, demo_orgs)

            for org in demo_orgs:
                org_id = str(org.get("id") or "org-demo")
                existing = db.get(Organization, org_id)
                if existing is None:
                    db.add(
                        Organization(
                            id=org_id,
                            name=str(org.get("name") or org_id),
                            plan=str(org.get("plan", "free")),
                            status=str(org.get("status", "active")),
                            region=str(org.get("region", "unknown")),
                            contact_email=org.get("contactEmail") or org.get("contact_email") or f"{org_id}@example.com",
                        )
                    )
            db.commit()

    with SessionLocal() as db:
        if db.query(User).count() == 0:
            role_lookup = {role.name: role.id for role in db.query(Role).all()}
            default_users = [
                {
                    "email": "hari@spartexai.com",
                    "username": "hari",
                    "full_name": "Hari Admin",
                    "organization_id": "org-spartexai",
                    "role": "REPORT_ADMIN",
                },
                {
                    "email": "alex@spartexai.com",
                    "username": "alex",
                    "full_name": "Alex User",
                    "organization_id": "org-spartexai",
                    "role": "REPORT_USER",
                },
            ]

            for item in default_users:
                org_exists = db.get(Organization, item["organization_id"])
                if org_exists is None:
                    continue
                if not db.query(User).filter(User.email == item["email"]).first():
                    user = User(
                        email=item["email"],
                        username=item["username"],
                        full_name=item["full_name"],
                        organization_id=item["organization_id"],
                        organization_name="Spartexai",
                        region="us-east",
                        status="active",
                    )
                    db.add(user)
                    db.flush()

                    role_id = role_lookup.get(item["role"])
                    if role_id is not None and not db.query(UserRole).filter_by(user_id=user.id, role_id=role_id).first():
                        db.add(UserRole(user_id=user.id, role_id=role_id))

            db.commit()
