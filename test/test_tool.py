import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.dependencies import getDb
from app.modules.tool import service
from app.modules.tool.router import router as toolRouter
from app.modules.tool.schemas import ToolCreate, ToolUpdate


@pytest.fixture()
def apiClient(db):
    """App mínima con solo el router de herramientas y la BD de pruebas."""
    app = FastAPI()
    app.include_router(toolRouter)
    app.dependency_overrides[getDb] = lambda: db
    return TestClient(app)


def makeTool(db, name="Taladro", quantity=3, status="disponible"):
    return service.createTool(
        db, ToolCreate(name=name, quantity=quantity, status=status)
    )


def test_tool01_crearHerramienta(db):
    """Crear una herramienta con datos válidos.
    Esperado: activa, con los valores indicados y descripción por defecto."""
    tool = makeTool(db)

    assert tool.id is not None
    assert tool.isActive is True
    assert tool.name == "Taladro"
    assert tool.quantity == 3
    assert tool.status == "disponible"
    assert tool.description == ""


def test_tool02_nombreDuplicadoDevuelve409(db):
    """Crear una herramienta con un nombre ya registrado (otra capitalización).
    Esperado: error 409 de conflicto."""
    makeTool(db, name="Taladro")

    with pytest.raises(HTTPException) as error:
        makeTool(db, name="taladro")

    assert error.value.status_code == 409


def test_tool03_forzarDuplicadoCrea(db):
    """Registrar un duplicado confirmando con force.
    Esperado: se crea una segunda herramienta activa."""
    makeTool(db, name="Taladro")

    tool = service.createTool(
        db, ToolCreate(name="Taladro", quantity=1, status="baja"), force=True
    )

    assert tool.id is not None
    assert tool.isActive is True


def test_tool04_eliminarEsBorradoLogico(db):
    """Eliminar una herramienta.
    Esperado: queda inactiva en la BD y ya no se encuentra (404)."""
    tool = makeTool(db)

    service.deleteTool(db, tool.id)

    db.refresh(tool)
    assert tool.isActive is False
    with pytest.raises(HTTPException) as error:
        service.getTool(db, tool.id)
    assert error.value.status_code == 404


def test_tool05_filtrarPorEstado(db):
    """Listar solo las herramientas en uso.
    Esperado: la lista filtrada contiene únicamente esa herramienta."""
    makeTool(db, name="Disponible", status="disponible")
    makeTool(db, name="EnUso", status="en_uso")

    enUso = service.getTools(db, "en_uso")

    assert [tool.name for tool in enUso] == ["EnUso"]


def test_tool06_endpointSinPermisoDevuelve403(apiClient, makeUser, authHeader):
    """Listar herramientas sin el permiso tools:read y con él.
    Esperado: 403 sin permiso; 200 con permiso."""
    sinPermiso = makeUser(username="sinpermiso", codes=["warranties:read"])
    conPermiso = makeUser(username="conpermiso", codes=["tools:read"])

    denegado = apiClient.get("/tools", headers=authHeader(sinPermiso))
    permitido = apiClient.get("/tools", headers=authHeader(conPermiso))

    assert denegado.status_code == 403
    assert permitido.status_code == 200


def test_tool07_cantidadCeroNoPuedeEstarDisponible(db):
    """Crear una herramienta con cantidad 0 y estado disponible.
    Esperado: error 400 por datos incoherentes."""
    with pytest.raises(HTTPException) as error:
        service.createTool(
            db, ToolCreate(name="SinStock", quantity=0, status="disponible")
        )

    assert error.value.status_code == 400


def test_tool08_cantidadCeroEnMantenimientoEsValida(db):
    """Crear una herramienta con cantidad 0 y estado mantenimiento.
    Esperado: se crea, porque no promete unidades operativas."""
    tool = service.createTool(
        db, ToolCreate(name="EnMantenimiento", quantity=0, status="mantenimiento")
    )

    assert tool.id is not None
    assert tool.status == "mantenimiento"


def test_tool09_editarCantidadACeroConDisponibleFalla(db):
    """Editar solo la cantidad a 0 de una herramienta disponible.
    Esperado: error 400 usando el estado actual."""
    tool = makeTool(db, name="Taladro", quantity=3, status="disponible")

    with pytest.raises(HTTPException) as error:
        service.updateTool(db, tool.id, ToolUpdate(quantity=0))

    assert error.value.status_code == 400
