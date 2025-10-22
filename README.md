API de comentarios

Este repositorio contiene la API de comentarios desarrollada en Python con Flask. El objetivo principal de este proyecto no es solo la funcionalidad, sino el uso de GitHub Actions para garantizar la seguridad del código, las dependencias y el contenedor en cada PR.

## Pipeline de Integración Continua y Seguridad (CI/CD)

El flujo de trabajo de CI/CD se activa en cada `push` y `Pull Request` hacia la rama `main` y está diseñado bajo el principio de **"Fail-Fast"** (Falla Rápido), bloqueando el *merge* si se detecta cualquier riesgo.

### 1. Herramientas de Seguridad Integradas

| Fase DevSecOps | Herramienta | Archivo YAML | Propósito del Escaneo |
| :--- | :--- | :--- | :--- |
| **SAST** (Static Analysis) | **Bandit** | `security_scan.yml` | Analiza el código fuente en busca de patrones inseguros (ej. *hardcoding* de credenciales). |
| **Secret Scanning** | **Gitleaks** | `security_scan.yml` | Escanea el historial completo de Git en busca de secretos expuestos (tokens, claves). |
| **DAST** (Dynamic Analysis) | **OWASP ZAP** | `security_scan.yml` | Escanea la aplicación en ejecución (Docker) buscando vulnerabilidades web (ej. Cabeceras faltantes, XSS). |
| **SCA** (Comp. Analysis) | **Trivy / Dependency Review** | `container_scan.yml` | Identifica librerías con Vulnerabilidades Conocidas (CVEs) en `requirements.txt`. |
| **Container Hardening** | **Hadolint / Dockerfile** | `container_scan.yml` | Aplica *best practices* de Docker (ej. Uso de usuario no-root). |


## Detalle de las Controles de Seguridad

### A. Hardening del Contenedor (Mínimo Privilegio)

El `Dockerfile` incluye los siguientes pasos de seguridad crítica para prevenir la escalada de privilegios en caso de compromiso:

* **Imagen Base:** Se utiliza una imagen base oficial (`python:3.11-slim`) para reducir la superficie de ataque.
* **Usuario No-Root:** La aplicación se ejecuta como el usuario de bajo privilegio **`appuser`** (`USER appuser`) y no como `root`.

### B. Mitigación de Vulnerabilidades Web (ZAP)

Para resolver las fallas de seguridad dinámica (DAST), se implementó la librería `Flask-Talisman` en `app.py`.

```python
# app.py
from flask_talisman import Talisman

Talisman(
    app, 
    force_https=False, # Necesario para el escaneo HTTP de ZAP
    frame_options='DENY',
    content_security_policy={"default-src": "'self'"}
)


Al realizar esta configuración se resolvieron las alertas de ClickJacking y la mayoría de las cabeceras faltantes de HTTP.

Control Proactivo de Dependencias (SCA)

Para demostrar la capacidad de bloqueo proactivo, se realizó la siguiente prueba:

Se introdujo intencionalmente la versión vulnerable de una dependencia (requests==2.6.0).
El check Dependency Review (SCA) falló en rojo, bloqueando el merge.
La dependencia fue actualizada a una versión segura (requests>=2.31.0), y el check pasó a verde.

Gracias a esto el Pipeline garantiza que solo se puedan utilizar dependencias limpias.

