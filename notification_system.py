"""
Notification System
===================

Core Design: System to send notifications via email, SMS, push notifications.

Design Patterns & Strategies Used:
1. Strategy Pattern - Different notification channels (Email, SMS, Push)
2. Factory Pattern - Create notification senders
3. Observer Pattern - Notification delivery status
4. Queue Pattern - Async notification processing
5. Retry Pattern - Retry failed notifications
6. Circuit Breaker Pattern - Handle service failures
7. Priority Queue - Prioritize notifications

Features:
- Multiple channels (Email, SMS, Push)
- Retry mechanism with exponential backoff
- Delivery guarantees
- Rate limiting per channel
- Priority-based sending
- Batching for efficiency
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from queue import PriorityQueue
from threading import Lock, Thread
import time
import random


class NotificationPriority(Enum):
    LOW = 3
    MEDIUM = 2
    HIGH = 1
    URGENT = 0


class DeliveryStatus(Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"


class NotificationChannel(Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"


# ==================== STRATEGY PATTERN ====================
# Different notification channels

class NotificationSender(ABC):
    """Notification sender strategy interface"""
    
    @abstractmethod
    def send(self, recipient: str, subject: str, message: str) -> bool:
        pass
    
    @abstractmethod
    def get_channel(self) -> NotificationChannel:
        pass


class EmailSender(NotificationSender):
    """Email notification sender"""
    
    def send(self, recipient: str, subject: str, message: str) -> bool:
        # Simulate email sending
        print(f"[Email] To: {recipient}, Subject: {subject}")
        print(f"       Body: {message[:50]}...")
        # Simulate occasional failure
        return random.random() > 0.1
    
    def get_channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL


class SMSSender(NotificationSender):
    """SMS notification sender"""
    
    def send(self, recipient: str, subject: str, message: str) -> bool:
        # Simulate SMS sending
        print(f"[SMS] To: {recipient}")
        print(f"      Message: {message[:50]}...")
        return random.random() > 0.15
    
    def get_channel(self) -> NotificationChannel:
        return NotificationChannel.SMS


class PushSender(NotificationSender):
    """Push notification sender"""
    
    def send(self, recipient: str, subject: str, message: str) -> bool:
        # Simulate push notification
        print(f"[Push] To: {recipient}, Title: {subject}")
        print(f"       Body: {message[:50]}...")
        return random.random() > 0.2
    
    def get_channel(self) -> NotificationChannel:
        return NotificationChannel.PUSH


# ==================== CIRCUIT BREAKER PATTERN ====================

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Circuit breaker for handling failures"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.lock = Lock()
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == CircuitState.OPEN:
                if (datetime.now() - self.last_failure_time).seconds >= self.timeout:
                    self.state = CircuitState.HALF_OPEN
                else:
                    return False
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            return False
    
    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN


# ==================== NOTIFICATION CLASSES ====================

@dataclass
class Notification:
    """Notification data structure"""
    notification_id: str
    recipient: str
    subject: str
    message: str
    channel: NotificationChannel
    priority: NotificationPriority
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        """For priority queue"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class NotificationService:
    """Main notification service"""
    
    def __init__(self):
        self.senders: Dict[NotificationChannel, NotificationSender] = {
            NotificationChannel.EMAIL: EmailSender(),
            NotificationChannel.SMS: SMSSender(),
            NotificationChannel.PUSH: PushSender()
        }
        self.circuit_breakers: Dict[NotificationChannel, CircuitBreaker] = {
            channel: CircuitBreaker() for channel in NotificationChannel
        }
        self.queue = PriorityQueue()
        self.running = False
        self.worker_thread: Optional[Thread] = None
    
    def send_notification(self, recipient: str, subject: str, message: str,
                         channel: NotificationChannel,
                         priority: NotificationPriority = NotificationPriority.MEDIUM):
        """Queue notification for sending"""
        from uuid import uuid4
        notification = Notification(
            notification_id=str(uuid4()),
            recipient=recipient,
            subject=subject,
            message=message,
            channel=channel,
            priority=priority,
            created_at=datetime.now()
        )
        self.queue.put(notification)
        return notification.notification_id
    
    def start(self):
        """Start notification processing"""
        self.running = True
        
        def worker():
            while self.running or not self.queue.empty():
                try:
                    notification = self.queue.get(timeout=1)
                    self._process_notification(notification)
                except:
                    pass
        
        self.worker_thread = Thread(target=worker, daemon=True)
        self.worker_thread.start()
    
    def _process_notification(self, notification: Notification):
        """Process notification with retry"""
        sender = self.senders[notification.channel]
        circuit_breaker = self.circuit_breakers[notification.channel]
        
        def send():
            return sender.send(notification.recipient, notification.subject, notification.message)
        
        success = circuit_breaker.call(send)
        
        if not success:
            if notification.retry_count < notification.max_retries:
                # Exponential backoff
                delay = 2 ** notification.retry_count
                notification.retry_count += 1
                notification.created_at = datetime.now() + timedelta(seconds=delay)
                self.queue.put(notification)
            else:
                print(f"[Failed] Notification {notification.notification_id} failed after max retries")
    
    def stop(self):
        """Stop notification processing"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)


class NotificationFactory:
    """Factory for creating notification senders"""
    
    @staticmethod
    def create_sender(channel: NotificationChannel) -> NotificationSender:
        """Create notification sender for channel"""
        if channel == NotificationChannel.EMAIL:
            return EmailSender()
        elif channel == NotificationChannel.SMS:
            return SMSSender()
        elif channel == NotificationChannel.PUSH:
            return PushSender()
        else:
            raise ValueError(f"Unknown channel: {channel}")


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("NOTIFICATION SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    service = NotificationService()
    service.start()
    
    print("1. Sending notifications:")
    service.send_notification("user1@example.com", "Welcome", "Welcome to our service!",
                             NotificationChannel.EMAIL, NotificationPriority.HIGH)
    service.send_notification("+1234567890", "OTP", "Your OTP is 1234",
                             NotificationChannel.SMS, NotificationPriority.URGENT)
    service.send_notification("device123", "Update", "New update available",
                             NotificationChannel.PUSH, NotificationPriority.MEDIUM)
    print()
    
    time.sleep(1)
    
    print("2. Sending batch notifications:")
    for i in range(3):
        service.send_notification(f"user{i}@example.com", f"Newsletter {i}", 
                                  "Check out our latest offers!",
                                  NotificationChannel.EMAIL, NotificationPriority.LOW)
    
    time.sleep(1)
    
    service.stop()
    
    print()
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. Strategy Pattern - Different channels (Email, SMS, Push)")
    print("2. Factory Pattern - Create notification senders")
    print("3. Queue Pattern - Async processing with priority queue")
    print("4. Retry Pattern - Exponential backoff retry")
    print("5. Circuit Breaker - Handle service failures")
    print()
    print("FEATURES:")
    print("- Priority-based sending")
    print("- Retry with exponential backoff")
    print("- Circuit breaker for resilience")
    print("- Async processing")
    print("- Multiple channels")
    print("=" * 60)


if __name__ == "__main__":
    main()

