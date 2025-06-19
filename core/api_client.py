"""
Cliente para WordPress REST API de El Orden Mundial
"""
import requests
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from config.settings import EOMConfig

logger = logging.getLogger(__name__)

class EOMAPIClient:
    """Cliente para interactuar con la API REST de El Orden Mundial"""
    
    def __init__(self, config: EOMConfig, request_delay: float = 1.0):
        self.config = config
        self.session = requests.Session()
        self.request_delay = request_delay
        self.authenticated = False
        
        # Headers por defecto
        self.session.headers.update({
            'User-Agent': 'EOM-Scraper/1.0',
            'Accept': 'application/json'
        })
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Realiza una petición con rate limiting y manejo de errores"""
        url = f"{self.config.base_url}{self.config.api_base}{endpoint}"
        
        try:
            logger.debug(f"Realizando petición: {url} con params: {params}")
            response = self.session.get(url, params=params, timeout=30)
            
            # Rate limiting
            time.sleep(self.request_delay)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error en petición: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición HTTP: {e}")
            return None
    
    def authenticate(self) -> bool:
        """Autenticación para contenido premium (implementación futura)"""
        if not self.config.username or not self.config.password:
            logger.warning("No hay credenciales para autenticación")
            return False
        
        # TODO: Implementar autenticación MemberPress
        # Por ahora, solo marcar como no autenticado
        self.authenticated = False
        logger.info("Autenticación deshabilitada en esta versión")
        return False
    
    def get_posts_since(self, since_datetime: datetime, max_posts: int = 100) -> List[Dict]:
        """Obtiene posts publicados desde una fecha específica"""
        since_iso = since_datetime.isoformat()
        
        params = {
            'after': since_iso,
            'per_page': min(max_posts, self.config.max_per_page),
            'orderby': 'date',
            'order': 'desc',
            'status': 'publish'
        }
        
        logger.info(f"Buscando posts desde: {since_iso}")
        
        posts = self._make_request('/posts', params)
        if posts is None:
            return []
        
        logger.info(f"Encontrados {len(posts)} posts nuevos")
        return posts
    
    def get_all_recent_posts(self, limit: int = 50) -> List[Dict]:
        """Obtiene los posts más recientes (para inicialización)"""
        all_posts = []
        page = 1
        
        while len(all_posts) < limit:
            remaining = limit - len(all_posts)
            per_page = min(remaining, self.config.max_per_page)
            
            params = {
                'per_page': per_page,
                'page': page,
                'orderby': 'date',
                'order': 'desc',
                'status': 'publish'
            }
            
            posts = self._make_request('/posts', params)
            if not posts:
                break
            
            all_posts.extend(posts)
            page += 1
            
            # Si obtenemos menos posts de los solicitados, no hay más páginas
            if len(posts) < per_page:
                break
        
        logger.info(f"Obtenidos {len(all_posts)} posts recientes")
        return all_posts[:limit]
    
    def classify_post_access(self, post_data: Dict) -> str:
        """Clasifica si un post es abierto o premium"""
        content = post_data.get('content', {}).get('rendered', '')
        
        if 'mepr-unauthorized-excerpt' in content:
            return 'premium'
        else:
            return 'open'
    
    def extract_post_metadata(self, post_data: Dict) -> Dict[str, Any]:
        """Extrae metadatos útiles de un post"""
        return {
            'id': post_data.get('id'),
            'title': post_data.get('title', {}).get('rendered', ''),
            'excerpt': post_data.get('excerpt', {}).get('rendered', ''),
            'url': post_data.get('link', ''),
            'date': post_data.get('date', ''),
            'modified': post_data.get('modified', ''),
            'author_id': post_data.get('author'),
            'categories': post_data.get('categories', []),
            'tags': post_data.get('tags', []),
            'places': post_data.get('lugar', []),  # Taxonomía personalizada
            'coauthors': post_data.get('coauthors', []),
            'content_raw': post_data.get('content', {}).get('rendered', ''),
            'access_type': self.classify_post_access(post_data)
        }
    
    def get_post_by_id(self, post_id: int) -> Optional[Dict]:
        """Obtiene un post específico por ID"""
        return self._make_request(f'/posts/{post_id}')
    
    def discover_api_endpoints(self) -> Optional[Dict]:
        """Descubre endpoints disponibles en la API"""
        return self._make_request('')