# Flujos de trabajo por rol — Plataforma SPF

## Roles del sistema

| Rol | Descripción |
|-----|-------------|
| `GESTOR_SERVICIO` | Responsable de un servicio. Crea y gestiona las PEGs de su propio servicio. |
| `GESTOR_ECONOMICO` | Técnico económico. Valida PEGs, gestiona remesas y controla los pagos. |
| `ADMIN` | Administrador total. Tiene todos los permisos de GESTOR_ECONOMICO más la gestión del sistema. |

---

## Estados de una PEG

```
PENDIENTE (1) → VALIDADO (2) → EN_REMESA (3) → PAGADO (4)
                     ↕               ↕
               INCIDENCIA (5) ←──────┘
```

---

## 1. GESTOR_SERVICIO

### Flujo principal: Crear y gestionar una PEG

```
1. Login (/login)
        │
        ▼
2. Dashboard (/)
        │
        ├─── Ver listado de PEGs de mi servicio (/pegs/)
        │         • Solo ve las PEGs de su propio servicio (filtrado automático)
        │         • Puede filtrar por estado y texto libre
        │
        ├─── Crear nueva PEG (/pegs/nuevo) ──────────────────────────────────┐
        │         1. Seleccionar proveedor                                    │
        │              • Buscar proveedor existente                           │
        │              • O dar de alta proveedor rápido (modal)               │
        │         2. Rellenar datos del documento:                            │
        │              • Nº documento, fechas (documento/recepción/vencimto.) │
        │              • Descripción del gasto, observaciones                 │
        │              • Forma de pago prevista                               │
        │              • Líneas de IVA (base imponible + tipo)                │
        │              • IRPF (si aplica)                                     │
        │         3. Adjuntar OBLIGATORIAMENTE al menos 1 documento           │
        │              (FACTURA, FACTURA_PROFORMA, PRESUPUESTO, OTROS)        │
        │         4. Guardar → PEG creada en estado PENDIENTE                 │
        │              → Se notifica por email al equipo económico            │
        │                                                                     │
        ├─── Ver detalle de una PEG (/pegs/{id})                             │
        │         • Solo puede ver PEGs de su propio servicio                 │
        │         • Si está PAGADA: puede marcar/desmarcar "factura recibida" │
        │                                                                     │
        ├─── Editar PEG (/pegs/{id}/editar)                                  │
        │         ⚠ Solo si la PEG está en estado PENDIENTE                  │
        │         • Puede editar: descripción, nº documento, fechas,          │
        │           proveedor, forma de pago, líneas IVA                      │
        │         • NO puede cambiar el estado                                │
        │                                                                     │
        ├─── Gestionar documentos adjuntos                                    │
        │         • Subir nuevo documento a PEG existente                    │
        │         • Eliminar documento adjunto                                │
        │         • Descargar documento                                       │
        │                                                                     │
        └─── Ver / crear proveedores (/proveedores/)
                  • Puede ver el listado completo de proveedores
                  • Puede dar de alta nuevos proveedores (formulario completo)
                  • Puede editar datos básicos e IBAN de proveedores
```

### Restricciones del GESTOR_SERVICIO

| Acción | Permitido |
|--------|-----------|
| Ver PEGs de otros servicios | NO |
| Crear PEGs para otros servicios | NO |
| Editar PEGs en estado distinto a PENDIENTE | NO |
| Cambiar estado de una PEG | NO |
| Acceder a remesas | NO |
| Gestionar usuarios | NO |
| Ver analíticas y cuentas de gasto | Solo lectura al crear PEG |

---

## 2. GESTOR_ECONOMICO

### Flujo principal: Validación de PEGs

```
1. Login (/login)
        │
        ▼
2. Dashboard (/)
        │
        ├─── Ver listado de TODOS los PEGs (/pegs/)
        │         • Ve todas las PEGs de todos los servicios
        │         • Puede filtrar por servicio, estado, texto y proveedor
        │         • Alerta visual si hay PEGs en estado PAGADO sin factura recibida
        │
        └─── Proceso de validación de una PEG:
                  │
                  ▼
            PEG en PENDIENTE
                  │
                  ├─── Revisar documentación adjunta (facturas, presupuestos)
                  │
                  ├─── Si hay algún problema → Marcar como INCIDENCIA
                  │         • Añadir comentario explicando la incidencia
                  │         • El solicitante recibe notificación por email
                  │         • Desde INCIDENCIA puede volver a PENDIENTE
                  │
                  └─── Si todo es correcto → Validar PEG (/pegs/{id}/validar)
                            1. Asignar analítica del servicio
                            2. Asignar cuenta de gasto (grupo 6)
                            3. Confirmar/asignar cuenta cliente A3Con del proveedor
                            → PEG pasa a estado VALIDADO
                            → Solicitante recibe notificación por email
```

### Flujo principal: Gestión de Remesas

