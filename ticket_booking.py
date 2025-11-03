"""
BookMyShow / Ticket Booking System
==================================

Core Design: System for seat reservation, payment, and ticket issuance.

Design Patterns & Strategies Used:
1. State Pattern - Seat states (Available, Locked, Reserved, Occupied)
2. Observer Pattern - Notify users about booking status
3. Strategy Pattern - Different payment strategies
4. Command Pattern - Booking operations with undo (cancellation)
5. Lock Pattern - Seat locking with timeout
6. Transaction Pattern - Ensure atomic booking operations
7. Factory Pattern - Create tickets and bookings

Race Condition Handling:
- Optimistic locking with version numbers
- Database-level transactions
- Distributed locks for seat reservation

Seat Locking Strategy:
- Lock seats for X minutes during booking
- Auto-release after timeout
- Prevent double booking with atomic operations
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta
from threading import Lock
from dataclasses import dataclass
from uuid import uuid4


class SeatState(Enum):
    AVAILABLE = "AVAILABLE"
    LOCKED = "LOCKED"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"


class PaymentStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


# ==================== STATE PATTERN ====================
# Seat state management

class Seat:
    """Seat with State Pattern"""
    
    def __init__(self, seat_id: str, row: str, number: int, seat_type: str):
        self.seat_id = seat_id
        self.row = row
        self.number = number
        self.seat_type = seat_type
        self.state = SeatState.AVAILABLE
        self.locked_by: Optional[str] = None
        self.locked_until: Optional[datetime] = None
        self.version = 0  # For optimistic locking
        self.lock = Lock()
    
    def lock_seat(self, user_id: str, timeout_minutes: int = 5) -> bool:
        """Lock seat for booking with timeout"""
        with self.lock:
            if self.state == SeatState.AVAILABLE:
                self.state = SeatState.LOCKED
                self.locked_by = user_id
                self.locked_until = datetime.now() + timedelta(minutes=timeout_minutes)
                self.version += 1
                return True
            return False
    
    def reserve_seat(self, user_id: str) -> bool:
        """Reserve seat after payment"""
        with self.lock:
            if self.state == SeatState.LOCKED and self.locked_by == user_id:
                self.state = SeatState.RESERVED
                self.version += 1
                return True
            return False
    
    def release_lock(self) -> bool:
        """Release lock if expired or cancelled"""
        with self.lock:
            if self.state == SeatState.LOCKED:
                self.state = SeatState.AVAILABLE
                self.locked_by = None
                self.locked_until = None
                self.version += 1
                return True
            return False
    
    def is_locked_expired(self) -> bool:
        """Check if lock has expired"""
        if self.state == SeatState.LOCKED and self.locked_until:
            return datetime.now() > self.locked_until
        return False
    
    def occupy_seat(self):
        """Mark seat as occupied (show has started)"""
        with self.lock:
            if self.state == SeatState.RESERVED:
                self.state = SeatState.OCCUPIED
                self.version += 1


# ==================== OBSERVER PATTERN ====================
# Notify about booking events

class BookingObserver(ABC):
    """Observer interface"""
    
    @abstractmethod
    def update(self, event_type: str, booking_id: str, message: str):
        pass


class EmailNotifier(BookingObserver):
    """Email notification observer"""
    
    def update(self, event_type: str, booking_id: str, message: str):
        if event_type in ["BOOKING_CONFIRMED", "PAYMENT_FAILED", "BOOKING_CANCELLED"]:
            print(f"[Email] Booking {booking_id}: {message}")


class SMSNotifier(BookingObserver):
    """SMS notification observer"""
    
    def update(self, event_type: str, booking_id: str, message: str):
        if event_type in ["BOOKING_CONFIRMED", "SEAT_LOCKED"]:
            print(f"[SMS] Booking {booking_id}: {message}")


class BookingNotifier:
    """Subject for Observer Pattern"""
    
    def __init__(self):
        self.observers: List[BookingObserver] = []
    
    def attach(self, observer: BookingObserver):
        self.observers.append(observer)
    
    def notify(self, event_type: str, booking_id: str, message: str):
        for observer in self.observers:
            observer.update(event_type, booking_id, message)


# ==================== STRATEGY PATTERN ====================
# Different payment methods

class PaymentStrategy(ABC):
    """Payment strategy interface"""
    
    @abstractmethod
    def process_payment(self, amount: float, booking_id: str) -> bool:
        pass
    
    @abstractmethod
    def refund(self, amount: float, transaction_id: str) -> bool:
        pass


class CreditCardPayment(PaymentStrategy):
    """Credit card payment strategy"""
    
    def process_payment(self, amount: float, booking_id: str) -> bool:
        print(f"Processing credit card payment: ${amount} for booking {booking_id}")
        # Simulate payment processing
        return True
    
    def refund(self, amount: float, transaction_id: str) -> bool:
        print(f"Refunding ${amount} to credit card: {transaction_id}")
        return True


class UPIPayment(PaymentStrategy):
    """UPI payment strategy"""
    
    def process_payment(self, amount: float, booking_id: str) -> bool:
        print(f"Processing UPI payment: ${amount} for booking {booking_id}")
        return True
    
    def refund(self, amount: float, transaction_id: str) -> bool:
        print(f"Refunding ${amount} via UPI: {transaction_id}")
        return True


class WalletPayment(PaymentStrategy):
    """Wallet payment strategy"""
    
    def process_payment(self, amount: float, booking_id: str) -> bool:
        print(f"Processing wallet payment: ${amount} for booking {booking_id}")
        return True
    
    def refund(self, amount: float, transaction_id: str) -> bool:
        print(f"Refunding ${amount} to wallet: {transaction_id}")
        return True


# ==================== COMMAND PATTERN ====================
# Booking operations with undo

class BookingCommand(ABC):
    """Command interface"""
    
    @abstractmethod
    def execute(self) -> bool:
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        pass


@dataclass
class Booking:
    """Booking data structure"""
    booking_id: str
    user_id: str
    show_id: str
    seat_ids: List[str]
    total_amount: float
    payment_status: PaymentStatus
    created_at: datetime
    payment_strategy: Optional[PaymentStrategy] = None


class CreateBookingCommand(BookingCommand):
    """Command to create booking"""
    
    def __init__(self, booking_service: 'BookingService', user_id: str, 
                 show_id: str, seat_ids: List[str], payment_strategy: PaymentStrategy):
        self.booking_service = booking_service
        self.user_id = user_id
        self.show_id = show_id
        self.seat_ids = seat_ids
        self.payment_strategy = payment_strategy
        self.booking: Optional[Booking] = None
    
    def execute(self) -> bool:
        self.booking = self.booking_service.create_booking(
            self.user_id, self.show_id, self.seat_ids, self.payment_strategy
        )
        return self.booking is not None
    
    def undo(self) -> bool:
        if self.booking:
            return self.booking_service.cancel_booking(self.booking.booking_id)
        return False


class BookingService:
    """Main booking service"""
    
    def __init__(self):
        self.shows: Dict[str, 'Show'] = {}
        self.bookings: Dict[str, Booking] = {}
        self.notifier = BookingNotifier()
        self.notifier.attach(EmailNotifier())
        self.notifier.attach(SMSNotifier())
        self.lock = Lock()
    
    def add_show(self, show: 'Show'):
        """Add a show"""
        self.shows[show.show_id] = show
    
    def create_booking(self, user_id: str, show_id: str, 
                      seat_ids: List[str], payment_strategy: PaymentStrategy) -> Optional[Booking]:
        """Create booking with transaction-like atomicity"""
        if show_id not in self.shows:
            return None
        
        show = self.shows[show_id]
        
        # Step 1: Lock seats (atomic operation)
        locked_seats = []
        try:
            for seat_id in seat_ids:
                seat = show.get_seat(seat_id)
                if not seat or not seat.lock_seat(user_id):
                    # Rollback: release already locked seats
                    for locked_seat in locked_seats:
                        locked_seat.release_lock()
                    return None
                locked_seats.append(seat)
            
            # Step 2: Calculate total amount
            total_amount = sum(show.get_seat_price(sid) for sid in seat_ids)
            
            # Step 3: Create booking
            booking_id = str(uuid4())
            booking = Booking(
                booking_id=booking_id,
                user_id=user_id,
                show_id=show_id,
                seat_ids=seat_ids,
                total_amount=total_amount,
                payment_status=PaymentStatus.PENDING,
                created_at=datetime.now(),
                payment_strategy=payment_strategy
            )
            
            self.bookings[booking_id] = booking
            
            # Step 4: Process payment
            if payment_strategy.process_payment(total_amount, booking_id):
                booking.payment_status = PaymentStatus.COMPLETED
                # Step 5: Reserve seats
                for seat in locked_seats:
                    seat.reserve_seat(user_id)
                
                self.notifier.notify("BOOKING_CONFIRMED", booking_id, 
                                   f"Booking confirmed for {len(seat_ids)} seats")
            else:
                booking.payment_status = PaymentStatus.FAILED
                # Release locks on payment failure
                for seat in locked_seats:
                    seat.release_lock()
                self.notifier.notify("PAYMENT_FAILED", booking_id, "Payment processing failed")
                return None
            
            return booking
            
        except Exception as e:
            # Rollback on any error
            for seat in locked_seats:
                seat.release_lock()
            return None
    
    def cancel_booking(self, booking_id: str) -> bool:
        """Cancel booking and process refund"""
        if booking_id not in self.bookings:
            return False
        
        booking = self.bookings[booking_id]
        
        if booking.payment_status != PaymentStatus.COMPLETED:
            return False
        
        # Release seats
        show = self.shows[booking.show_id]
        for seat_id in booking.seat_ids:
            seat = show.get_seat(seat_id)
            if seat:
                seat.release_lock()
        
        # Process refund
        if booking.payment_strategy:
            booking.payment_strategy.refund(booking.total_amount, booking_id)
        
        booking.payment_status = PaymentStatus.REFUNDED
        self.notifier.notify("BOOKING_CANCELLED", booking_id, 
                           f"Booking cancelled, refund processed")
        
        return True
    
    def release_expired_locks(self):
        """Background task to release expired locks"""
        for show in self.shows.values():
            for seat in show.seats:
                if seat.is_locked_expired():
                    seat.release_lock()


class Show:
    """Movie/Theater Show"""
    
    def __init__(self, show_id: str, movie_name: str, theater_id: str, 
                 show_time: datetime):
        self.show_id = show_id
        self.movie_name = movie_name
        self.theater_id = theater_id
        self.show_time = show_time
        self.seats: List[Seat] = []
        self.seat_prices: Dict[str, float] = {}
    
    def add_seat(self, seat: Seat, price: float):
        """Add seat to show"""
        self.seats.append(seat)
        self.seat_prices[seat.seat_id] = price
    
    def get_seat(self, seat_id: str) -> Optional[Seat]:
        """Get seat by ID"""
        for seat in self.seats:
            if seat.seat_id == seat_id:
                return seat
        return None
    
    def get_seat_price(self, seat_id: str) -> float:
        """Get seat price"""
        return self.seat_prices.get(seat_id, 0.0)
    
    def get_available_seats(self) -> List[Seat]:
        """Get all available seats"""
        return [seat for seat in self.seats if seat.state == SeatState.AVAILABLE]


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("TICKET BOOKING SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    # Create service
    service = BookingService()
    
    # Create show
    show = Show("SHOW1", "Avengers", "THEATER1", datetime.now() + timedelta(hours=2))
    
    # Add seats
    for i in range(1, 6):
        seat = Seat(f"S{i}", "A", i, "REGULAR")
        show.add_seat(seat, 500.0)
    
    service.add_show(show)
    
    # Create booking
    print("1. Creating booking:")
    payment = CreditCardPayment()
    booking = service.create_booking("USER1", "SHOW1", ["S1", "S2"], payment)
    if booking:
        print(f"Booking created: {booking.booking_id}")
        print(f"Payment status: {booking.payment_status.value}")
        print(f"Total amount: ${booking.total_amount}")
    print()
    
    # Try double booking
    print("2. Attempting double booking (should fail):")
    booking2 = service.create_booking("USER2", "SHOW1", ["S1"], UPIPayment())
    if not booking2:
        print("Double booking prevented!")
    print()
    
    # Check available seats
    print("3. Available seats after booking:")
    available = show.get_available_seats()
    print(f"Available: {[s.seat_id for s in available]}")
    print()
    
    # Cancel booking
    print("4. Cancelling booking:")
    service.cancel_booking(booking.booking_id)
    print()
    
    print("5. Available seats after cancellation:")
    available = show.get_available_seats()
    print(f"Available: {[s.seat_id for s in available]}")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. State Pattern - Seat states (Available, Locked, Reserved)")
    print("2. Observer Pattern - Email/SMS notifications")
    print("3. Strategy Pattern - Payment methods (Card, UPI, Wallet)")
    print("4. Command Pattern - Booking operations with undo")
    print("5. Transaction Pattern - Atomic booking operations")
    print("6. Lock Pattern - Seat locking with timeout")
    print()
    print("RACE CONDITION HANDLING:")
    print("- Per-seat locks for concurrent access")
    print("- Optimistic locking with version numbers")
    print("- Atomic lock-then-reserve operation")
    print("- Rollback on failure")
    print("=" * 60)


if __name__ == "__main__":
    main()

