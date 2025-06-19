"""
Configuración centralizada para EOM Scraper
"""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class EmailConfig:
    """Configuración para envío de emails a Readwise"""
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    readwise_email: str
    from_email: str
    from_name: str = "EOM Scraper"

@dataclass
class EOMConfig:
    """Configuración para El Orden Mundial"""
    base_url: str = "https://elordenmundial.com"
    api_base: str = "/wp-json/wp/v2"
    max_per_page: int = 100
    
    # Credenciales para contenido premium (futuro)
    username: Optional[str] = None
    password: Optional[str] = None
    enable_premium: bool = False

@dataclass
class AppConfig:
    """Configuración general de la aplicación"""
    state_file: str = "eom_state.json"
    log_level: str = "INFO"
    dry_run: bool = False  # Para testing sin enviar emails
    
    # Filtros de contenido
    process_open_content: bool = True
    process_premium_content: bool = False
    
    # Rate limiting
    request_delay: float = 1.0  # segundos entre requests

def load_config() -> tuple[EmailConfig, EOMConfig, AppConfig]:
    """Carga configuración desde variables de entorno"""
    
    email_config = EmailConfig(
        smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        smtp_port=int(os.getenv('SMTP_PORT', '587')),
        smtp_username=os.getenv('SMTP_USERNAME', ''),
        smtp_password=os.getenv('SMTP_PASSWORD', ''),
        readwise_email=os.getenv('READWISE_EMAIL', ''),
        from_email=os.getenv('FROM_EMAIL', ''),
        from_name=os.getenv('FROM_NAME', 'EOM Scraper')
    )
    
    eom_config = EOMConfig(
        username=os.getenv('EOM_USERNAME'),
        password=os.getenv('EOM_PASSWORD'),
        enable_premium=os.getenv('EOM_ENABLE_PREMIUM', 'false').lower() == 'true'
    )
    
    app_config = AppConfig(
        state_file=os.getenv('STATE_FILE', 'eom_state.json'),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        dry_run=os.getenv('DRY_RUN', 'false').lower() == 'true',
        process_premium_content=eom_config.enable_premium,
        request_delay=float(os.getenv('REQUEST_DELAY', '1.0'))
    )
    
    return email_config, eom_config, app_config

def validate_config(email_config: EmailConfig, eom_config: EOMConfig, app_config: AppConfig) -> list[str]:
    """Valida la configuración y retorna lista de errores"""
    errors = []
    
    if not email_config.readwise_email:
        errors.append("READWISE_EMAIL es obligatorio")
    
    if not email_config.from_email:
        errors.append("FROM_EMAIL es obligatorio")
    
    if not email_config.smtp_username or not email_config.smtp_password:
        errors.append("SMTP_USERNAME y SMTP_PASSWORD son obligatorios")
    
    if app_config.process_premium_content and (not eom_config.username or not eom_config.password):
        errors.append("EOM_USERNAME y EOM_PASSWORD son obligatorios para contenido premium")
    
    return errors