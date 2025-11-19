"""
Graceful shutdown handling for long-running processes.

Handles SIGTERM/SIGINT signals to allow in-flight operations to complete
before shutting down.
"""

import signal
import logging
import threading
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """
    Manages graceful shutdown for long-running processes.
    
    Allows in-flight operations to complete before shutting down.
    """
    
    def __init__(self, shutdown_callback: Optional[Callable] = None):
        """
        Initialize graceful shutdown handler.
        
        Args:
            shutdown_callback: Optional callback to run on shutdown
        """
        self.shutdown_requested = False
        self.shutdown_callback = shutdown_callback
        self._lock = threading.Lock()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for SIGTERM and SIGINT"""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        logger.info("Graceful shutdown handlers registered")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        signal_name = signal.Signals(signum).name
        logger.warning(f"Received {signal_name} signal, initiating graceful shutdown...")
        
        with self._lock:
            if not self.shutdown_requested:
                self.shutdown_requested = True
                if self.shutdown_callback:
                    try:
                        self.shutdown_callback()
                    except Exception as e:
                        logger.error(f"Error in shutdown callback: {str(e)}")
            else:
                logger.warning("Shutdown already requested, forcing exit")
                import sys
                sys.exit(1)
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested"""
        with self._lock:
            return self.shutdown_requested
    
    def wait_for_shutdown(self, timeout: Optional[float] = None):
        """
        Wait for shutdown signal.
        
        Args:
            timeout: Maximum time to wait (None = wait indefinitely)
        """
        import time
        start_time = time.time()
        
        while not self.is_shutdown_requested():
            if timeout and (time.time() - start_time) >= timeout:
                break
            time.sleep(0.1)


# Global instance
_shutdown_handler: Optional[GracefulShutdown] = None


def init_graceful_shutdown(shutdown_callback: Optional[Callable] = None) -> GracefulShutdown:
    """
    Initialize global graceful shutdown handler.
    
    Args:
        shutdown_callback: Optional callback to run on shutdown
        
    Returns:
        GracefulShutdown instance
    """
    global _shutdown_handler
    _shutdown_handler = GracefulShutdown(shutdown_callback)
    return _shutdown_handler


def get_shutdown_handler() -> Optional[GracefulShutdown]:
    """Get global shutdown handler"""
    return _shutdown_handler


def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested"""
    handler = get_shutdown_handler()
    return handler.is_shutdown_requested() if handler else False

