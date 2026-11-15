"""Configuración común de las pruebas.

Las pruebas usan SQLite en memoria: NO tocan la base MySQL real.
Las variables de entorno se fijan ANTES de importar la app (la config las exige).
"""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "clave-solo-para-pruebas-de-zproject-0123456789"
os.environ["SMTP_HOST"] = ""  # nunca se envían correos reales

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra todas las tablas en Base.metadata)
from app.core.database import Base
from app.core.dependencies import getDb
from app.core.security import createAccessToken, hashPassword
from app.modules.auth.models import Permission, Role, User
from app.modules.auth.router import router as authRouter
from app.modules.client.models import Client
from app.modules.material.models import Material
from app.modules.material.router import router as materialRouter
from app.modules.printOrder.router import router as printOrderRouter


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db):
    """TestClient con una app mínima que usa la BD de pruebas."""
    app = FastAPI()
    app.include_router(authRouter)
    app.include_router(materialRouter)
    app.include_router(printOrderRouter)
    app.dependency_overrides[getDb] = lambda: db
    return TestClient(app)


# ---------- Datos de ejemplo ----------

@pytest.fixture()
def makeUser(db):
    """Crea un usuario con un rol que tiene los permisos indicados."""

    def _make(username="kenneth", password="clave12345", codes=(), isActive=True):
        permissions = []
        for code in codes:
            permission = db.query(Permission).filter_by(code=code).first()
            if permission is None:
                permission = Permission(code=code)
                db.add(permission)
            permissions.append(permission)
        role = Role(name=f"rol-{username}", permissions=permissions)
        user = User(
            username=username,
            passwordHash=hashPassword(password),
            isActive=isActive,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture()
def authHeader():
    def _header(user):
        return {"Authorization": f"Bearer {createAccessToken(user.id)}"}

    return _header


@pytest.fixture()
def makeClient(db):
    def _make(name="Cliente Prueba", email="cliente@correo.com"):
        newClient = Client(name=name, phone="8888-8888", email=email)
        db.add(newClient)
        db.commit()
        db.refresh(newClient)
        return newClient

    return _make


@pytest.fixture()
def makeMaterial(db):
    def _make(type="PLA", color="Negro", stockGrams=1000):
        material = Material(type=type, color=color, diameter=1.75, stockGrams=stockGrams)
        db.add(material)
        db.commit()
        db.refresh(material)
        return material

    return _make
