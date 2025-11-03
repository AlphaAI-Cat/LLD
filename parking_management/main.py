"""
Parking Management System
Design Patterns Used:
1. Observer Pattern - For notifying subscribers about parking events
2. Singleton Pattern - For the ParkingLotManager
3. Factory Pattern - For creating vehicles and parking slots
4. Strategy Pattern - For different pricing strategies
5. State Pattern - For parking slot states (Available, Occupied, Maintenance)
6. Command Pattern - For parking/unparking operations with undo capability
7. Decorator Pattern - For premium parking features
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass


# ==================== OBSERVER PATTERN ====================
# Allows objects to notify multiple observers about parking events

class Observer(ABC):
    """Observer interface for the Observer Pattern"""
    
    @abstractmethod
    def update(self, event_type: str, message: str):
        pass


class ParkingEventNotifier:
    """Subject for Observer Pattern - manages observers and notifies them"""
    
    def __init__(self):
        self._observers: List[Observer] = []
    
    def attach(self, observer: Observer):
        """Attach an observer"""
        if observer not in self._observers:
            self._observers.append(observer)
    
    def detach(self, observer: Observer):
        """Detach an observer"""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify(self, event_type: str, message: str):
        """Notify all observers"""
        for observer in self._observers:
            observer.update(event_type, message)


class ParkingDisplayBoard(Observer):
    """Concrete Observer - displays parking availability"""
    
    def __init__(self):
        self.availability: Dict[str, int] = {}
    
    def update(self, event_type: str, message: str):
        if event_type == "PARKING_UPDATE":
            print(f"[Display Board] {message}")
            self._update_availability(message)
    
    def _update_availability(self, message: str):
        # Parse and update availability from message
        if "available" in message.lower():
            # Update internal state
            pass


class SMSNotifier(Observer):
    """Concrete Observer - sends SMS notifications"""
    
    def update(self, event_type: str, message: str):
        if event_type in ["PARKING_FULL", "VEHICLE_PARKED", "PAYMENT_RECEIVED"]:
            print(f"[SMS] {message}")


# ==================== STATE PATTERN ====================
# Represents parking slot states (Available, Occupied, Maintenance)

class SlotState(ABC):
    """State interface for State Pattern"""
    
    @abstractmethod
    def park(self, slot: 'ParkingSlot') -> bool:
        pass
    
    @abstractmethod
    def unpark(self, slot: 'ParkingSlot') -> bool:
        pass
    
    @abstractmethod
    def get_state_name(self) -> str:
        pass


class AvailableState(SlotState):
    """Concrete State - Slot is available"""
    
    def park(self, slot: 'ParkingSlot') -> bool:
        slot.state = OccupiedState()
        return True
    
    def unpark(self, slot: 'ParkingSlot') -> bool:
        return False
    
    def get_state_name(self) -> str:
        return "AVAILABLE"


class OccupiedState(SlotState):
    """Concrete State - Slot is occupied"""
    
    def park(self, slot: 'ParkingSlot') -> bool:
        return False
    
    def unpark(self, slot: 'ParkingSlot') -> bool:
        slot.state = AvailableState()
        return True
    
    def get_state_name(self) -> str:
        return "OCCUPIED"


class MaintenanceState(SlotState):
    """Concrete State - Slot is under maintenance"""
    
    def park(self, slot: 'ParkingSlot') -> bool:
        return False
    
    def unpark(self, slot: 'ParkingSlot') -> bool:
        return False
    
    def get_state_name(self) -> str:
        return "MAINTENANCE"


# ==================== FACTORY PATTERN ====================
# Creates different types of vehicles and parking slots

class VehicleType(Enum):
    CAR = "CAR"
    MOTORCYCLE = "MOTORCYCLE"
    TRUCK = "TRUCK"
    VAN = "VAN"


class Vehicle(ABC):
    """Base vehicle class"""
    
    def __init__(self, license_plate: str, vehicle_type: VehicleType):
        self.license_plate = license_plate
        self.vehicle_type = vehicle_type


class VehicleFactory:
    """Factory Pattern - Creates vehicles"""
    
    @staticmethod
    def create_vehicle(vehicle_type: VehicleType, license_plate: str) -> Vehicle:
        if vehicle_type == VehicleType.CAR:
            return Car(license_plate)
        elif vehicle_type == VehicleType.MOTORCYCLE:
            return Motorcycle(license_plate)
        elif vehicle_type == VehicleType.TRUCK:
            return Truck(license_plate)
        elif vehicle_type == VehicleType.VAN:
            return Van(license_plate)
        else:
            raise ValueError(f"Unknown vehicle type: {vehicle_type}")


class Car(Vehicle):
    def __init__(self, license_plate: str):
        super().__init__(license_plate, VehicleType.CAR)


class Motorcycle(Vehicle):
    def __init__(self, license_plate: str):
        super().__init__(license_plate, VehicleType.MOTORCYCLE)


class Truck(Vehicle):
    def __init__(self, license_plate: str):
        super().__init__(license_plate, VehicleType.TRUCK)


class Van(Vehicle):
    def __init__(self, license_plate: str):
        super().__init__(license_plate, VehicleType.VAN)


class ParkingSlot:
    """Parking slot with State Pattern"""
    
    def __init__(self, slot_id: str, slot_type: VehicleType, floor: int):
        self.slot_id = slot_id
        self.slot_type = slot_type
        self.floor = floor
        self.state: SlotState = AvailableState()
        self.vehicle: Optional[Vehicle] = None
        self.parked_at: Optional[datetime] = None
    
    def park_vehicle(self, vehicle: Vehicle) -> bool:
        if vehicle.vehicle_type != self.slot_type:
            return False
        if self.state.park(self):
            self.vehicle = vehicle
            self.parked_at = datetime.now()
            return True
        return False
    
    def unpark_vehicle(self) -> Optional[Vehicle]:
        if self.state.unpark(self):
            vehicle = self.vehicle
            self.vehicle = None
            self.parked_at = None
            return vehicle
        return None
    
    def is_available(self) -> bool:
        return isinstance(self.state, AvailableState)


# ==================== STRATEGY PATTERN ====================
# Different pricing strategies (Hourly, Daily, Flat Rate)

class PricingStrategy(ABC):
    """Strategy interface for Strategy Pattern"""
    
    @abstractmethod
    def calculate_cost(self, duration: timedelta) -> float:
        pass


class HourlyPricingStrategy(PricingStrategy):
    """Concrete Strategy - Hourly pricing"""
    
    def __init__(self, rate_per_hour: float):
        self.rate_per_hour = rate_per_hour
    
    def calculate_cost(self, duration: timedelta) -> float:
        hours = duration.total_seconds() / 3600
        return hours * self.rate_per_hour


class DailyPricingStrategy(PricingStrategy):
    """Concrete Strategy - Daily pricing"""
    
    def __init__(self, rate_per_day: float):
        self.rate_per_day = rate_per_day
    
    def calculate_cost(self, duration: timedelta) -> float:
        days = max(1, duration.days + (1 if duration.seconds > 0 else 0))
        return days * self.rate_per_day


class FlatRatePricingStrategy(PricingStrategy):
    """Concrete Strategy - Flat rate pricing"""
    
    def __init__(self, flat_rate: float):
        self.flat_rate = flat_rate
    
    def calculate_cost(self, duration: timedelta) -> float:
        return self.flat_rate


# ==================== DECORATOR PATTERN ====================
# Adds premium features to parking slots

class PremiumFeature(ABC):
    """Decorator Pattern - Base component"""
    
    @abstractmethod
    def get_description(self) -> str:
        pass
    
    @abstractmethod
    def get_additional_cost(self, base_cost: float) -> float:
        pass


class BasicParking(PremiumFeature):
    """Concrete Component - Basic parking"""
    
    def get_description(self) -> str:
        return "Basic Parking"
    
    def get_additional_cost(self, base_cost: float) -> float:
        return 0.0


class CoveredParking(PremiumFeature):
    """Concrete Decorator - Adds covered parking feature"""
    
    def __init__(self, parking: PremiumFeature):
        self._parking = parking
        self.extra_cost = 5.0
    
    def get_description(self) -> str:
        return f"{self._parking.get_description()} + Covered"
    
    def get_additional_cost(self, base_cost: float) -> float:
        return self._parking.get_additional_cost(base_cost) + self.extra_cost


class ValetParking(PremiumFeature):
    """Concrete Decorator - Adds valet parking feature"""
    
    def __init__(self, parking: PremiumFeature):
        self._parking = parking
        self.extra_cost = 10.0
    
    def get_description(self) -> str:
        return f"{self._parking.get_description()} + Valet"
    
    def get_additional_cost(self, base_cost: float) -> float:
        return self._parking.get_additional_cost(base_cost) + self.extra_cost


# ==================== COMMAND PATTERN ====================
# Encapsulates parking/unparking operations with undo capability

class Command(ABC):
    """Command interface for Command Pattern"""
    
    @abstractmethod
    def execute(self) -> bool:
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        pass


class ParkCommand(Command):
    """Concrete Command - Park vehicle"""
    
    def __init__(self, slot: ParkingSlot, vehicle: Vehicle, notifier: ParkingEventNotifier):
        self.slot = slot
        self.vehicle = vehicle
        self.notifier = notifier
        self.executed = False
    
    def execute(self) -> bool:
        if self.slot.park_vehicle(self.vehicle):
            self.executed = True
            self.notifier.notify("VEHICLE_PARKED", 
                               f"Vehicle {self.vehicle.license_plate} parked in {self.slot.slot_id}")
            return True
        return False
    
    def undo(self) -> bool:
        if self.executed:
            self.slot.unpark_vehicle()
            self.notifier.notify("PARKING_CANCELLED", 
                               f"Parking cancelled for {self.vehicle.license_plate}")
            self.executed = False
            return True
        return False


class UnparkCommand(Command):
    """Concrete Command - Unpark vehicle"""
    
    def __init__(self, slot: ParkingSlot, notifier: ParkingEventNotifier):
        self.slot = slot
        self.notifier = notifier
        self.vehicle: Optional[Vehicle] = None
        self.executed = False
    
    def execute(self) -> bool:
        self.vehicle = self.slot.unpark_vehicle()
        if self.vehicle:
            self.executed = True
            self.notifier.notify("VEHICLE_UNPARKED", 
                               f"Vehicle {self.vehicle.license_plate} unparked from {self.slot.slot_id}")
            return True
        return False
    
    def undo(self) -> bool:
        if self.executed and self.vehicle:
            self.slot.park_vehicle(self.vehicle)
            self.notifier.notify("UNPARK_CANCELLED", 
                               f"Unpark cancelled for {self.vehicle.license_plate}")
            self.executed = False
            return True
        return False


# ==================== SINGLETON PATTERN ====================
# Ensures only one instance of ParkingLotManager exists

class ParkingLotManager:
    """Singleton Pattern - Manages the entire parking lot"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ParkingLotManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.slots: List[ParkingSlot] = []
        self.notifier = ParkingEventNotifier()
        self.pricing_strategies: Dict[VehicleType, PricingStrategy] = {}
        self.active_vehicles: Dict[str, ParkingSlot] = {}  # license_plate -> slot
        self.command_history: List[Command] = []
        
        # Initialize default pricing strategies
        self.pricing_strategies[VehicleType.CAR] = HourlyPricingStrategy(2.0)
        self.pricing_strategies[VehicleType.MOTORCYCLE] = HourlyPricingStrategy(1.0)
        self.pricing_strategies[VehicleType.TRUCK] = HourlyPricingStrategy(5.0)
        self.pricing_strategies[VehicleType.VAN] = HourlyPricingStrategy(3.0)
        
        # Attach default observers
        self.display_board = ParkingDisplayBoard()
        self.sms_notifier = SMSNotifier()
        self.notifier.attach(self.display_board)
        self.notifier.attach(self.sms_notifier)
        
        self._initialized = True
    
    def add_slot(self, slot: ParkingSlot):
        """Add a parking slot"""
        self.slots.append(slot)
        self.notifier.notify("PARKING_UPDATE", 
                           f"Slot {slot.slot_id} added. Type: {slot.slot_type.value}")
    
    def find_available_slot(self, vehicle_type: VehicleType) -> Optional[ParkingSlot]:
        """Find an available slot for vehicle type"""
        for slot in self.slots:
            if slot.slot_type == vehicle_type and slot.is_available():
                return slot
        return None
    
    def park_vehicle(self, vehicle: Vehicle) -> Optional[str]:
        """Park a vehicle using Command Pattern"""
        slot = self.find_available_slot(vehicle.vehicle_type)
        if not slot:
            self.notifier.notify("PARKING_FULL", 
                               f"No available slots for {vehicle.vehicle_type.value}")
            return None
        
        command = ParkCommand(slot, vehicle, self.notifier)
        if command.execute():
            self.active_vehicles[vehicle.license_plate] = slot
            self.command_history.append(command)
            return slot.slot_id
        return None
    
    def unpark_vehicle(self, license_plate: str) -> Optional[float]:
        """Unpark a vehicle and calculate cost"""
        if license_plate not in self.active_vehicles:
            return None
        
        slot = self.active_vehicles[license_plate]
        vehicle = slot.vehicle
        
        command = UnparkCommand(slot, self.notifier)
        if command.execute():
            duration = datetime.now() - slot.parked_at if slot.parked_at else timedelta(0)
            
            # Calculate base cost using Strategy Pattern
            pricing_strategy = self.pricing_strategies[vehicle.vehicle_type]
            base_cost = pricing_strategy.calculate_cost(duration)
            
            # Apply Decorator Pattern for premium features (example)
            premium_service = BasicParking()
            # Can be decorated: premium_service = CoveredParking(premium_service)
            additional_cost = premium_service.get_additional_cost(base_cost)
            
            total_cost = base_cost + additional_cost
            
            del self.active_vehicles[license_plate]
            self.command_history.append(command)
            
            self.notifier.notify("PAYMENT_RECEIVED", 
                               f"Payment of ${total_cost:.2f} received for {license_plate}")
            
            return total_cost
        
        return None
    
    def set_pricing_strategy(self, vehicle_type: VehicleType, strategy: PricingStrategy):
        """Set pricing strategy using Strategy Pattern"""
        self.pricing_strategies[vehicle_type] = strategy
    
    def get_status(self) -> Dict:
        """Get parking lot status"""
        status = {}
        for slot in self.slots:
            slot_type = slot.slot_type.value
            if slot_type not in status:
                status[slot_type] = {"total": 0, "available": 0, "occupied": 0}
            
            status[slot_type]["total"] += 1
            if slot.is_available():
                status[slot_type]["available"] += 1
            else:
                status[slot_type]["occupied"] += 1
        
        return status


