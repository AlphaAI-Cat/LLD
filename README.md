# Low-Level Design Systems

This repository contains implementations of 19 common system design problems, each in a separate Python file with comprehensive design patterns and strategies.

## Systems Overview

### 1. Cache System (LRU/LFU Cache)
**File:** `cache_system.py`
- **Patterns:** Strategy, Template Method, Decorator, Factory
- **Features:** O(1) get/put operations, LRU/LFU eviction, thread-safe, cache stampede prevention

### 2. BookMyShow / Ticket Booking
**File:** `ticket_booking.py`
- **Patterns:** State, Observer, Strategy, Command, Transaction
- **Features:** Seat reservation, payment, double-booking prevention, seat locking with timeout

### 3. Elevator System
**File:** `elevator_system.py`
- **Patterns:** State, Strategy, Command, Observer, Singleton
- **Features:** Multiple elevators, scheduling algorithms (SCAN, LOOK, FCFS), concurrent requests

### 4. Logger System
**File:** `logger_system.py`
- **Patterns:** Strategy, Chain of Responsibility, Observer, Singleton, Factory, Decorator
- **Features:** Multiple log levels, appenders (Console, File, DB), log rotation, async logging

### 5. Rate Limiter
**File:** `rate_limiter.py`
- **Patterns:** Strategy, Factory, Decorator
- **Features:** Token Bucket, Leaky Bucket, Sliding Window, Fixed Window algorithms

### 6. Online Food Ordering
**File:** `food_ordering.py`
- **Patterns:** State, Observer, Strategy, Factory, Command
- **Features:** Order management, delivery assignment, real-time tracking, restaurant search

### 7. Notification System
**File:** `notification_system.py`
- **Patterns:** Strategy, Factory, Observer, Queue, Retry, Circuit Breaker
- **Features:** Multiple channels (Email, SMS, Push), retry with backoff, priority queue

### 8. Splitwise / Expense Sharing
**File:** `splitwise.py`
- **Patterns:** Graph Algorithm, Strategy, Observer, Factory
- **Features:** Group expenses, balance tracking, settlement optimization

### 9. URL Shortener
**File:** `url_shortener.py`
- **Patterns:** Strategy, Singleton, Factory, Cache, Observer
- **Features:** Base62 encoding, hash-based, analytics, LRU cache

### 10. File Storage / Dropbox System
**File:** `file_storage.py`
- **Patterns:** Strategy, Version Control, Factory, Observer, Command
- **Features:** File versioning, conflict resolution, delta sync, multiple storage backends

### 11. Ride-Sharing System
**File:** `ride_sharing.py`
- **Patterns:** Observer, Strategy, State, Factory, Command
- **Features:** Driver matching, surge pricing, real-time tracking, ETA calculation

### 12. ATM System
**File:** `atm_system.py`
- **Patterns:** State, Command, Strategy, Chain of Responsibility, Observer
- **Features:** Transaction processing, authorization chain, concurrent handling, rollback

### 13. Library Management System
**File:** `library_management.py`
- **Patterns:** State, Observer, Factory, Strategy, Command
- **Features:** Book catalog, borrowing, reservations, fine calculation, search

### 14. Chat/Messaging System
**File:** `chat_messaging.py`
- **Patterns:** Observer, Strategy, State, Factory, Publisher-Subscriber, Queue
- **Features:** One-on-one and group chats, delivery status, real-time updates

### 15. E-Commerce Cart System
**File:** `ecommerce_cart.py`
- **Patterns:** State, Strategy, Observer, Factory, Command
- **Features:** Cart management, pricing strategies, discounts, inventory, checkout

### 16. Notification Scheduler / Job Queue
**File:** `job_queue.py`
- **Patterns:** Priority Queue, Strategy, Observer, Factory, Thread Pool
- **Features:** Priority scheduling, retry mechanism, scheduled/recurring jobs

### 17. Document Collaboration
**File:** `document_collaboration.py`
- **Patterns:** Operational Transform, Observer, State, Command, Strategy, Event Sourcing
- **Features:** Real-time editing, conflict resolution, cursor tracking, permissions

### 18. Payment Gateway
**File:** `payment_gateway.py`
- **Patterns:** Strategy, State, Chain of Responsibility, Factory, Observer, Circuit Breaker
- **Features:** Multiple payment methods, validation chain, refunds, fraud detection

### 19. Hotel Management System
**File:** `hotel_management.py`
- **Patterns:** State, Strategy, Observer, Factory, Command
- **Features:** Room booking, check-in/out, pricing strategies, guest management

## Common Design Patterns Used

1. **Strategy Pattern** - Different algorithms/behaviors (pricing, matching, encoding)
2. **Observer Pattern** - Event notifications and updates
3. **State Pattern** - Object state management
4. **Factory Pattern** - Object creation
5. **Command Pattern** - Encapsulate operations with undo
6. **Singleton Pattern** - Single instance services
7. **Template Method** - Define algorithm skeleton
8. **Decorator Pattern** - Add functionality dynamically
9. **Chain of Responsibility** - Request handling chain
10. **Publisher-Subscriber** - Message broadcasting

## Running the Systems

Each file can be run independently:
```bash
python cache_system.py
python ticket_booking.py
# ... etc
```

Each system includes:
- Comprehensive documentation
- Design pattern explanations
- Demonstration code
- Feature descriptions

## Notes

- All systems are designed for educational purposes
- Real-world implementations would require additional features like:
  - Database persistence
  - Distributed systems support
  - Production-grade error handling
  - Security measures
  - Performance optimizations

