"""
Hotel Management System
=======================

Core Design: System for hotel room booking, check-in/check-out, and billing.

Design Patterns & Strategies Used:
1. State Pattern - Room states (Available, Occupied, Maintenance, Reserved)
2. Strategy Pattern - Different pricing strategies (Seasonal, Dynamic)
3. Observer Pattern - Notifications for bookings and room status
4. Factory Pattern - Create bookings and rooms
5. Command Pattern - Booking operations
6. Template Method - Booking workflow

Features:
- Room booking
- Check-in/check-out
- Room management
- Pricing strategies
- Guest management
- Billing
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass
from uuid import uuid4


class RoomState(Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    RESERVED = "RESERVED"
    MAINTENANCE = "MAINTENANCE"


class BookingStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLED = "CANCELLED"


class RoomType(Enum):
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    SUITE = "SUITE"
    DELUXE = "DELUXE"


@dataclass
class Room:
    """Hotel room"""
    room_number: str
    room_type: RoomType
    floor: int
    base_price: float
    state: RoomState
    max_occupancy: int
    
    def is_available(self) -> bool:
        """Check if room is available"""
        return self.state == RoomState.AVAILABLE


@dataclass
class Guest:
    """Hotel guest"""
    guest_id: str
    name: str
    email: str
    phone: str
    check_in_date: Optional[datetime] = None
    check_out_date: Optional[datetime] = None
    room_number: Optional[str] = None


@dataclass
class Booking:
    """Booking entity"""
    booking_id: str
    guest_id: str
    room_number: str
    check_in: datetime
    check_out: datetime
    status: BookingStatus
    total_amount: float
    created_at: datetime
    
    def get_nights(self) -> int:
        """Get number of nights"""
        return (self.check_out - self.check_in).days


class PricingStrategy(ABC):
    """Pricing strategy interface"""
    
    @abstractmethod
    def calculate_price(self, room: Room, check_in: datetime, check_out: datetime) -> float:
        pass


class StandardPricingStrategy(PricingStrategy):
    """Standard pricing"""
    
    def calculate_price(self, room: Room, check_in: datetime, check_out: datetime) -> float:
        nights = (check_out - check_in).days
        return room.base_price * nights


class SeasonalPricingStrategy(PricingStrategy):
    """Seasonal pricing with peak season multipliers"""
    
    def __init__(self, peak_multiplier: float = 1.5):
        self.peak_multiplier = peak_multiplier
    
    def calculate_price(self, room: Room, check_in: datetime, check_out: datetime) -> float:
        base_price = StandardPricingStrategy().calculate_price(room, check_in, check_out)
        
        # Check if peak season (simplified - summer months)
        if check_in.month in [6, 7, 8]:
            return base_price * self.peak_multiplier
        
        return base_price


class DynamicPricingStrategy(PricingStrategy):
    """Dynamic pricing based on occupancy"""
    
    def __init__(self, occupancy_threshold: float = 0.7):
        self.occupancy_threshold = occupancy_threshold
    
    def calculate_price(self, room: Room, check_in: datetime, check_out: datetime) -> float:
        base_price = StandardPricingStrategy().calculate_price(room, check_in, check_out)
        
        # In real system, would check actual occupancy rate
        # Simplified - assume high occupancy
        occupancy_rate = 0.8
        
        if occupancy_rate > self.occupancy_threshold:
            multiplier = 1 + (occupancy_rate - self.occupancy_threshold) * 2
            return base_price * multiplier
        
        return base_price


class HotelObserver(ABC):
    """Observer for hotel events"""
    
    @abstractmethod
    def on_booking_confirmed(self, booking: Booking):
        pass
    
    @abstractmethod
    def on_check_in(self, guest: Guest, room: Room):
        pass
    
    @abstractmethod
    def on_check_out(self, guest: Guest, amount: float):
        pass


class EmailNotifier(HotelObserver):
    """Email notification observer"""
    
    def on_booking_confirmed(self, booking: Booking):
        print(f"[Email] Booking {booking.booking_id} confirmed")
    
    def on_check_in(self, guest: Guest, room: Room):
        print(f"[Email] {guest.name} checked in to room {room.room_number}")
    
    def on_check_out(self, guest: Guest, amount: float):
        print(f"[Email] {guest.name} checked out. Amount: ${amount:.2f}")


class HotelService:
    """Hotel management service"""
    
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.guests: Dict[str, Guest] = {}
        self.bookings: Dict[str, Booking] = {}
        self.pricing_strategy: PricingStrategy = StandardPricingStrategy()
        self.observers: List[HotelObserver] = []
    
    def add_room(self, room: Room):
        """Add room to hotel"""
        self.rooms[room.room_number] = room
    
    def set_pricing_strategy(self, strategy: PricingStrategy):
        """Set pricing strategy"""
        self.pricing_strategy = strategy
    
    def add_observer(self, observer: HotelObserver):
        """Add observer"""
        self.observers.append(observer)
    
    def register_guest(self, name: str, email: str, phone: str) -> str:
        """Register guest"""
        guest_id = str(uuid4())
        guest = Guest(guest_id, name, email, phone)
        self.guests[guest_id] = guest
        return guest_id
    
    def search_available_rooms(self, check_in: datetime, check_out: datetime,
                               room_type: Optional[RoomType] = None) -> List[Room]:
        """Search available rooms"""
        available = []
        
        for room in self.rooms.values():
            if room.state != RoomState.AVAILABLE:
                continue
            
            if room_type and room.room_type != room_type:
                continue
            
            # Check if room is booked during period
            is_booked = False
            for booking in self.bookings.values():
                if (booking.room_number == room.room_number and
                    booking.status != BookingStatus.CANCELLED and
                    booking.status != BookingStatus.CHECKED_OUT and
                    not (check_out <= booking.check_in or check_in >= booking.check_out)):
                    is_booked = True
                    break
            
            if not is_booked:
                available.append(room)
        
        return available
    
    def book_room(self, guest_id: str, room_number: str,
                 check_in: datetime, check_out: datetime) -> Optional[str]:
        """Book room"""
        if room_number not in self.rooms or guest_id not in self.guests:
            return None
        
        room = self.rooms[room_number]
        
        # Check availability
        if not room.is_available():
            return None
        
        # Calculate price
        total_amount = self.pricing_strategy.calculate_price(room, check_in, check_out)
        
        # Create booking
        booking_id = str(uuid4())
        booking = Booking(
            booking_id=booking_id,
            guest_id=guest_id,
            room_number=room_number,
            check_in=check_in,
            check_out=check_out,
            status=BookingStatus.CONFIRMED,
            total_amount=total_amount,
            created_at=datetime.now()
        )
        
        self.bookings[booking_id] = booking
        room.state = RoomState.RESERVED
        
        # Notify observers
        for observer in self.observers:
            observer.on_booking_confirmed(booking)
        
        return booking_id
    
    def check_in(self, booking_id: str) -> bool:
        """Check in guest"""
        if booking_id not in self.bookings:
            return False
        
        booking = self.bookings[booking_id]
        
        if booking.status != BookingStatus.CONFIRMED:
            return False
        
        room = self.rooms[booking.room_number]
        guest = self.guests[booking.guest_id]
        
        room.state = RoomState.OCCUPIED
        booking.status = BookingStatus.CHECKED_IN
        guest.check_in_date = datetime.now()
        guest.room_number = booking.room_number
        
        # Notify observers
        for observer in self.observers:
            observer.on_check_in(guest, room)
        
        return True
    
    def check_out(self, booking_id: str) -> float:
        """Check out guest and return total amount"""
        if booking_id not in self.bookings:
            return 0.0
        
        booking = self.bookings[booking_id]
        
        if booking.status != BookingStatus.CHECKED_IN:
            return 0.0
        
        room = self.rooms[booking.room_number]
        guest = self.guests[booking.guest_id]
        
        room.state = RoomState.AVAILABLE
        booking.status = BookingStatus.CHECKED_OUT
        guest.check_out_date = datetime.now()
        guest.room_number = None
        
        # Notify observers
        for observer in self.observers:
            observer.on_check_out(guest, booking.total_amount)
        
        return booking.total_amount
    
    def cancel_booking(self, booking_id: str) -> bool:
        """Cancel booking"""
        if booking_id not in self.bookings:
            return False
        
        booking = self.bookings[booking_id]
        
        if booking.status in [BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]:
            return False
        
        room = self.rooms[booking.room_number]
        room.state = RoomState.AVAILABLE
        booking.status = BookingStatus.CANCELLED
        
        return True


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("HOTEL MANAGEMENT SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    hotel = HotelService()
    hotel.add_observer(EmailNotifier())
    
    # Add rooms
    room1 = Room("101", RoomType.SINGLE, 1, 100.0, RoomState.AVAILABLE, 1)
    room2 = Room("201", RoomType.DOUBLE, 2, 150.0, RoomState.AVAILABLE, 2)
    hotel.add_room(room1)
    hotel.add_room(room2)
    
    print("1. Registering guest:")
    guest_id = hotel.register_guest("John Doe", "john@example.com", "123-456-7890")
    print(f"Guest registered: {guest_id}")
    print()
    
    print("2. Searching available rooms:")
    check_in = datetime.now() + timedelta(days=1)
    check_out = datetime.now() + timedelta(days=3)
    available = hotel.search_available_rooms(check_in, check_out)
    print(f"Available rooms: {[r.room_number for r in available]}")
    print()
    
    print("3. Booking room:")
    booking_id = hotel.book_room(guest_id, "101", check_in, check_out)
    print(f"Booking confirmed: {booking_id}")
    print()
    
    print("4. Checking in:")
    hotel.check_in(booking_id)
    print(f"Guest checked in to room 101")
    print()
    
    print("5. Testing seasonal pricing:")
    hotel.set_pricing_strategy(SeasonalPricingStrategy())
    price = hotel.pricing_strategy.calculate_price(room1, check_in, check_out)
    print(f"Seasonal price: ${price:.2f}")
    print()
    
    print("6. Checking out:")
    amount = hotel.check_out(booking_id)
    print(f"Checkout completed. Total: ${amount:.2f}")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. State Pattern - Room states")
    print("2. Strategy Pattern - Pricing strategies (Standard, Seasonal, Dynamic)")
    print("3. Observer Pattern - Booking notifications")
    print("4. Factory Pattern - Create bookings and guests")
    print("5. Command Pattern - Booking operations")
    print()
    print("FEATURES:")
    print("- Room booking")
    print("- Check-in/check-out")
    print("- Pricing strategies")
    print("- Guest management")
    print("- Billing")
    print("=" * 60)


if __name__ == "__main__":
    main()

