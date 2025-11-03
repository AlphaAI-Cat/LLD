"""
Elevator System
===============

Core Design: Elevator control system with multiple lifts and floors.

Design Patterns & Strategies Used:
1. State Pattern - Elevator states (Idle, Moving Up, Moving Down, Maintenance)
2. Strategy Pattern - Scheduling algorithms (SCAN, LOOK, FCFS)
3. Command Pattern - Floor request commands
4. Observer Pattern - Notify floors about elevator arrival
5. Singleton Pattern - Elevator controller
6. Priority Queue Pattern - For request prioritization

Scheduling Algorithms:
- SCAN: Elevator moves in one direction until end, then reverses
- LOOK: Similar to SCAN but reverses when no requests ahead
- FCFS: First Come First Served (simple but inefficient)

Concurrent Request Handling:
- Priority queue for requests
- Direction-based prioritization
- Nearest floor selection when idle
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Set
from dataclasses import dataclass
from queue import PriorityQueue
from threading import Lock, Thread
import time


class ElevatorState(Enum):
    IDLE = "IDLE"
    MOVING_UP = "MOVING_UP"
    MOVING_DOWN = "MOVING_DOWN"
    MAINTENANCE = "MAINTENANCE"
    DOOR_OPEN = "DOOR_OPEN"


class Direction(Enum):
    UP = 1
    DOWN = -1
    NONE = 0


# ==================== STATE PATTERN ====================
# Elevator state management

class ElevatorStateContext:
    """State interface"""
    
    @abstractmethod
    def handle_request(self, elevator: 'Elevator', floor: int) -> bool:
        pass
    
    @abstractmethod
    def move(self, elevator: 'Elevator') -> bool:
        pass


class IdleState(ElevatorStateContext):
    """Idle state - elevator waiting for requests"""
    
    def handle_request(self, elevator: 'Elevator', floor: int) -> bool:
        if floor != elevator.current_floor:
            if floor > elevator.current_floor:
                elevator.state = ElevatorState.MOVING_UP
                elevator.direction = Direction.UP
            else:
                elevator.state = ElevatorState.MOVING_DOWN
                elevator.direction = Direction.DOWN
            return True
        return False
    
    def move(self, elevator: 'Elevator') -> bool:
        return False


class MovingUpState(ElevatorStateContext):
    """Moving up state"""
    
    def handle_request(self, elevator: 'Elevator', floor: int) -> bool:
        # Add to request queue if valid
        if floor > elevator.current_floor:
            elevator.add_request(floor)
            return True
        return False
    
    def move(self, elevator: 'Elevator') -> bool:
        next_floor = elevator.get_next_floor()
        if next_floor is not None:
            elevator.current_floor = next_floor
            if elevator.current_floor in elevator.requested_floors:
                elevator.stop_at_floor()
            return True
        else:
            # No more requests, go idle or change direction
            if elevator.has_down_requests():
                elevator.state = ElevatorState.MOVING_DOWN
                elevator.direction = Direction.DOWN
            else:
                elevator.state = ElevatorState.IDLE
                elevator.direction = Direction.NONE
            return True


class MovingDownState(ElevatorStateContext):
    """Moving down state"""
    
    def handle_request(self, elevator: 'Elevator', floor: int) -> bool:
        if floor < elevator.current_floor:
            elevator.add_request(floor)
            return True
        return False
    
    def move(self, elevator: 'Elevator') -> bool:
        next_floor = elevator.get_next_floor()
        if next_floor is not None:
            elevator.current_floor = next_floor
            if elevator.current_floor in elevator.requested_floors:
                elevator.stop_at_floor()
            return True
        else:
            # No more requests, go idle or change direction
            if elevator.has_up_requests():
                elevator.state = ElevatorState.MOVING_UP
                elevator.direction = Direction.UP
            else:
                elevator.state = ElevatorState.IDLE
                elevator.direction = Direction.NONE
            return True


# ==================== STRATEGY PATTERN ====================
# Different scheduling algorithms

class SchedulingStrategy(ABC):
    """Scheduling strategy interface"""
    
    @abstractmethod
    def select_elevator(self, floor: int, direction: Direction, 
                       elevators: List['Elevator']) -> Optional['Elevator']:
        pass


class SCANStrategy(SchedulingStrategy):
    """SCAN algorithm - elevator moves in one direction until end"""
    
    def select_elevator(self, floor: int, direction: Direction, 
                       elevators: List['Elevator']) -> Optional['Elevator']:
        best_elevator = None
        min_distance = float('inf')
        
        for elevator in elevators:
            if elevator.state == ElevatorState.MAINTENANCE:
                continue
            
            # Calculate distance based on current direction
            distance = abs(elevator.current_floor - floor)
            
            # Prefer elevator moving in same direction
            if (elevator.direction == direction and 
                ((direction == Direction.UP and elevator.current_floor < floor) or
                 (direction == Direction.DOWN and elevator.current_floor > floor))):
                distance *= 0.5  # Prefer same direction
            
            if distance < min_distance:
                min_distance = distance
                best_elevator = elevator
        
        return best_elevator


class LOOKStrategy(SchedulingStrategy):
    """LOOK algorithm - reverses when no requests ahead"""
    
    def select_elevator(self, floor: int, direction: Direction, 
                       elevators: List['Elevator']) -> Optional['Elevator']:
        best_elevator = None
        min_distance = float('inf')
        
        for elevator in elevators:
            if elevator.state == ElevatorState.MAINTENANCE:
                continue
            
            # Calculate distance
            distance = abs(elevator.current_floor - floor)
            
            # Prefer idle or moving in same direction
            if (elevator.state == ElevatorState.IDLE or
                (elevator.direction == direction and 
                 ((direction == Direction.UP and elevator.current_floor <= floor) or
                  (direction == Direction.DOWN and elevator.current_floor >= floor)))):
                if elevator.state == ElevatorState.IDLE:
                    distance *= 0.3  # Strongly prefer idle
                else:
                    distance *= 0.7  # Prefer same direction
            
            if distance < min_distance:
                min_distance = distance
                best_elevator = elevator
        
        return best_elevator


class FCFSStrategy(SchedulingStrategy):
    """First Come First Served - simple but inefficient"""
    
    def select_elevator(self, floor: int, direction: Direction, 
                       elevators: List['Elevator']) -> Optional['Elevator']:
        # Select first available elevator
        for elevator in elevators:
            if elevator.state != ElevatorState.MAINTENANCE:
                return elevator
        return None


# ==================== COMMAND PATTERN ====================
# Floor request commands

class Command(ABC):
    """Command interface"""
    
    @abstractmethod
    def execute(self) -> bool:
        pass


@dataclass
class FloorRequest:
    """Floor request data"""
    floor: int
    direction: Direction
    timestamp: float


class RequestFloorCommand(Command):
    """Command to request elevator at floor"""
    
    def __init__(self, controller: 'ElevatorController', floor: int, direction: Direction):
        self.controller = controller
        self.floor = floor
        self.direction = direction
    
    def execute(self) -> bool:
        return self.controller.request_elevator(self.floor, self.direction)


# ==================== OBSERVER PATTERN ====================
# Notify floors about elevator arrival

class FloorObserver(ABC):
    """Observer interface"""
    
    @abstractmethod
    def elevator_arrived(self, elevator_id: int, floor: int):
        pass


class FloorDisplay(FloorObserver):
    """Floor display observer"""
    
    def __init__(self, floor: int):
        self.floor = floor
    
    def elevator_arrived(self, elevator_id: int, floor: int):
        if floor == self.floor:
            print(f"[Floor {self.floor} Display] Elevator {elevator_id} arrived!")


class Elevator:
    """Elevator with state management"""
    
    def __init__(self, elevator_id: int, min_floor: int, max_floor: int):
        self.elevator_id = elevator_id
        self.min_floor = min_floor
        self.max_floor = max_floor
        self.current_floor = min_floor
        self.state = ElevatorState.IDLE
        self.direction = Direction.NONE
        self.requested_floors: Set[int] = set()
        self.state_context: ElevatorStateContext = IdleState()
        self.lock = Lock()
        self.observers: List[FloorObserver] = []
    
    def add_observer(self, observer: FloorObserver):
        self.observers.append(observer)
    
    def add_request(self, floor: int):
        """Add floor request"""
        with self.lock:
            if self.min_floor <= floor <= self.max_floor:
                self.requested_floors.add(floor)
    
    def get_next_floor(self) -> Optional[int]:
        """Get next floor to visit based on direction"""
        with self.lock:
            if not self.requested_floors:
                return None
            
            if self.direction == Direction.UP:
                above_floors = [f for f in self.requested_floors if f > self.current_floor]
                return min(above_floors) if above_floors else None
            elif self.direction == Direction.DOWN:
                below_floors = [f for f in self.requested_floors if f < self.current_floor]
                return max(below_floors) if below_floors else None
            else:
                # Find nearest floor
                nearest = min(self.requested_floors, 
                            key=lambda x: abs(x - self.current_floor))
                return nearest
    
    def has_up_requests(self) -> bool:
        """Check if there are requests above current floor"""
        return any(f > self.current_floor for f in self.requested_floors)
    
    def has_down_requests(self) -> bool:
        """Check if there are requests below current floor"""
        return any(f < self.current_floor for f in self.requested_floors)
    
    def stop_at_floor(self):
        """Stop at current floor"""
        with self.lock:
            self.state = ElevatorState.DOOR_OPEN
            if self.current_floor in self.requested_floors:
                self.requested_floors.remove(self.current_floor)
            
            # Notify observers
            for observer in self.observers:
                observer.elevator_arrived(self.elevator_id, self.current_floor)
            
            # Simulate door open/close
            time.sleep(0.1)
            self._update_state()
    
    def _update_state(self):
        """Update state based on remaining requests"""
        if self.requested_floors:
            if self.direction == Direction.UP and self.has_up_requests():
                self.state = ElevatorState.MOVING_UP
                self.state_context = MovingUpState()
            elif self.direction == Direction.DOWN and self.has_down_requests():
                self.state = ElevatorState.MOVING_DOWN
                self.state_context = MovingDownState()
            elif self.has_up_requests():
                self.state = ElevatorState.MOVING_UP
                self.direction = Direction.UP
                self.state_context = MovingUpState()
            elif self.has_down_requests():
                self.state = ElevatorState.MOVING_DOWN
                self.direction = Direction.DOWN
                self.state_context = MovingDownState()
        else:
            self.state = ElevatorState.IDLE
            self.direction = Direction.NONE
            self.state_context = IdleState()
    
    def request_floor(self, floor: int) -> bool:
        """Request to go to floor"""
        return self.state_context.handle_request(self, floor)
    
    def move(self):
        """Move elevator one step"""
        if self.state in [ElevatorState.MOVING_UP, ElevatorState.MOVING_DOWN]:
            self.state_context.move(self)


# ==================== SINGLETON PATTERN ====================
# Elevator controller singleton

class ElevatorController:
    """Singleton elevator controller"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ElevatorController, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.elevators: List[Elevator] = []
        self.scheduling_strategy: SchedulingStrategy = LOOKStrategy()
        self.running = False
        self._initialized = True
    
    def add_elevator(self, elevator: Elevator):
        """Add elevator to system"""
        self.elevators.append(elevator)
    
    def set_scheduling_strategy(self, strategy: SchedulingStrategy):
        """Set scheduling strategy"""
        self.scheduling_strategy = strategy
    
    def request_elevator(self, floor: int, direction: Direction) -> bool:
        """Request elevator using scheduling strategy"""
        elevator = self.scheduling_strategy.select_elevator(
            floor, direction, self.elevators
        )
        
        if elevator:
            elevator.add_request(floor)
            # Set direction if idle
            if elevator.state == ElevatorState.IDLE:
                if floor > elevator.current_floor:
                    elevator.state = ElevatorState.MOVING_UP
                    elevator.direction = Direction.UP
                    elevator.state_context = MovingUpState()
                elif floor < elevator.current_floor:
                    elevator.state = ElevatorState.MOVING_DOWN
                    elevator.direction = Direction.DOWN
                    elevator.state_context = MovingDownState()
            return True
        return False
    
    def start(self):
        """Start elevator system"""
        self.running = True
        
        def run_elevators():
            while self.running:
                for elevator in self.elevators:
                    if elevator.state != ElevatorState.MAINTENANCE:
                        elevator.move()
                time.sleep(0.1)
        
        thread = Thread(target=run_elevators, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop elevator system"""
        self.running = False


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("ELEVATOR SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    # Create controller
    controller = ElevatorController()
    
    # Create elevators
    elevator1 = Elevator(1, 0, 10)
    elevator2 = Elevator(2, 0, 10)
    
    controller.add_elevator(elevator1)
    controller.add_elevator(elevator2)
    
    # Set scheduling strategy
    controller.set_scheduling_strategy(LOOKStrategy())
    
    # Start system
    controller.start()
    
    print("1. Requesting elevators:")
    controller.request_elevator(5, Direction.UP)
    controller.request_elevator(3, Direction.UP)
    time.sleep(0.5)
    
    print(f"Elevator 1: Floor {elevator1.current_floor}, State: {elevator1.state.value}")
    print(f"Elevator 2: Floor {elevator2.current_floor}, State: {elevator2.state.value}")
    print()
    
    print("2. Requesting from floor 7:")
    controller.request_elevator(7, Direction.DOWN)
    time.sleep(0.5)
    
    print(f"Elevator 1: Floor {elevator1.current_floor}, State: {elevator1.state.value}")
    print(f"Elevator 2: Floor {elevator2.current_floor}, State: {elevator2.state.value}")
    print()
    
    print("3. Testing SCAN strategy:")
    controller.set_scheduling_strategy(SCANStrategy())
    print("SCAN strategy set")
    print()
    
    controller.stop()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. State Pattern - Elevator states (Idle, Moving Up/Down)")
    print("2. Strategy Pattern - Scheduling algorithms (SCAN, LOOK, FCFS)")
    print("3. Command Pattern - Floor request commands")
    print("4. Observer Pattern - Floor arrival notifications")
    print("5. Singleton Pattern - Single elevator controller")
    print()
    print("SCHEDULING ALGORITHMS:")
    print("- SCAN: Moves in one direction until end")
    print("- LOOK: Reverses when no requests ahead")
    print("- FCFS: First Come First Served")
    print()
    print("CONCURRENT HANDLING:")
    print("- Priority queue for requests")
    print("- Thread-safe operations with locks")
    print("- Direction-based prioritization")
    print("=" * 60)


if __name__ == "__main__":
    main()

