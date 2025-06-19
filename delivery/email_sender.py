"""
Envío de emails a Readwise
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Dict, Any
from config.settings import EmailConfig

logger = logging.getLogger(__name__)

class EmailSender:
    """Enviador de emails para integración con Readwise"""
    
    def __init__(self, config: EmailConfig, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
    
    def send_article_email(self, email_content: Dict[str, str], 
                          article_metadata: Dict[str, Any]) -> bool:
        """Envía un artículo por email a Readwise"""
        
        if self.dry_run:
            logger.info(f"DRY RUN: Email que se enviaría:")
            logger.info(f"To: {self.config.readwise_email}")
            logger.info(f"Subject: {email_content['subject']}")
            logger.info(f"Article ID: {article_metadata.get('id')}")
            logger.info(f"Article URL: {article_metadata.get('url')}")
            return True
        
        try:
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['Subject'] = email_content['subject']
            msg['From'] = formataddr((self.config.from_name, self.config.from_email))
            msg['To'] = self.config.readwise_email
            
            # Añadir headers específicos para Readwise (si los tienen)
            msg['X-Readwise-Source'] = 'eom-scraper'
            msg['X-Article-URL'] = article_metadata.get('url', '')
            msg['X-Article-ID'] = str(article_metadata.get('id', ''))
            
            # Crear contenido HTML
            html_part = MIMEText(email_content['body'], 'html', 'utf-8')
            msg.attach(html_part)
            
            # Enviar email
            return self._send_smtp_email(msg)
            
        except Exception as e:
            logger.error(f"Error creando email para artículo {article_metadata.get('id')}: {e}")
            return False
    
    def _send_smtp_email(self, msg: MIMEMultipart) -> bool:
        """Envía email via SMTP"""
        try:
            # Configurar servidor SMTP
            if self.config.smtp_port == 465:
                # SSL
                server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)
            else:
                # TLS
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
                server.starttls()
            
            # Autenticación
            server.login(self.config.smtp_username, self.config.smtp_password)
            
            # Enviar
            text = msg.as_string()
            server.sendmail(self.config.from_email, self.config.readwise_email, text)
            server.quit()
            
            logger.info(f"Email enviado exitosamente: {msg['Subject']}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("Error de autenticación SMTP. Verificar credenciales.")
            return False
        except smtplib.SMTPRecipientsRefused:
            logger.error(f"Email rechazado: {self.config.readwise_email}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"Error SMTP: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado enviando email: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Prueba la conexión SMTP"""
        if self.dry_run:
            logger.info("DRY RUN: Test de conexión SMTP simulado")
            return True
        
        try:
            if self.config.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)
            else:
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
                server.starttls()
            
            server.login(self.config.smtp_username, self.config.smtp_password)
            server.quit()
            
            logger.info("Conexión SMTP exitosa")
            return True
            
        except Exception as e:
            logger.error(f"Error en test de conexión SMTP: {e}")
            return False
    
    def send_test_email(self) -> bool:
        """Envía un email de prueba"""
        test_content = {
            'subject': 'EOM Scraper - Test de conexión',
            'body': '''
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Test de EOM Scraper</h2>
                <p>Este es un email de prueba para verificar la integración con Readwise.</p>
                <p>Si recibes este mensaje, la configuración es correcta.</p>
                <hr>
                <small>Enviado automáticamente por EOM Scraper</small>
            </body>
            </html>
            ''',
            'html': True
        }
        
        test_metadata = {
            'id': 'test',
            'url': 'https://elordenmundial.com',
            'title': 'Test Article'
        }
        
        return self.send_article_email(test_content, test_metadata)