"""
Parking Management System - Simplified for Interview
Design Patterns:
1. Observer Pattern - Event notifications
2. State Pattern - Slot states (Available, Occupied)
3. Strategy Pattern - Pricing strategies
4. Factory Pattern - Vehicle creation
5. Singleton Pattern - Single manager instance
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime, timedelta


# ==================== OBSERVER PATTERN ====================

class Observer(ABC):
    @abstractmethod
    def update(self, event: str, message: str):
        pass


class ParkingNotifier:
    """Subject - notifies observers"""
    
    def __init__(self):
        self.observers: List[Observer] = []
    
    def attach(self, observer: Observer):
        if observer not in self.observers:
            self.observers.append(observer)

    def detach(self, observer: Observer):
        if observer in self.observers:
            self.observers.remove(observer)
    
    def notify(self, event: str, message: str):
        for observer in self.observers:
            observer.update(event, message)


class DisplayBoard(Observer):
    """Observer - shows parking status"""
    
    def update(self, event: str, message: str):
        print(f"[Display] {message}")


class SMSNotifier(Observer):
    """Observer - sends SMS"""
    
    def update(self, event: str, message: str):
        if event in ["PARKED", "FULL", "PAID"]:
            print(f"[SMS] {message}")


# ==================== STATE PATTERN ====================

class SlotState(ABC):
    @abstractmethod
    def park(self, slot: 'ParkingSlot') -> bool:
        pass
    
    @abstractmethod
    def unpark(self, slot: 'ParkingSlot') -> bool:
        pass


class Available(SlotState):
    def park(self, slot: 'ParkingSlot') -> bool:
        slot.state = Occupied()
        return True
    
    def unpark(self, slot: 'ParkingSlot') -> bool:
        return False


class Occupied(SlotState):
    def park(self, slot: 'ParkingSlot') -> bool:
        return False
    
    def unpark(self, slot: 'ParkingSlot') -> bool:
        slot.state = Available()
        return True


# ==================== STRATEGY PATTERN ====================

class VehicleType(Enum):
    CAR = "CAR"
    BIKE = "BIKE"
    TRUCK = "TRUCK"


class PricingStrategy(ABC):
    @abstractmethod
    def calculate(self, hours: float) -> float:
        pass


class HourlyPricing(PricingStrategy):
    def __init__(self, rate: float):
        self.rate = rate
    
    def calculate(self, hours: float) -> float:
        return hours * self.rate


class DailyPricing(PricingStrategy):
    def __init__(self, rate: float):
        self.rate = rate
    
    def calculate(self, hours: float) -> float:
        days = max(1, (hours + 23) // 24)
        return days * self.rate


# ==================== CORE CLASSES ====================

class Vehicle:
    def __init__(self, plate: str, v_type: VehicleType):
        self.license_plate = plate
        self.vehicle_type = v_type


# ==================== FACTORY PATTERN ====================

class VehicleFactory:
    """Factory for creating vehicles with validation"""
    
    @staticmethod
    def create_vehicle(plate: str, v_type: VehicleType) -> Optional[Vehicle]:
        """Create a vehicle with validation"""
        # Validate license plate format
        if not plate or len(plate.strip()) == 0:
            print("Error: Invalid license plate")
            return None
        
        # Validate vehicle type
        if v_type not in VehicleType:
            print("Error: Invalid vehicle type")
            return None
        
        return Vehicle(plate.strip().upper(), v_type)
    
    @staticmethod
    def create_car(plate: str) -> Optional[Vehicle]:
        """Convenience method for creating cars"""
        return VehicleFactory.create_vehicle(plate, VehicleType.CAR)
    
    @staticmethod
    def create_bike(plate: str) -> Optional[Vehicle]:
        """Convenience method for creating bikes"""
        return VehicleFactory.create_vehicle(plate, VehicleType.BIKE)
    
    @staticmethod
    def create_truck(plate: str) -> Optional[Vehicle]:
        """Convenience method for creating trucks"""
        return VehicleFactory.create_vehicle(plate, VehicleType.TRUCK)


class ParkingSlot:
    def __init__(self, slot_id: str, slot_type: VehicleType):
        self.slot_id = slot_id
        self.slot_type = slot_type
        self.state: SlotState = Available()
        self.vehicle: Optional[Vehicle] = None
        self.parked_at: Optional[datetime] = None
    
    def park(self, vehicle: Vehicle) -> bool:
        if vehicle.vehicle_type != self.slot_type:
            return False
        if self.state.park(self):
            self.vehicle = vehicle
            self.parked_at = datetime.now()
            return True
        return False
    
    def unpark(self) -> Optional[Vehicle]:
        if self.state.unpark(self):
            vehicle = self.vehicle
            self.vehicle = None
            self.parked_at = None
            return vehicle
        return None
    
    def is_available(self) -> bool:
        return isinstance(self.state, Available)


# ==================== SINGLETON PATTERN ====================

class ParkingLotManager:
    """Singleton - manages parking lot"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init = False
        return cls._instance
    
    def __init__(self):
        if self._init:
            return
        
        self.slots: List[ParkingSlot] = []
        self.notifier = ParkingNotifier()
        self.active_vehicles: Dict[str, ParkingSlot] = {}
        self.pricing: Dict[VehicleType, PricingStrategy] = {
            VehicleType.CAR: HourlyPricing(2.0),
            VehicleType.BIKE: HourlyPricing(1.0),
            VehicleType.TRUCK: HourlyPricing(5.0)
        }
        
        # Attach observers
        self.notifier.attach(DisplayBoard())
        self.notifier.attach(SMSNotifier())
        
        self._init = True
    
    def add_slot(self, slot: ParkingSlot):
        self.slots.append(slot)
        self.notifier.notify("UPDATE", f"Added slot {slot.slot_id}")
    
    def find_slot(self, v_type: VehicleType) -> Optional[ParkingSlot]:
        for slot in self.slots:
            if slot.slot_type == v_type and slot.is_available():
                return slot
        return None
    
    def park_vehicle(self, vehicle: Vehicle) -> Optional[str]:
        slot = self.find_slot(vehicle.vehicle_type)
        if not slot:
            self.notifier.notify("FULL", f"No slot for {vehicle.vehicle_type.value}")
            return None
        
        if slot.park(vehicle):
            self.active_vehicles[vehicle.license_plate] = slot
            self.notifier.notify("PARKED", 
                               f"{vehicle.license_plate} parked in {slot.slot_id}")
            return slot.slot_id
        return None
    
    def unpark_vehicle(self, plate: str) -> Optional[float]:
        if plate not in self.active_vehicles:
            return None
        
        slot = self.active_vehicles[plate]
        vehicle = slot.unpark()
        if not vehicle:
            return None
        
        # Calculate cost
        duration = datetime.now() - slot.parked_at if slot.parked_at else timedelta(0)
        hours = duration.total_seconds() / 3600
        cost = self.pricing[vehicle.vehicle_type].calculate(hours)
        
        del self.active_vehicles[plate]
        self.notifier.notify("PAID", f"{plate} paid ${cost:.2f}")
        
        return cost
    
    def set_pricing(self, v_type: VehicleType, strategy: PricingStrategy):
        self.pricing[v_type] = strategy
    
    def get_status(self) -> Dict:
        status = {}
        for slot in self.slots:
            v_type = slot.slot_type.value
            if v_type not in status:
                status[v_type] = {"total": 0, "available": 0, "occupied": 0}
            
            status[v_type]["total"] += 1
            if slot.is_available():
                status[v_type]["available"] += 1
            else:
                status[v_type]["occupied"] += 1
        return status


