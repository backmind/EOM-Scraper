# EOM Scraper

Scraper automático para extraer artículos de El Orden Mundial y enviarlos a [Reader de Readwise](https://readwise.io/read) via email, de modo que permita la integración con el sistema de feed/intake de información con mucha menos fricción y en un lugar centralizado.

## Características

- ✅ Extracción de contenido abierto completo
- ✅ Preview de contenido premium (requiere suscripción para contenido completo)
- ✅ Detección incremental con filtro temporal (`after`)
- ✅ Integración con Readwise via email
- ✅ Gestión de estado persistente
- ✅ Rate limiting y manejo de errores
- ✅ Modo dry-run para testing
- 🔄 Autenticación premium (en desarrollo)

## Instalación

```bash
# Clonar/descargar archivos del proyecto
cd eom-scraper

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
nano .env  # Editar credenciales

# Test
python main.py --test
```

## Configuración

### Variables de entorno obligatorias

```bash
# Email para envío a Readwise
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password  # App Password de Gmail
FROM_EMAIL=tu-email@gmail.com
READWISE_EMAIL=tu-email@reader.readwise.io  # Email de Readwise Reader

# Opcional: credenciales EOM para contenido premium
EOM_USERNAME=tu-usuario-eom
EOM_PASSWORD=tu-password-eom
EOM_ENABLE_PREMIUM=true
```

### Configuración de Gmail

1. Habilitar autenticación de 2 factores
2. Generar App Password específica para el scraper
3. Usar el App Password en `SMTP_PASSWORD`

### Configuración de Readwise

1. En Readwise Reader, ir a Settings → Email
2. Copiar tu email único de importación
3. Usarlo en `READWISE_EMAIL`

## Uso

### Test de configuración
```bash
python main.py --test
```

### Enviar email de prueba
```bash
python main.py --test-email
```

### Ejecución normal
```bash
python main.py
```

### Ejecución en modo dry-run (sin enviar emails)
```bash
python main.py --dry-run
```

### Con logging debug
```bash
python main.py --log-level DEBUG
```

## Automatización

### Cron (Linux/Mac)
```bash
# Editar crontab
crontab -e

# Ejecutar cada 2 horas
0 */2 * * * cd /ruta/a/eom-scraper && /ruta/a/venv/bin/python main.py

# Ejecutar diariamente a las 9:00
0 9 * * * cd /ruta/a/eom-scraper && /ruta/a/venv/bin/python main.py
```

### Task Scheduler (Windows)
1. Abrir Task Scheduler
2. Create Basic Task
3. Configurar trigger (ej: daily)
4. Action: Start Program
5. Program: `python.exe`
6. Arguments: `main.py`
7. Start in: ruta al directorio del scraper

## Funcionamiento

1. **Detección incremental**: Usa `after` parameter para obtener solo artículos nuevos
2. **Clasificación automática**: Distingue entre contenido abierto y premium
3. **Procesamiento diferencial**:
   - Contenido abierto: artículo completo
   - Contenido premium: preview + enlace
4. **Envío a Readwise**: Emails HTML formateados para óptima lectura
5. **Gestión de estado**: Tracking de artículos procesados para evitar duplicados

## Estructura del proyecto

```
eom-scraper/
├── main.py                    # Script principal
├── config/
│   └── settings.py           # Configuración
├── core/
│   ├── api_client.py         # Cliente WordPress REST API
│   ├── content_processor.py  # Procesamiento de contenido
│   └── auth.py              # Autenticación (futuro)
├── storage/
│   └── state_manager.py     # Gestión de estado
├── delivery/
│   └── email_sender.py      # Envío de emails
└── utils/
    └── helpers.py           # Utilidades
```

## Estado de desarrollo

### ✅ Implementado
- Extracción de contenido abierto
- Detección incremental con `after`
- Envío a Readwise via email
- Gestión de estado persistente
- Rate limiting y error handling

### 🔄 En desarrollo
- Autenticación para contenido premium
- Scraping HTML para contenido protegido
- Dockerización
- Dashboard web

### 📋 Planificado
- Integración directa con Readwise API
- Filtros por categorías/tags
- Notificaciones de errores
- Métricas y monitoring

## Logs

Los logs se guardan en:
- `eom_scraper.log`: Log completo
- Consola: Output en tiempo real

## Troubleshooting

### Error de autenticación SMTP
- Verificar App Password de Gmail
- Verificar que 2FA esté habilitado
- Probar con `--test`

### No se reciben emails en Readwise
- Verificar email de Readwise Reader
- Verificar en spam
- Probar con `--test-email`

### Error "No hay artículos nuevos"
- Normal si no hay contenido nuevo
- Verificar `eom_state.json` para timestamp
- Usar `--log-level DEBUG` para más detalles

## Licencia

MIT License - Ver LICENSE file para detalles