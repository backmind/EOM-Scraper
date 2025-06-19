"""
Módulo core para funcionalidades principales de EOM Scraper
"""
from .api_client import EOMAPIClient
from .content_processor import ContentProcessor

__all__ = ['EOMAPIClient', 'ContentProcessor']