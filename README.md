# 🏋️ Gestor de Gimnasios

Sistema web para administrar gimnasios con varias sedes: socios, planes de membresía, cobros y control de asistencias en recepción.

> Proyecto académico desarrollado con metodología **Scrum** (historias de usuario y criterios de aceptación gestionados en Jira).

---

## ✨ Funcionalidades

- **Registro de administrador** junto con su gimnasio, y acceso con **roles** (Administrador y Encargado)
- **Multisede:** cada usuario solo ve la información de los gimnasios que tiene asignados
- **Socios:** alta con número de referencia automático, búsqueda, ficha y edición
- **Planes de membresía:** creación y edición con descuento y precio final calculado
- **Membresías:** asignación de planes a socios con fecha de vencimiento automática
- **Cobros:** registro de pagos (efectivo, tarjeta o transferencia), desglose del primer pago y renovaciones, e historial
- **Recepción:** registro de entradas, validando que el socio tenga una membresía vigente

---

## 🛠️ Tecnologías

| Capa | Tecnologías |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy 2 (ORM), Pydantic |
| Base de datos | SQLite (desarrollo) |
| Seguridad | JWT, contraseñas cifradas con Argon2, control de acceso por roles (RBAC) |
| Frontend | HTML, CSS y JavaScript |
| Pruebas | pytest (más de 100 pruebas automatizadas), Postman |
| Metodología | Scrum con Jira |

---

## 🏗️ Arquitectura

```
Frontend (HTML/CSS/JS)  ──►  API REST (FastAPI)  ──►  SQLAlchemy  ──►  Base de datos
```

La API está organizada en capas: **modelos** (tablas), **esquemas** (validación de datos), **endpoints** (rutas) y **dependencias** (autenticación y permisos por gimnasio).

| Módulo | Ruta |
|---|---|
| Autenticación | `/api/v1/auth` |
| Gimnasios y planes | `/api/v1/gyms` |
| Usuarios | `/api/v1/users` |
| Socios, membresías y cobros | `/api/v1/socios` |
| Asistencias | `/api/v1/attendance` |

---

## 🚀 Cómo correrlo localmente

**Requisitos:** Python 3.11+

```bash
python -m venv .venv
.venv\Scripts\activate        # En Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- Aplicación: http://127.0.0.1:8000
- Documentación interactiva de la API: http://127.0.0.1:8000/docs

Para usarlo fuera de desarrollo, crea un archivo `.env` con tu propia clave:

```env
SECRET_KEY=TU_CLAVE_SECRETA
```

### Pruebas

```bash
pytest
```

---

## 📁 Estructura

```
app/
├── api/          # Endpoints y dependencias (auth, permisos por gimnasio)
├── core/         # Configuración, seguridad, fechas y errores
├── db/           # Conexión a la base de datos
├── models/       # Tablas: gimnasios, usuarios, socios, planes, pagos, asistencias
├── schemas/      # Validación de datos con Pydantic
├── static/       # Interfaz web (login, socios, planes, cobros, recepción)
└── tests/        # Pruebas automatizadas con pytest
```

---

## 📬 Contacto

**Josué Gasca** · Desarrollador web y de bases de datos
✉️ gascajosueabdiel@gmail.com · 🐙 [github.com/gascajosueabdiel-dev](https://github.com/gascajosueabdiel-dev)
