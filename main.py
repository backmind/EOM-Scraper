#!/usr/bin/env python3
"""
EOM Scraper - Scraper automático para El Orden Mundial
Extrae artículos y los envía a Readwise via email
"""
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Añadir directorio actual al path
sys.path.append(str(Path(__file__).parent))

from config.settings import load_config, validate_config
from core.api_client import EOMAPIClient
from core.content_processor import ContentProcessor
from storage.state_manager import StateManager
from delivery.email_sender import EmailSender

# Configurar logging
def setup_logging(log_level: str = "INFO"):
    """Configura el sistema de logging"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('eom_scraper.log', encoding='utf-8')
        ]
    )

class EOMScraper:
    """Scraper principal para El Orden Mundial"""
    
    def __init__(self):
        # Cargar configuración
        self.email_config, self.eom_config, self.app_config = load_config()
        
        # Validar configuración
        config_errors = validate_config(self.email_config, self.eom_config, self.app_config)
        if config_errors:
            for error in config_errors:
                logging.error(f"Error de configuración: {error}")
            raise ValueError("Configuración inválida")
        
        # Inicializar componentes
        self.api_client = EOMAPIClient(self.eom_config, self.app_config.request_delay)
        self.content_processor = ContentProcessor()
        self.state_manager = StateManager(self.app_config.state_file)
        self.email_sender = EmailSender(self.email_config, self.app_config.dry_run)
        
        # Cargar estado
        self.state = self.state_manager.load_state()
        
        self.logger = logging.getLogger(__name__)
    
    def run(self) -> bool:
        """Ejecuta el scraper completo"""
        self.logger.info("=== Iniciando EOM Scraper ===")
        
        try:
            # Test de conexión SMTP
            if not self.email_sender.test_connection():
                self.logger.error("Fallo en test de conexión email. Abortando.")
                return False
            
            # Autenticación si está habilitada
            if self.app_config.process_premium_content:
                if not self.api_client.authenticate():
                    self.logger.warning("Fallo en autenticación. Solo se procesará contenido abierto.")
                    self.app_config.process_premium_content = False
            
            # Obtener artículos nuevos
            new_articles = self._get_new_articles()
            
            if not new_articles:
                self.logger.info("No hay artículos nuevos para procesar.")
                self.state_manager.mark_successful_run()
                self.state_manager.save_state()
                return True
            
            # Procesar y enviar artículos
            processed_count = self._process_articles(new_articles)
            
            # Actualizar estado
            if processed_count > 0:
                self.state_manager.update_last_check(datetime.now(timezone.utc))
                self.state_manager.mark_successful_run()
                self.state_manager.cleanup_old_processed_ids()
            
            self.state_manager.save_state()
            
            self.logger.info(f"=== Scraper completado: {processed_count}/{len(new_articles)} artículos procesados ===")
            return True
            
        except Exception as e:
            self.logger.error(f"Error crítico en scraper: {e}", exc_info=True)
            self.state_manager.increment_error_count()
            self.state_manager.save_state()
            return False
    
    def _get_new_articles(self) -> List[Dict[str, Any]]:
        """Obtiene artículos nuevos desde la última verificación"""
        last_check = self.state_manager.get_last_check_datetime()
        self.logger.info(f"Buscando artículos desde: {last_check}")
        
        # Obtener posts desde la API
        raw_posts = self.api_client.get_posts_since(last_check)
        
        if not raw_posts:
            return []
        
        # Convertir a metadata y filtrar ya procesados
        new_articles = []
        for post in raw_posts:
            post_id = post.get('id')
            
            if not post_id:
                continue
            
            if self.state_manager.is_post_processed(post_id):
                self.logger.debug(f"Post {post_id} ya procesado, saltando")
                continue
            
            # Extraer metadata
            metadata = self.api_client.extract_post_metadata(post)
            
            # Filtrar por tipo de contenido si es necesario
            if not self._should_process_article(metadata):
                self.logger.debug(f"Post {post_id} filtrado por configuración")
                continue
            
            new_articles.append(metadata)
        
        self.logger.info(f"Encontrados {len(new_articles)} artículos nuevos para procesar")
        return new_articles
    
    def _should_process_article(self, metadata: Dict[str, Any]) -> bool:
        """Determina si un artículo debe ser procesado según la configuración"""
        access_type = metadata.get('access_type', 'unknown')
        
        if access_type == 'open' and self.app_config.process_open_content:
            return True
        
        if access_type == 'premium' and self.app_config.process_premium_content:
            return True
        
        return False
    
    def _process_articles(self, articles: List[Dict[str, Any]]) -> int:
        """Procesa y envía lista de artículos"""
        processed_count = 0
        
        for i, article_metadata in enumerate(articles, 1):
            post_id = article_metadata['id']
            title = article_metadata['title']
            
            self.logger.info(f"Procesando artículo {i}/{len(articles)}: {title} (ID: {post_id})")
            
            try:
                # Procesar contenido
                processed_article = self.content_processor.process_article(article_metadata)
                
                # Crear email
                email_content = self.content_processor.create_email_content(processed_article)
                
                # Enviar email
                if self.email_sender.send_article_email(email_content, processed_article):
                    self.state_manager.mark_post_processed(post_id)
                    processed_count += 1
                    self.logger.info(f"Artículo {post_id} enviado exitosamente")
                else:
                    self.logger.error(f"Error enviando artículo {post_id}")
                
                # Delay entre envíos para evitar spam
                if i < len(articles):  # No delay después del último
                    time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Error procesando artículo {post_id}: {e}", exc_info=True)
                continue
        
        return processed_count
    
    def test_setup(self) -> bool:
        """Prueba la configuración del scraper"""
        self.logger.info("=== Test de configuración ===")
        
        # Test API
        self.logger.info("Probando conexión API...")
        api_info = self.api_client.discover_api_endpoints()
        if api_info:
            self.logger.info("✓ API de WordPress accesible")
        else:
            self.logger.error("✗ Error accediendo a la API")
            return False
        
        # Test posts recientes
        self.logger.info("Probando obtención de posts...")
        recent_posts = self.api_client.get_all_recent_posts(5)
        if recent_posts:
            self.logger.info(f"✓ Obtenidos {len(recent_posts)} posts recientes")
            
            # Mostrar tipos de contenido
            open_count = sum(1 for p in recent_posts if self.api_client.classify_post_access(p) == 'open')
            premium_count = len(recent_posts) - open_count
            self.logger.info(f"  - Contenido abierto: {open_count}")
            self.logger.info(f"  - Contenido premium: {premium_count}")
        else:
            self.logger.error("✗ Error obteniendo posts")
            return False
        
        # Test email
        self.logger.info("Probando conexión email...")
        if self.email_sender.test_connection():
            self.logger.info("✓ Conexión SMTP exitosa")
        else:
            self.logger.error("✗ Error en conexión SMTP")
            return False
        
        # Test estado
        self.logger.info("Probando gestión de estado...")
        stats = self.state_manager.get_stats()
        self.logger.info(f"✓ Estado cargado: {stats}")
        
        self.logger.info("=== Test completado exitosamente ===")
        return True
    
    def send_test_email(self) -> bool:
        """Envía un email de prueba"""
        self.logger.info("Enviando email de prueba...")
        return self.email_sender.send_test_email()

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='EOM Scraper - Scraper para El Orden Mundial')
    parser.add_argument('--test', action='store_true', help='Ejecutar test de configuración')
    parser.add_argument('--test-email', action='store_true', help='Enviar email de prueba')
    parser.add_argument('--dry-run', action='store_true', help='Ejecutar sin enviar emails')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Nivel de logging')
    
    args = parser.parse_args()
    
    # Configurar logging
    setup_logging(args.log_level)
    
    # Override dry-run si se especifica
    if args.dry_run:
        import os
        os.environ['DRY_RUN'] = 'true'
    
    try:
        scraper = EOMScraper()
        
        if args.test:
            success = scraper.test_setup()
            sys.exit(0 if success else 1)
        
        if args.test_email:
            success = scraper.send_test_email()
            print("Email de prueba enviado exitosamente" if success else "Error enviando email de prueba")
            sys.exit(0 if success else 1)
        
        # Ejecución normal
        success = scraper.run()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logging.info("Scraper interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error crítico: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()