import time
from typing import Callable, Any
from logger import log_structured

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED (ok), OPEN (broken), HALF-OPEN (testing)

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF-OPEN"
                log_structured("CIRCUIT_CHANGE", "CircuitBreaker", state="HALF-OPEN")
            else:
                log_structured("CIRCUIT_BLOCKED", "CircuitBreaker", state="OPEN")
                raise Exception("Circuit is OPEN. Fast failing.")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF-OPEN":
                self.state = "CLOSED"
                self.failures = 0
                log_structured("CIRCUIT_CHANGE", "CircuitBreaker", state="CLOSED")
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            log_structured("CIRCUIT_FAILURE", "CircuitBreaker", error=str(e), failures=self.failures)
            
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
                log_structured("CIRCUIT_CHANGE", "CircuitBreaker", state="OPEN")
            raise e
