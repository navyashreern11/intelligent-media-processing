import queue
import threading
from app.logging_config import logger

class JobQueueManager:
    def __init__(self):
        self.queue = queue.Queue()
        self.worker_thread = None
        self.should_stop = False
        self._lock = threading.Lock()

    def start(self):
        """Starts the background worker thread if not already running."""
        with self._lock:
            # Drain queue to clear any leftover tasks or sentinels from previous lifecycles
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except (queue.Empty, ValueError):
                    break

            if self.worker_thread is None or not self.worker_thread.is_alive():
                self.should_stop = False
                self.worker_thread = threading.Thread(
                    target=self._worker_loop,
                    daemon=True,
                    name="BackgroundWorker"
                )
                self.worker_thread.start()
                logger.info("Background worker thread started successfully")

    def stop(self):
        """Signals the background worker thread to stop and waits for it."""
        with self._lock:
            if self.worker_thread is not None and self.worker_thread.is_alive():
                logger.info("Stopping background worker thread...")
                self.should_stop = True
                # Put a sentinel value (None) to wake up and terminate the queue reader
                self.queue.put(None)
                self.worker_thread.join(timeout=5.0)
                logger.info("Background worker thread stopped")

    def enqueue(self, job_id: str):
        """Adds a processing job ID to the queue."""
        self.queue.put(job_id)
        logger.info(f"Enqueued job in-memory", extra={"processing_id": job_id})

    def get_status(self) -> str:
        """Returns the state of the worker thread."""
        with self._lock:
            if self.worker_thread and self.worker_thread.is_alive():
                return "running"
            return "stopped"

    def _worker_loop(self):
        logger.info("Background worker loop started")
        try:
            # Deferred import to prevent circular import loops with processor
            from app.services.processor import process_job
            logger.info("Successfully imported process_job in worker thread")
        except Exception as e:
            logger.error(f"Failed to import process_job in worker thread: {e}", exc_info=True)
            return

        while not self.should_stop:
            try:
                job_id = self.queue.get()
                if job_id is None:
                    logger.info("Worker thread received shutdown sentinel")
                    self.queue.task_done()
                    break

                logger.info(f"Worker thread starting job processing", extra={"processing_id": job_id})
                process_job(job_id)
                self.queue.task_done()
            except Exception as e:
                logger.error(
                    f"Fatal error in worker thread processing cycle: {e}",
                    exc_info=True,
                    extra={"processing_id": job_id if 'job_id' in locals() else "-"}
                )
                # Keep thread alive, but mark task completed to prevent deadlock
                try:
                    self.queue.task_done()
                except ValueError:
                    pass
        logger.info("Background worker loop exited")

# Singleton instance
job_queue_manager = JobQueueManager()
