"""
Funciones auxiliares y utilidades generales
"""
import re
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def format_datetime(dt_str: str, output_format: str = "%d/%m/%Y %H:%M") -> str:
    """
    Formatea una fecha de WordPress a formato legible
    
    Args:
        dt_str: Fecha en formato ISO (ej: "2025-06-19T07:00:00")
        output_format: Formato de salida
    
    Returns:
        Fecha formateada o string original si hay error
    """
    if not dt_str:
        return ""
    
    try:
        # Manejar diferentes formatos de fecha de WordPress
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        elif '+' not in dt_str and not dt_str.endswith('+00:00'):
            dt_str += '+00:00'
        
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime(output_format)
    except ValueError as e:
        logger.warning(f"Error formateando fecha '{dt_str}': {e}")
        return dt_str

def clean_filename(filename: str, max_length: int = 100) -> str:
    """
    Limpia un string para usar como nombre de archivo
    
    Args:
        filename: String a limpiar
        max_length: Longitud máxima del filename
    
    Returns:
        Filename válido
    """
    if not filename:
        return "untitled"
    
    # Remover caracteres no válidos
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remover espacios múltiples y caracteres especiales
    cleaned = re.sub(r'\s+', '_', cleaned)
    cleaned = re.sub(r'[^\w\-_.]', '', cleaned)
    
    # Truncar si es muy largo
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    # Asegurar que no esté vacío
    if not cleaned or cleaned == '_':
        cleaned = "untitled"
    
    return cleaned

def extract_domain(url: str) -> Optional[str]:
    """
    Extrae el dominio de una URL
    
    Args:
        url: URL completa
    
    Returns:
        Dominio o None si hay error
    """
    if not url:
        return None
    
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception as e:
        logger.warning(f"Error extrayendo dominio de '{url}': {e}")
        return None

def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Trunca texto manteniendo palabras completas
    
    Args:
        text: Texto a truncar
        max_length: Longitud máxima
        suffix: Sufijo para texto truncado
    
    Returns:
        Texto truncado
    """
    if not text or len(text) <= max_length:
        return text
    
    # Truncar en la última palabra completa
    truncated = text[:max_length].rsplit(' ', 1)[0]
    
    return truncated + suffix

def extract_reading_time_from_content(html_content: str, wpm: int = 200) -> int:
    """
    Estima tiempo de lectura desde contenido HTML
    
    Args:
        html_content: Contenido HTML
        wpm: Palabras por minuto
    
    Returns:
        Tiempo estimado en minutos
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return 1
    
    # Extraer texto limpio
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    
    # Contar palabras
    word_count = len(text.split())
    
    # Calcular tiempo (mínimo 1 minuto)
    read_time = max(1, round(word_count / wpm))
    
    return read_time

def is_valid_email(email: str) -> bool:
    """
    Valida formato de email básico
    
    Args:
        email: Email a validar
    
    Returns:
        True si el formato es válido
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def sanitize_html_for_email(html_content: str) -> str:
    """
    Sanitiza HTML para compatibilidad con clientes de email
    
    Args:
        html_content: Contenido HTML
    
    Returns:
        HTML sanitizado
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remover elementos problemáticos en emails
    for element in soup.find_all(['script', 'style', 'meta', 'link']):
        element.decompose()
    
    # Convertir estilos complejos a básicos
    for element in soup.find_all(style=True):
        # Mantener solo estilos básicos seguros para email
        style = element.get('style', '')
        safe_styles = []
        
        for style_rule in style.split(';'):
            if any(prop in style_rule.lower() for prop in ['color', 'font-size', 'text-align', 'margin', 'padding']):
                safe_styles.append(style_rule.strip())
        
        if safe_styles:
            element['style'] = '; '.join(safe_styles)
        else:
            del element['style']
    
    return str(soup)

def get_current_timestamp() -> str:
    """
    Obtiene timestamp actual en formato ISO
    
    Returns:
        Timestamp en formato ISO UTC
    """
    return datetime.now(timezone.utc).isoformat()