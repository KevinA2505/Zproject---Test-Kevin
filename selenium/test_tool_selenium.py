import os
import shutil
import tempfile
import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.getenv("ZP_BASE_URL", "http://localhost:5173")
USER = os.getenv("ZP_USER", "admin")
PASSWORD = os.getenv("ZP_PASS", "")


@pytest.fixture()
def driver():
    options = webdriver.EdgeOptions()
    options.add_argument("--start-maximized")
    profile = None
    if os.getenv("ZP_HEADLESS") == "1":
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-sync")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        profile = tempfile.mkdtemp(prefix="edge-profile-")
        options.add_argument(f"--user-data-dir={profile}")

    d = webdriver.Edge(options=options)
    d.implicitly_wait(2)
    yield d
    d.quit()
    if profile:
        shutil.rmtree(profile, ignore_errors=True)


def wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def js_click(driver, locator):
    element = wait(driver).until(EC.visibility_of_element_located(locator))
    driver.execute_script("arguments[0].click();", element)


def click_guardar(driver):
    js_click(driver, (By.XPATH, "//button[contains(., 'Guardar')]"))


def login(driver):
    if not PASSWORD:
        pytest.fail("Define ZP_PASS antes de ejecutar las pruebas")

    driver.get(f"{BASE_URL}/login")
    wait(driver).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//label[contains(., 'Usuario')]/following::input[1]")
        )
    ).send_keys(USER)

    driver.find_element(
        By.XPATH, "//label[contains(., 'Contraseña')]/following::input[1]"
    ).send_keys(PASSWORD)

    driver.find_element(By.XPATH, "//button[contains(., 'Iniciar sesión')]").click()
    wait(driver).until(lambda d: "/login" not in d.current_url)


def go_tools(driver):
    driver.get(f"{BASE_URL}/tools")
    wait(driver).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//button[contains(., 'Nueva herramienta')]")
        )
    )


def unique_name(prefix="Tool Selenium"):
    return f"{prefix} {int(time.time() * 1000)}"


def open_create(driver, name, description="Creada por Selenium", quantity=1):
    js_click(driver, (By.XPATH, "//button[contains(., 'Nueva herramienta')]"))

    wait(driver).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//label[contains(., 'Nombre')]/following::input[1]")
        )
    ).send_keys(name)

    driver.find_element(
        By.XPATH, "//label[contains(., 'Descripción')]/following::input[1]"
    ).send_keys(description)

    qty = driver.find_element(
        By.XPATH, "//label[contains(., 'Cantidad')]/following::input[1]"
    )
    qty.clear()
    qty.send_keys(str(quantity))

    click_guardar(driver)


def create_tool(driver, name, description="Creada por Selenium", quantity=1):
    open_create(driver, name, description, quantity)
    wait(driver).until(
        EC.visibility_of_element_located((By.XPATH, f"//td[contains(., '{name}')]"))
    )


def row_by_name(driver, name):
    return driver.find_element(By.XPATH, f"//tr[td[contains(., '{name}')]]")


def matching_rows(driver, name):
    return driver.find_elements(By.XPATH, f"//tr[td[contains(., '{name}')]]")


def delete_tool(driver, name):
    before = len(matching_rows(driver, name))
    if before == 0:
        raise AssertionError(f"No se encontró la herramienta: {name}")

    delete_button = row_by_name(driver, name).find_element(
        By.XPATH, ".//button[contains(., 'Eliminar')]"
    )
    driver.execute_script("arguments[0].click();", delete_button)

    js_click(
        driver,
        (By.XPATH, "//*[@role='dialog']//button[contains(., 'Eliminar')]"),
    )

    wait(driver).until(
        lambda d: len(matching_rows(d, name)) == before - 1
    )


def test_tool_selenium_01_listar(driver):
    login(driver)
    go_tools(driver)

    assert driver.find_element(
        By.XPATH, "//h2[contains(., 'Herramientas')]"
    ).is_displayed()
    assert driver.find_element(
        By.XPATH, "//button[contains(., 'Nueva herramienta')]"
    ).is_displayed()


def test_tool_selenium_02_crear(driver):
    login(driver)
    go_tools(driver)

    name = unique_name()
    create_tool(driver, name)

    assert name in driver.page_source
    delete_tool(driver, name)


def test_tool_selenium_03_duplicado_con_force(driver):
    login(driver)
    go_tools(driver)

    name = unique_name("Tool Duplicada")
    create_tool(driver, name)

    open_create(driver, name)

    js_click(
        driver,
        (By.XPATH, "//*[@role='dialog']//button[contains(., 'Crear de todas formas')]"),
    )

    wait(driver).until(
        lambda d: len(d.find_elements(By.XPATH, f"//tr[td[contains(., '{name}')]]")) >= 2
    )

    delete_tool(driver, name)
    delete_tool(driver, name)


def test_tool_selenium_04_editar(driver):
    login(driver)
    go_tools(driver)

    name = unique_name("Tool Editar")
    description = "Descripcion editada por Selenium"
    create_tool(driver, name, description="Descripcion original")

    edit_button = row_by_name(driver, name).find_element(
        By.XPATH, ".//button[contains(., 'Editar')]"
    )
    driver.execute_script("arguments[0].click();", edit_button)

    field = wait(driver).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//label[contains(., 'Descripción')]/following::input[1]")
        )
    )
    field.clear()
    field.send_keys(description)

    click_guardar(driver)

    wait(driver).until(
        EC.visibility_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{name}')]][td[contains(., '{description}')]]")
        )
    )

    delete_tool(driver, name)


def test_tool_selenium_05_eliminar(driver):
    login(driver)
    go_tools(driver)

    name = unique_name("Tool Eliminar")
    create_tool(driver, name)
    delete_tool(driver, name)

    assert name not in driver.page_source