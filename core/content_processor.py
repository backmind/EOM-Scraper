"""
Procesador de contenido para artículos de EOM
"""
import re
import logging
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)

class ContentProcessor:
    """Procesador de contenido de artículos"""
    
    def __init__(self):
        self.soup_parser = 'html.parser'
    
    def process_article(self, post_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa un artículo completo"""
        processed = {
            'id': post_metadata['id'],
            'title': self._clean_title(post_metadata['title']),
            'url': post_metadata['url'],
            'date': self._format_date(post_metadata['date']),
            'access_type': post_metadata['access_type'],
            'categories': post_metadata['categories'],
            'tags': post_metadata['tags'],
            'author_id': post_metadata['author_id']
        }
        
        if post_metadata['access_type'] == 'open':
            processed.update(self._process_open_content(post_metadata))
        else:
            processed.update(self._process_premium_content(post_metadata))
        
        return processed
    
    def _process_open_content(self, post_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa contenido abierto completo"""
        content_html = post_metadata['content_raw']
        
        # Limpiar HTML
        cleaned_content = self._clean_html_content(content_html)
        
        # Extraer texto plano para preview
        text_content = self._extract_text_content(content_html)
        
        # Extraer imágenes
        images = self._extract_images(content_html)
        
        return {
            'content_html': cleaned_content,
            'content_text': text_content,
            'excerpt': self._clean_excerpt(post_metadata['excerpt']),
            'images': images,
            'word_count': len(text_content.split()),
            'estimated_read_time': self._estimate_read_time(text_content)
        }
    
    def _process_premium_content(self, post_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa contenido premium (solo excerpt por ahora)"""
        excerpt_html = post_metadata['content_raw']
        
        # Extraer solo el excerpt del paywall
        soup = BeautifulSoup(excerpt_html, self.soup_parser)
        excerpt_div = soup.find('div', class_='mepr-unauthorized-excerpt')
        
        if excerpt_div:
            excerpt_content = str(excerpt_div)
            text_content = excerpt_div.get_text(strip=True)
        else:
            excerpt_content = post_metadata['excerpt']
            text_content = self._extract_text_content(post_metadata['excerpt'])
        
        return {
            'content_html': excerpt_content,
            'content_text': text_content,
            'excerpt': self._clean_excerpt(post_metadata['excerpt']),
            'images': [],
            'word_count': len(text_content.split()),
            'estimated_read_time': 1,  # Mínimo para excerpts
            'requires_subscription': True
        }
    
    def _clean_html_content(self, html_content: str) -> str:
        """Limpia el contenido HTML"""
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, self.soup_parser)
        
        # Remover elementos de paywall
        for element in soup.find_all('div', class_=['mp_wrapper', 'payment-wall', 'mepr-login-form-wrap']):
            element.decompose()
        
        # Remover scripts
        for script in soup.find_all('script'):
            script.decompose()
        
        # Remover estilos inline excesivos
        for element in soup.find_all(style=True):
            del element['style']
        
        # Limpiar atributos innecesarios pero mantener estructura
        allowed_attrs = ['href', 'src', 'alt', 'title', 'class']
        for element in soup.find_all():
            attrs_to_remove = [attr for attr in element.attrs if attr not in allowed_attrs]
            for attr in attrs_to_remove:
                del element[attr]
        
        return str(soup)
    
    def _extract_text_content(self, html_content: str) -> str:
        """Extrae texto plano del HTML"""
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, self.soup_parser)
        
        # Remover elementos no deseados
        for element in soup.find_all(['script', 'style', 'nav', 'footer']):
            element.decompose()
        
        # Obtener texto y limpiar
        text = soup.get_text(separator=' ', strip=True)
        
        # Limpiar espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _clean_title(self, title: str) -> str:
        """Limpia el título del artículo"""
        if not title:
            return ""
        
        # Remover HTML si lo hay
        soup = BeautifulSoup(title, self.soup_parser)
        clean_title = soup.get_text(strip=True)
        
        return clean_title
    
    def _clean_excerpt(self, excerpt: str) -> str:
        """Limpia el excerpt del artículo"""
        if not excerpt:
            return ""
        
        soup = BeautifulSoup(excerpt, self.soup_parser)
        clean_excerpt = soup.get_text(strip=True)
        
        return clean_excerpt
    
    def _extract_images(self, html_content: str) -> List[Dict[str, str]]:
        """Extrae información de imágenes del contenido"""
        images = []
        
        if not html_content:
            return images
        
        soup = BeautifulSoup(html_content, self.soup_parser)
        
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            
            if src:
                images.append({
                    'src': src,
                    'alt': alt,
                    'title': img.get('title', '')
                })
        
        return images
    
    def _format_date(self, date_str: str) -> str:
        """Formatea la fecha del artículo"""
        if not date_str:
            return ""
        
        try:
            # Formato de fecha de WordPress: "2025-06-19T07:00:00"
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            logger.warning(f"Formato de fecha no reconocido: {date_str}")
            return date_str
    
    def _estimate_read_time(self, text_content: str, wpm: int = 200) -> int:
        """Estima tiempo de lectura en minutos"""
        if not text_content:
            return 1
        
        word_count = len(text_content.split())
        read_time = max(1, round(word_count / wpm))
        
        return read_time
    
    def create_email_content(self, processed_article: Dict[str, Any]) -> Dict[str, str]:
        """Crea contenido del email para enviar a Readwise"""
        title = processed_article['title']
        url = processed_article['url']
        date = processed_article['date']
        content = processed_article.get('content_html', '')
        excerpt = processed_article.get('excerpt', '')
        read_time = processed_article.get('estimated_read_time', 1)
        
        # Subject del email
        subject = f"EOM: {title}"
        
        # Determinar contenido del email
        if processed_article['access_type'] == 'open':
            email_body = self._create_full_article_email(
                title, url, date, content, read_time
            )
        else:
            email_body = self._create_preview_email(
                title, url, date, excerpt, read_time
            )
        
        return {
            'subject': subject,
            'body': email_body,
            'html': True
        }
    
    def _create_full_article_email(self, title: str, url: str, date: str, 
                                 content: str, read_time: int) -> str:
        """Crea email con artículo completo"""
        return f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto;">
            <header style="border-bottom: 2px solid #e0e0e0; padding-bottom: 20px; margin-bottom: 30px;">
                <h1 style="color: #333; margin-bottom: 10px;">{title}</h1>
                <p style="color: #666; margin: 0;">
                    <strong>Fecha:</strong> {date} | 
                    <strong>Tiempo de lectura:</strong> {read_time} min | 
                    <strong>Fuente:</strong> <a href="{url}">El Orden Mundial</a>
                </p>
            </header>
            
            <main>
                <div style="background-color: #f8f9fa; padding: 20px; border-left: 4px solid #007cba; margin-bottom: 20px;">
                    <h3 style="color: #007cba; margin-top: 0;">Vista previa</h3>
                    <p>{excerpt}</p>
                </div>
                
                <div style="text-align: center; padding: 20px; background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px;">
                    <p style="margin: 0; color: #856404;">
                        <strong>Artículo completo disponible con suscripción</strong><br>
                        <a href="{url}" style="color: #007cba; text-decoration: none; font-weight: bold;">Leer artículo completo →</a>
                    </p>
                </div>
            </main>
            
            <footer style="border-top: 1px solid #e0e0e0; padding-top: 20px; margin-top: 40px;">
                <p style="color: #888; font-size: 14px;">
                    Artículo original: <a href="{url}">{url}</a><br>
                    Enviado automáticamente por EOM Scraper
                </p>
            </footer>
        </body>
        </html>
        """El Orden Mundial</a>
                </p>
            </header>
            
            <main>
                {content}
            </main>
            
            <footer style="border-top: 1px solid #e0e0e0; padding-top: 20px; margin-top: 40px;">
                <p style="color: #888; font-size: 14px;">
                    Artículo original: <a href="{url}">{url}</a><br>
                    Enviado automáticamente por EOM Scraper
                </p>
            </footer>
        </body>
        </html>
        """
    
    def _create_preview_email(self, title: str, url: str, date: str, 
                            excerpt: str, read_time: int) -> str:
        """Crea email con preview del artículo premium"""
        return f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto;">
            <header style="border-bottom: 2px solid #e0e0e0; padding-bottom: 20px; margin-bottom: 30px;">
                <h1 style="color: #333; margin-bottom: 10px;">{title}</h1>
                <p style="color: #666; margin: 0;">
                    <strong>Fecha:</strong> {date} | 
                    <strong>Tipo:</strong> Artículo premium | 
                    <strong>Fuente:</strong> <a href="{url}">