# ==================== DEMONSTRATION ====================

def main():
    """Demonstrate the Parking Management System with all design patterns"""
    
    print("=" * 60)
    print("PARKING MANAGEMENT SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    # Singleton Pattern - Get the only instance
    manager = ParkingLotManager()
    manager2 = ParkingLotManager()
    print(f"Singleton Pattern: manager is manager2? {manager is manager2}")
    print()
    
    # Factory Pattern - Create vehicles
    print("Factory Pattern - Creating vehicles:")
    car1 = VehicleFactory.create_vehicle(VehicleType.CAR, "ABC-123")
    motorcycle1 = VehicleFactory.create_vehicle(VehicleType.MOTORCYCLE, "XYZ-789")
    truck1 = VehicleFactory.create_vehicle(VehicleType.TRUCK, "TRK-456")
    print(f"Created: {car1.license_plate} ({car1.vehicle_type.value})")
    print(f"Created: {motorcycle1.license_plate} ({motorcycle1.vehicle_type.value})")
    print(f"Created: {truck1.license_plate} ({truck1.vehicle_type.value})")
    print()
    
    # Add parking slots
    print("Adding parking slots:")
    for i in range(3):
        manager.add_slot(ParkingSlot(f"C-{i+1}", VehicleType.CAR, 1))
    for i in range(2):
        manager.add_slot(ParkingSlot(f"M-{i+1}", VehicleType.MOTORCYCLE, 1))
    for i in range(1):
        manager.add_slot(ParkingSlot(f"T-{i+1}", VehicleType.TRUCK, 1))
    print()
    
    # Observer Pattern - Display board will be notified
    print("Observer Pattern - Parking vehicles (observers will be notified):")
    manager.park_vehicle(car1)
    manager.park_vehicle(motorcycle1)
    manager.park_vehicle(truck1)
    print()
    
    # State Pattern - Show slot states
    print("State Pattern - Checking slot states:")
    for slot in manager.slots[:3]:
        print(f"Slot {slot.slot_id}: {slot.state.get_state_name()}")
    print()
    
    # Strategy Pattern - Change pricing strategy
    print("Strategy Pattern - Setting daily pricing for cars:")
    daily_strategy = DailyPricingStrategy(15.0)
    manager.set_pricing_strategy(VehicleType.CAR, daily_strategy)
    print()
    
    # Decorator Pattern - Premium features
    print("Decorator Pattern - Premium parking features:")
    basic = BasicParking()
    covered = CoveredParking(basic)
    valet = ValetParking(covered)
    print(f"Service: {valet.get_description()}")
    print(f"Additional cost: ${valet.get_additional_cost(10.0):.2f}")
    print()
    
    # Command Pattern - Unpark with undo capability
    print("Command Pattern - Unparking vehicle:")
    cost = manager.unpark_vehicle(car1.license_plate)
    print(f"Total cost: ${cost:.2f}")
    print()
    
    # Show final status
    print("Final Parking Status:")
    status = manager.get_status()
    for vehicle_type, stats in status.items():
        print(f"{vehicle_type}: {stats['available']}/{stats['total']} available, "
              f"{stats['occupied']} occupied")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS USED:")
    print("=" * 60)
    print("1. Observer Pattern - Notifies display boards, SMS services")
    print("2. Singleton Pattern - Single ParkingLotManager instance")
    print("3. Factory Pattern - Creates different vehicle types")
    print("4. Strategy Pattern - Different pricing strategies (hourly, daily, flat)")
    print("5. State Pattern - Slot states (Available, Occupied, Maintenance)")
    print("6. Command Pattern - Park/Unpark operations with undo")
    print("7. Decorator Pattern - Premium features (covered, valet)")
    print("=" * 60)


if __name__ == "__main__":
    main()