# ==================== DEMO ====================

def main():
    print("=" * 50)
    print("PARKING MANAGEMENT SYSTEM")
    print("=" * 50)
    print()
    
    # Singleton
    lot = ParkingLotManager()
    lot2 = ParkingLotManager()
    print(f"Singleton: lot is lot2? {lot is lot2}")
    print()
    
    # Add slots
    lot.add_slot(ParkingSlot("C1", VehicleType.CAR))
    lot.add_slot(ParkingSlot("C2", VehicleType.CAR))
    lot.add_slot(ParkingSlot("B1", VehicleType.BIKE))
    print()
    
    # Park vehicles (using Factory Pattern)
    car = VehicleFactory.create_car("ABC-123")
    bike = VehicleFactory.create_bike("XYZ-789")
    
    lot.park_vehicle(car)
    lot.park_vehicle(bike)
    print()
    
    # State check
    print("Slot states:")
    for slot in lot.slots:
        state = "Available" if slot.is_available() else "Occupied"
        print(f"{slot.slot_id}: {state}")
    print()
    
    # Strategy - change pricing
    lot.set_pricing(VehicleType.CAR, DailyPricing(15.0))
    print("Changed to daily pricing for cars")
    print()
    
    # Unpark
    cost = lot.unpark_vehicle("ABC-123")
    print(f"Unparked. Cost: ${cost:.2f}")
    print()
    
    # Status
    status = lot.get_status()
    for v_type, stats in status.items():
        print(f"{v_type}: {stats['available']}/{stats['total']} available")
    print()
    
    print("DESIGN PATTERNS:")
    print("1. Observer - Display & SMS notifications")
    print("2. State - Slot states (Available/Occupied)")
    print("3. Strategy - Pricing (Hourly/Daily)")
    print("4. Factory - Vehicle creation with validation")
    print("5. Singleton - Single lot manager")


if __name__ == "__main__":
    main()
