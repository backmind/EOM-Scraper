"""
Gestor de estado para tracking de artículos procesados
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ScraperState:
    """Estado del scraper"""
    last_check_timestamp: str
    processed_post_ids: Set[int]
    total_posts_processed: int
    last_successful_run: str
    errors_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización"""
        return {
            'last_check_timestamp': self.last_check_timestamp,
            'processed_post_ids': list(self.processed_post_ids),
            'total_posts_processed': self.total_posts_processed,
            'last_successful_run': self.last_successful_run,
            'errors_count': self.errors_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScraperState':
        """Crea instancia desde diccionario"""
        return cls(
            last_check_timestamp=data.get('last_check_timestamp', ''),
            processed_post_ids=set(data.get('processed_post_ids', [])),
            total_posts_processed=data.get('total_posts_processed', 0),
            last_successful_run=data.get('last_successful_run', ''),
            errors_count=data.get('errors_count', 0)
        )

class StateManager:
    """Gestor de estado persistente"""
    
    def __init__(self, state_file: str):
        self.state_file = Path(state_file)
        self.state: Optional[ScraperState] = None
    
    def load_state(self) -> ScraperState:
        """Carga el estado desde archivo o crea uno nuevo"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.state = ScraperState.from_dict(data)
                logger.info(f"Estado cargado: {len(self.state.processed_post_ids)} posts procesados")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error cargando estado: {e}. Creando estado nuevo.")
                self.state = self._create_initial_state()
        else:
            logger.info("No existe archivo de estado. Creando estado inicial.")
            self.state = self._create_initial_state()
        
        return self.state
    
    def save_state(self) -> bool:
        """Guarda el estado actual"""
        if not self.state:
            logger.error("No hay estado para guardar")
            return False
        
        try:
            # Crear directorio si no existe
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Estado guardado en {self.state_file}")
            return True
        except Exception as e:
            logger.error(f"Error guardando estado: {e}")
            return False
    
    def _create_initial_state(self) -> ScraperState:
        """Crea estado inicial"""
        now = datetime.now(timezone.utc).isoformat()
        return ScraperState(
            last_check_timestamp=now,
            processed_post_ids=set(),
            total_posts_processed=0,
            last_successful_run='',
            errors_count=0
        )
    
    def update_last_check(self, timestamp: datetime) -> None:
        """Actualiza timestamp de última verificación"""
        if self.state:
            self.state.last_check_timestamp = timestamp.isoformat()
            logger.debug(f"Timestamp actualizado: {self.state.last_check_timestamp}")
    
    def mark_post_processed(self, post_id: int) -> None:
        """Marca un post como procesado"""
        if self.state:
            if post_id not in self.state.processed_post_ids:
                self.state.processed_post_ids.add(post_id)
                self.state.total_posts_processed += 1
                logger.debug(f"Post {post_id} marcado como procesado")
    
    def is_post_processed(self, post_id: int) -> bool:
        """Verifica si un post ya fue procesado"""
        if self.state:
            return post_id in self.state.processed_post_ids
        return False
    
    def mark_successful_run(self) -> None:
        """Marca una ejecución exitosa"""
        if self.state:
            self.state.last_successful_run = datetime.now(timezone.utc).isoformat()
            logger.debug("Ejecución exitosa marcada")
    
    def increment_error_count(self) -> None:
        """Incrementa contador de errores"""
        if self.state:
            self.state.errors_count += 1
    
    def get_last_check_datetime(self) -> datetime:
        """Obtiene la fecha de última verificación como datetime"""
        if self.state and self.state.last_check_timestamp:
            try:
                return datetime.fromisoformat(self.state.last_check_timestamp.replace('Z', '+00:00'))
            except ValueError:
                logger.warning("Formato de timestamp inválido, usando datetime actual")
        
        # Si no hay timestamp válido, usar hace 1 hora
        from datetime import timedelta
        return datetime.now(timezone.utc) - timedelta(hours=1)
    
    def cleanup_old_processed_ids(self, keep_recent: int = 1000) -> None:
        """Limpia IDs de posts procesados antiguos para evitar crecimiento excesivo"""
        if self.state and len(self.state.processed_post_ids) > keep_recent * 1.5:
            # Mantener solo los más recientes (asumiendo que IDs mayores = más recientes)
            sorted_ids = sorted(self.state.processed_post_ids, reverse=True)
            self.state.processed_post_ids = set(sorted_ids[:keep_recent])
            logger.info(f"Limpieza de estado: mantenidos {keep_recent} posts recientes")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del estado actual"""
        if not self.state:
            return {}
        
        return {
            'total_processed': self.state.total_posts_processed,
            'unique_posts_tracked': len(self.state.processed_post_ids),
            'last_check': self.state.last_check_timestamp,
            'last_successful_run': self.state.last_successful_run,
            'errors_count': self.state.errors_count
        }