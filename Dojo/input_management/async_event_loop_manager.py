"""
Centralized async event loop manager for the application.
Handles lazy initialization of the async loop in a background thread.
"""

import asyncio
import threading
from typing import Optional


class AsyncManager:
    """Singleton manager for the application's async event loop"""
    
    _instance: Optional['AsyncManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._started = False
    
    @classmethod
    def get_instance(cls) -> 'AsyncManager':
        """Get or create the singleton instance"""
        if cls._instance is None:
            print("Creating new AsyncManager instance")
            with cls._lock:
                print("Got lock")
                if cls._instance is None:
                    cls._instance = AsyncManager()
        return cls._instance
    
    def start(self) -> None:
        """Start the async event loop in a background thread (if not already started)"""

        if self._started:
            return
        
        with self._lock:
            if self._started:
                return
            print("AsyncManager: Initializing event loop in background thread")
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="AsyncManagerThread",
                daemon=True
            )
            self._thread.start()
            self._started = True
            print("AsyncManager: Started event loop in background thread")
    
    def _run_loop(self) -> None:
        """Run the event loop (called in background thread)"""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
    
    def stop(self) -> None:
        """Stop the async event loop and clean up"""
        if not self._started:
            return
        
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        self._started = False
        print("AsyncManager: Stopped event loop")
    
    def run_coroutine(self, coro) -> asyncio.Future:
        """
        Schedule a coroutine to run on the async loop.
        Returns a Future that can be used to get the result or wait for completion.
        
        Args:
            coro: The coroutine to run
            
        Returns:
            asyncio.Future: Future representing the coroutine's execution
        """
        if not self._started:
            self.start()
        
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    async def run_blocking_in_thread(self, func, *args, **kwargs):
        """
        Run a blocking function in a thread pool to avoid blocking the event loop.

        Args:
            func: The blocking function to run
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the blocking function
        """
        return await asyncio.to_thread(func, *args, **kwargs)
    
    def run_coroutine_sync(self, coro, timeout: Optional[float] = None):
        """
        Run a coroutine and block until it completes.
        
        Args:
            coro: The coroutine to run
            timeout: Optional timeout in seconds
            
        Returns:
            The result of the coroutine
        """
        future = self.run_coroutine(coro)
        return future.result(timeout=timeout)
