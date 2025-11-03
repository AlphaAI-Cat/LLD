from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass

class Observer(ABC):

    @abstractmethod
    def update(self, event_type: str, message: str):
        pass

class ParkingEventNotifier:

    def __init__(self):
        self._observers: List[Observer] = []

    def attach(self, observer: Observer):
        if observer not in self._observers: 
            self._observers.append(observer)

    def detach(self, observer: Observer):
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event_type: str, message: str):
        for observer in self._observers:
            observer.update(event_type, message)


class ParkingDisplayBoard(Observer):

    def __init__(self):
        self.availability: Dict[str, int] = {}
    
    def update(self, event_type: str, message: str):
        if event_type == "PARKING_UPDATE":
            print(f"[Display Board] {message}")
            self._update_availability(message)
    
    def _update_availability(self, message: str):
        if "available" in message.lower():
            self.availability[message.split(" ")[1]] += 1
        else:
            self.availability[message.split(" ")[1]] -= 1


class SMSNotifier(Observer):
    def update(self, event_type: str, message: str):
        if event_type in ["PARKING_FULL", "VEHICLE_PARKED", "PAYMENT_RECEIVED"]:
            print(f"[SMS] {message}")


class SlotState(ABC):
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
    def park(self, slot: 'ParkingSlot') -> bool:
        slot.state = OccupiedState()
        return True
    
    def unpark(self, slot: 'ParkingSlot') -> bool:
        return False
    
    def get_state_name(self) -> str:
        return "AVAILABLE"


class OccupiedState(SlotState):
    def park(self, slot: 'ParkingSlot') -> bool:
        return False
    def unpark(self, slot: 'ParkingSlot') -> bool:
        slot.state = AvailableState()
        return True
    def get_state_name(self) -> str:
        return "OCCUPIED"
    

class MaintenanceState(SlotState):
    def park(self, slot: 'ParkingSlot') -> bool:
        return False
    def unpark(self, slot: 'ParkingSlot') -> bool:
        return False
    def get_state_name(self) -> str:
        return "MAINTENANCE"


class VehicleType(Enum):
    CAR = "CAR"
    MOTORCYCLE = "MOTORCYCLE"
    TRUCK = "TRUCK"
    VAN = "VAN"



class Vehicle(ABC):
    def __init__(self, license_plate: str, vehicle_type: VehicleType):
        self.license_plate = license_plate


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
        return False

    
    def is_available(self) -> bool:
        return isinstance(self.state, AvailableState)



class PricingStrategy(ABC):

    @abstractmethod
    def calculate_cost(self, duration: timedelta) -> float:
        pass


class HourlyPricingStrategy(PricingStrategy):
    def __init__(self, rate_per_hour: float):
        self.rate_per_hour = rate_per_hour
    
    def calculate_cost(self, duration: timedelta) -> float:
        return duration.total_seconds() / 3600 * self.rate_per_hour


class DailyPricingStrategy(PricingStrategy):
    def __init__(self, rate_per_day: float):
        self.rate_per_day = rate_per_day
    
    def calculate_cost(self, duration: timedelta) -> float:
        return duration.total_seconds() / 86400 * self.rate_per_day
    
class FlatRatePricingStrategy(PricingStrategy):
    def __init__(self, flat_rate: float):
        self.flat_rate = flat_rate
    
    def calculate_cost(self, duration: timedelta) -> float:
        return self.flat_rate


def ParkCommand(Command):
    def __init__(self, slot: ParkingSlot, vehicle: Vehicle, notifier: ParkingEventNotifier):
        self.slot = slot
        self.vehicle = vehicle
        self.notifier = notifier
        self.executed = False
    
    def execute(self) -> bool:
        if self.slot.park_vehicle(self.vehicle):
            self.executed = True
            self.notifier.notify("VEHICLE_PARKED", f"Vehicle {self.vehicle.license_plate} parked in slot {self.slot.slot_id}")
            return True
        return False

    def undo(self) -> bool:
        if self.executed:
            self.slot.unpark_vehicle(self.vehicle.license_plate)
            self.notifier.notify("PARKING_CANCELLED", f"Parking cancelled for vehicle {self.vehicle.license_plate}")
            self.executed = False
            return True
        return False