```
1. Crear nueva remesa (/remesas/nueva)
        │   • Descripción y banco ordenante
        │   → Estado: ABIERTA
        │
        ▼
2. Añadir PEGs validados a la remesa
        │   • Desde el detalle de la remesa: seleccionar PEGs disponibles
        │   • O desde el detalle de la PEG: asignar a remesa abierta
        │   ⚠ Solo PEGs en estado VALIDADO y con analítica asignada
        │   → PEG pasa a estado EN_REMESA
        │
        ▼
3. Generar archivo bancario (/remesas/{id}/generar)
        │   → Remesa pasa a estado GENERADA
        │   → Ya no se pueden añadir/quitar PEGs
        │
        ▼
4. Generar PDF resumen (/remesas/{id}/generar-pdf)
        │   • PDF con detalle de todos los pagos
        │
        ▼
5. Exportar Suenlace A3Con (/remesas/{id}/suenlace)
        │   • Archivo de contabilización para A3Con
        │
        ▼
6. Cerrar remesa (/remesas/{id}/cerrar)
            → Todos los PEGs de la remesa pasan a PAGADO
            → Se asigna fecha de pago automática (fecha de cierre)
            → Se genera número de factura interno automático (ej: F6001ABR)
            → Solicitante recibe notificación por email
```

### Otras acciones del GESTOR_ECONOMICO

```
Gestión de PEGs:
  • Editar PEG en estado PENDIENTE o INCIDENCIA
  • Cambios de estado permitidos:
      PENDIENTE   → VALIDADO (validación)
      PENDIENTE   → INCIDENCIA
      VALIDADO    → PENDIENTE (requiere motivo)
      EN_REMESA   → VALIDADO (requiere motivo, quita la remesa)
      INCIDENCIA  → PENDIENTE
  • Eliminar PEG (solo si NO está PAGADA)
  • Actualizar fecha de pago (solo PEGs PAGADAS)
  • Actualizar número de factura interno (solo PEGs PAGADAS)
  • Subir/eliminar documentos adjuntos

Gestión de Proveedores:
  • Ver y editar datos completos de proveedores (IBAN, cuenta A3Con, etc.)
  • Crear nuevos proveedores
  • Consultar siguiente cuenta cliente disponible (grupo 4100001+)

Mi perfil:
  • Actualizar email
  • Cambiar contraseña
```

### Restricciones del GESTOR_ECONOMICO

| Acción | Permitido |
|--------|-----------|
| Editar PEGs en estado EN_REMESA o PAGADO | NO (puede revertir estado) |
| Gestionar usuarios | NO |
| Gestionar bancos | NO |
| Gestionar cuentas de gasto | NO |
| Modificar PEGs pagadas (fecha, nº factura) | SÍ |

---

## 3. ADMIN

El ADMIN tiene **todos los permisos del GESTOR_ECONOMICO** más:

### Flujo adicional: Gestión del sistema

```
Panel de administración
        │
        ├─── Gestión de Usuarios (/usuarios/)
        │         • Listar todos los usuarios del sistema
        │         • Crear nuevo usuario:
        │              - Username, nombre, apellidos, email
        │              - Rol: GESTOR_SERVICIO / GESTOR_ECONOMICO / ADMIN
        │              - Servicios asignados (para GESTOR_SERVICIO)
        │              - Contraseña inicial
        │         • Editar usuario (datos, rol, servicios, contraseña)
        │         • Desactivar/reactivar usuario
        │
        ├─── Gestión de Bancos (/remesas/admin/bancos)
        │         • Ver listado de bancos configurados
        │         • Crear nuevo banco (nombre, BIC, IBAN ordenante)
        │         • Editar banco existente
        │         • Activar/desactivar banco
        │
        └─── Gestión de Cuentas de Gasto (/admin/cuentas-gasto)
                  • Ver listado de cuentas del grupo 6
                  • Crear nueva cuenta (código + descripción)
                  • Editar cuenta existente
                  • Activar/desactivar cuenta
```

### Diferencias clave del ADMIN frente a GESTOR_ECONOMICO

| Acción | GESTOR_ECONOMICO | ADMIN |
|--------|-----------------|-------|
| Modificar PEGs en estado PAGADO | Parcialmente (fecha, nº factura) | SIN RESTRICCIONES |
| Revertir cualquier cambio de estado | Limitado | SIN RESTRICCIONES |
| Gestionar usuarios | NO | SÍ |
| Gestionar bancos | NO | SÍ |
| Gestionar cuentas de gasto | NO | SÍ |
| Eliminar PEGs PAGADAS | NO | SÍ |

---

## Resumen de permisos por módulo

| Módulo | GESTOR_SERVICIO | GESTOR_ECONOMICO | ADMIN |
|--------|:-:|:-:|:-:|
| Ver PEGs (propias) | ✓ | — | — |
| Ver PEGs (todas) | — | ✓ | ✓ |
| Crear PEG | ✓ | ✓ | ✓ |
| Editar PEG (PENDIENTE) | ✓ (solo la suya) | ✓ | ✓ |
| Validar PEG | — | ✓ | ✓ |
| Marcar incidencia | — | ✓ | ✓ |
| Remesas | — | ✓ | ✓ |
| Ver proveedores | ✓ | ✓ | ✓ |
| Crear/editar proveedores | ✓ | ✓ | ✓ |
| Editar cuenta A3Con proveedor | — | ✓ | ✓ |
| Gestión de usuarios | — | — | ✓ |
| Gestión de bancos | — | — | ✓ |
| Cuentas de gasto | — | — | ✓ |
| Mi perfil | ✓ | ✓ | ✓ |

---

## Notificaciones por email automáticas

| Evento | Destinatario |
|--------|-------------|
| PEG creada | Equipo económico (notificación interna) |
| PEG validada (→ VALIDADO) | Solicitante (creador de la PEG) |
| PEG con incidencia (→ INCIDENCIA) | Solicitante (creador de la PEG) |
| PEG pagada (→ PAGADO) | Solicitante (creador de la PEG) |
