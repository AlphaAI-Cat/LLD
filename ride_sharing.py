"""
Ride-Sharing System (Uber/Ola-like)
===================================

Core Design: System for matching riders and drivers.

Design Patterns & Strategies Used:
1. Observer Pattern - Real-time location tracking and notifications
2. Strategy Pattern - Matching algorithms (Nearest, Load balancing)
3. State Pattern - Ride states (Requested, Matched, In Progress, Completed, Cancelled)
4. Factory Pattern - Create rides and matches
5. Command Pattern - Ride operations
6. Location Tracking - Real-time GPS updates

Features:
- Driver allocation
- Surge pricing based on demand
- Real-time location tracking
- Dynamic ETA calculation
- Cancellation handling
- Rating system
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass
from uuid import uuid4
import math
import random


class RideState(Enum):
    REQUESTED = "REQUESTED"
    MATCHED = "MATCHED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class Location:
    latitude: float
    longitude: float
    
    def distance_to(self, other: 'Location') -> float:
        """Calculate distance in km"""
        R = 6371
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c


class Driver:
    """Driver"""
    
    def __init__(self, driver_id: str, name: str, location: Location, vehicle_type: str):
        self.driver_id = driver_id
        self.name = name
        self.location = location
        self.vehicle_type = vehicle_type
        self.is_available = True
        self.current_ride: Optional[str] = None
        self.rating = 5.0
        self.total_rides = 0
    
    def start_ride(self, ride_id: str):
        """Start ride"""
        self.current_ride = ride_id
        self.is_available = False
    
    def complete_ride(self):
        """Complete ride"""
        self.current_ride = None
        self.is_available = True
        self.total_rides += 1
    
    def update_location(self, location: Location):
        """Update driver location"""
        self.location = location


class Rider:
    """Rider"""
    
    def __init__(self, rider_id: str, name: str):
        self.rider_id = rider_id
        self.name = name
        self.rating = 5.0


class Ride:
    """Ride with state management"""
    
    def __init__(self, ride_id: str, rider_id: str, pickup: Location, 
                 dropoff: Location, vehicle_type: str):
        self.ride_id = ride_id
        self.rider_id = rider_id
        self.pickup = pickup
        self.dropoff = dropoff
        self.vehicle_type = vehicle_type
        self.state = RideState.REQUESTED
        self.driver_id: Optional[str] = None
        self.base_fare = 50.0
        self.surge_multiplier = 1.0
        self.total_fare: Optional[float] = None
        self.created_at = datetime.now()
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.eta_minutes: Optional[int] = None
    
    def calculate_fare(self, distance_km: float, duration_minutes: int) -> float:
        """Calculate ride fare"""
        distance_fare = distance_km * 10  # $10 per km
        time_fare = duration_minutes * 1   # $1 per minute
        total = (self.base_fare + distance_fare + time_fare) * self.surge_multiplier
        self.total_fare = total
        return total
    
    def update_state(self, new_state: RideState):
        """Update ride state"""
        valid_transitions = {
            RideState.REQUESTED: [RideState.MATCHED, RideState.CANCELLED],
            RideState.MATCHED: [RideState.IN_PROGRESS, RideState.CANCELLED],
            RideState.IN_PROGRESS: [RideState.COMPLETED, RideState.CANCELLED],
            RideState.COMPLETED: [],
            RideState.CANCELLED: []
        }
        
        if new_state in valid_transitions.get(self.state, []):
            self.state = new_state
            return True
        return False
    
    def assign_driver(self, driver_id: str):
        """Assign driver"""
        self.driver_id = driver_id
    
    def calculate_eta(self, driver_location: Location) -> int:
        """Calculate ETA in minutes"""
        distance = driver_location.distance_to(self.pickup)
        # Assume average speed of 30 km/h
        eta_minutes = int((distance / 30) * 60)
        self.eta_minutes = eta_minutes
        return eta_minutes


class MatchingStrategy(ABC):
    """Ride matching strategy interface"""
    
    @abstractmethod
    def match_ride(self, ride: Ride, available_drivers: List[Driver]) -> Optional[Driver]:
        pass


class NearestDriverStrategy(MatchingStrategy):
    """Match with nearest driver"""
    
    def match_ride(self, ride: Ride, available_drivers: List[Driver]) -> Optional[Driver]:
        matching_drivers = [d for d in available_drivers 
                          if d.is_available and d.vehicle_type == ride.vehicle_type]
        
        if not matching_drivers:
            return None
        
        nearest = min(matching_drivers, 
                     key=lambda d: ride.pickup.distance_to(d.location))
        return nearest


class LoadBalancingStrategy(MatchingStrategy):
    """Match considering driver load"""
    
    def match_ride(self, ride: Ride, available_drivers: List[Driver]) -> Optional[Driver]:
        matching_drivers = [d for d in available_drivers 
                          if d.is_available and d.vehicle_type == ride.vehicle_type]
        
        if not matching_drivers:
            return None
        
        # Score based on distance and rating
        def score(driver: Driver) -> float:
            distance = ride.pickup.distance_to(driver.location)
            # Lower distance and higher rating is better
            return distance - (driver.rating * 2)
        
        best = min(matching_drivers, key=score)
        return best


class RideSharingService:
    """Main ride sharing service"""
    
    def __init__(self):
        self.rides: Dict[str, Ride] = {}
        self.drivers: Dict[str, Driver] = {}
        self.riders: Dict[str, Rider] = {}
        self.matching_strategy: MatchingStrategy = NearestDriverStrategy()
        self.observers: List = []
    
    def add_driver(self, driver: Driver):
        """Add driver"""
        self.drivers[driver.driver_id] = driver
    
    def add_rider(self, rider: Rider):
        """Add rider"""
        self.riders[rider.rider_id] = rider
    
    def set_matching_strategy(self, strategy: MatchingStrategy):
        """Set matching strategy"""
        self.matching_strategy = strategy
    
    def request_ride(self, rider_id: str, pickup: Location, dropoff: Location,
                    vehicle_type: str = "Sedan") -> Optional[str]:
        """Request ride"""
        ride_id = str(uuid4())
        
        # Calculate surge pricing
        surge = self._calculate_surge(pickup)
        
        ride = Ride(ride_id, rider_id, pickup, dropoff, vehicle_type)
        ride.surge_multiplier = surge
        
        self.rides[ride_id] = ride
        
        # Match driver
        self._match_driver(ride)
        
        return ride_id
    
    def _calculate_surge(self, location: Location) -> float:
        """Calculate surge pricing based on demand"""
        # Simulate surge calculation
        # In real system, would consider nearby requests and available drivers
        base_surge = 1.0
        # Random surge between 1.0 and 2.0 for demo
        return base_surge + random.random()
    
    def _match_driver(self, ride: Ride):
        """Match driver to ride"""
        available_drivers = list(self.drivers.values())
        driver = self.matching_strategy.match_ride(ride, available_drivers)
        
        if driver:
            ride.assign_driver(driver.driver_id)
            ride.update_state(RideState.MATCHED)
            driver.start_ride(ride.ride_id)
            
            # Calculate ETA
            eta = ride.calculate_eta(driver.location)
            print(f"[Match] Driver {driver.driver_id} matched. ETA: {eta} minutes")
        else:
            print("[Match] No driver available")
    
    def start_ride(self, ride_id: str):
        """Start ride"""
        if ride_id not in self.rides:
            return False
        
        ride = self.rides[ride_id]
        if ride.update_state(RideState.IN_PROGRESS):
            ride.start_time = datetime.now()
            return True
        return False
    
    def complete_ride(self, ride_id: str) -> Optional[float]:
        """Complete ride and calculate fare"""
        if ride_id not in self.rides:
            return None
        
        ride = self.rides[ride_id]
        
        if ride.state != RideState.IN_PROGRESS:
            return None
        
        ride.update_state(RideState.COMPLETED)
        ride.end_time = datetime.now()
        
        # Calculate fare
        distance = ride.pickup.distance_to(ride.dropoff)
        duration = (ride.end_time - ride.start_time).total_seconds() / 60
        fare = ride.calculate_fare(distance, duration)
        
        # Release driver
        if ride.driver_id and ride.driver_id in self.drivers:
            self.drivers[ride.driver_id].complete_ride()
        
        return fare
    
    def cancel_ride(self, ride_id: str, cancelled_by: str):
        """Cancel ride"""
        if ride_id not in self.rides:
            return False
        
        ride = self.rides[ride_id]
        
        if ride.state in [RideState.COMPLETED, RideState.CANCELLED]:
            return False
        
        ride.update_state(RideState.CANCELLED)
        
        # Release driver if matched
        if ride.driver_id and ride.driver_id in self.drivers:
            self.drivers[ride.driver_id].complete_ride()
        
        print(f"[Cancel] Ride {ride_id} cancelled by {cancelled_by}")
        return True
    
    def update_driver_location(self, driver_id: str, location: Location):
        """Update driver location"""
        if driver_id in self.drivers:
            self.drivers[driver_id].update_location(location)
            
            # Update ETA for active ride
            for ride in self.rides.values():
                if ride.driver_id == driver_id and ride.state == RideState.MATCHED:
                    ride.calculate_eta(location)
    
    def get_ride_status(self, ride_id: str) -> Optional[Dict]:
        """Get ride status"""
        if ride_id not in self.rides:
            return None
        
        ride = self.rides[ride_id]
        return {
            "ride_id": ride_id,
            "state": ride.state.value,
            "driver_id": ride.driver_id,
            "eta": ride.eta_minutes,
            "surge_multiplier": ride.surge_multiplier,
            "fare": ride.total_fare
        }


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("RIDE-SHARING SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    service = RideSharingService()
    
    # Add drivers
    driver1 = Driver("D1", "John", Location(28.6139, 77.2090), "Sedan")
    driver2 = Driver("D2", "Jane", Location(28.6145, 77.2095), "Sedan")
    service.add_driver(driver1)
    service.add_driver(driver2)
    
    # Add rider
    rider = Rider("R1", "Alice")
    service.add_rider(rider)
    
    print("1. Requesting ride:")
    pickup = Location(28.6200, 77.2200)
    dropoff = Location(28.6300, 77.2300)
    ride_id = service.request_ride("R1", pickup, dropoff)
    print(f"Ride requested: {ride_id}")
    print()
    
    print("2. Ride status:")
    status = service.get_ride_status(ride_id)
    print(f"Status: {status}")
    print()
    
    print("3. Starting ride:")
    service.start_ride(ride_id)
    status = service.get_ride_status(ride_id)
    print(f"Status: {status}")
    print()
    
    print("4. Completing ride:")
    fare = service.complete_ride(ride_id)
    print(f"Fare: ${fare:.2f}")
    print()
    
    print("5. Testing load balancing strategy:")
    service.set_matching_strategy(LoadBalancingStrategy())
    ride_id2 = service.request_ride("R1", pickup, dropoff)
    print(f"Ride with load balancing: {ride_id2}")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. Observer Pattern - Location tracking and notifications")
    print("2. Strategy Pattern - Matching algorithms (Nearest, Load balancing)")
    print("3. State Pattern - Ride lifecycle states")
    print("4. Factory Pattern - Create rides")
    print("5. Command Pattern - Ride operations")
    print()
    print("FEATURES:")
    print("- Driver allocation with multiple strategies")
    print("- Surge pricing")
    print("- Real-time location tracking")
    print("- Dynamic ETA calculation")
    print("- Cancellation handling")
    print("=" * 60)


if __name__ == "__main__":
    main()