class ParkingLotManager:
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
        self.active_vehicles: Dict[str, ParkingSlot] = {}
        self.command_history: List[Command] = []
        self._initialized = True
        self.pricing_strategies[VehicleType.CAR] = HourlyPricingStrategy(2.0)
        self.pricing_strategies[VehicleType.MOTORCYCLE] = HourlyPricingStrategy(1.0)
        self.pricing_strategies[VehicleType.TRUCK] = HourlyPricingStrategy(5.0)
        self.pricing_strategies[VehicleType.VAN] = HourlyPricingStrategy(3.0)
        self.display_board = ParkingDisplayBoard()
        self.sms_notifier = SMSNotifier()
        self.notifier.attach(self.display_board)
        self.notifier.attach(self.sms_notifier)

    def add_slot(self, slot: ParkingSlot):
        self.slots.append(slot)
        self.notifier.notify("PARKING_UPDATE", f"Slot {slot.slot_id} added. Type: {slot.slot_type.value}")

    def find_available_slot(self, vehicle_type: VehicleType) -> Optional[ParkingSlot]:
        for slot in self.slots:
            if slot.slot_type == vehicle_type and slot.is_available():
                return slot
        return None
    
    def park_vehicle(self, vehicle: Vehicle) -> Optional[str]:
        slot = self.find_available_slot(vehicle.vehicle_type)
        if not slot:
            self.notifier.notify("PARKING_FULL", f"No available slots for {vehicle.vehicle_type.value}")
            return None
        command = ParkCommand(slot, vehicle, self.notifier)
        if command.execute():
            self.active_vehicles[vehicle.license_plate] = slot
            self.command_history.append(command)
            return slot.slot_id
        return None
    
    def unpark_vehicle(self, license_plate: str) -> Optional[float]:
        if license_plate not in self.active_vehicles:
            return None
        slot = self.active_vehicles[license_plate]
        vehicle = slot.vehicle
        command = UnparkCommand(slot, self.notifier)
        if command.execute():
    
    def unpark_vehicle(self, license_plate: str) -> Optional[float]:
        if license_plate not in self.active_vehicles:
            return None
        slot = self.active_vehicles[license_plate]
        vehicle = slot.vehicle
        command = UnparkCommand(slot, self.notifier)
        if command.execute():
            duration = datetime.now() - slot.parked_at if slot.parked_at else timedelta(0)
            pricing_strategy = self.pricing_strategies[vehicle.vehicle_type]
            base_cost = pricing_strategy.calculate_cost(duration)
            premium_service = BasicParking()
            additional_cost = premium_service.get_additional_cost(base_cost)

class Command(ABC):
    @abstractmethod
    def execute(self) -> bool:
        pass

    @abstractmethod
    def undo(self) -> bool:
        pass


class ParkCommand(Command):
    def __init__(self, slot: ParkingSlot, vehicle: Vehicle, notifier: ParkingEventNotifier):
        self.slot = slot
        self.vehicle = vehicle
        self.notifier = notifier
        self.executed = False
    
    def execute(self) -> bool:
        if self.slot.park_vehicle(self.vehicle):
            self.executed = True
            self.notifier.notify("VEHICLE_PARKED", f"Vehicle {self.vehicle.license_plate} parked in slot {self.slot.slot_id}")
            return True
        return False


class UnparkCommand(Command):
    def __init__(self, slot: ParkingSlot, notifier: ParkingEventNotifier):
        self.slot = slot
        self.notifier = notifier
        self.vehicle: Optional[Vehicle] = None
        self.executed = False
    
    def execute(self) -> bool:
        self.vehicle = self.slot.unpark_vehicle()
        if self.vehicle:
            self.executed = True
            self.notifier.notify("VEHICLE_UNPARKED", f"Vehicle {self.vehicle.license_plate} unparked from slot {self.slot.slot_id}")
            return True
