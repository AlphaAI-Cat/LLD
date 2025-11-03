"""
Online Food Ordering System (Zomato/Swiggy-like)
================================================

Core Design: Order management, restaurant search, and delivery assignment.

Design Patterns & Strategies Used:
1. State Pattern - Order states (Placed, Confirmed, Preparing, Ready, Out for Delivery, Delivered, Cancelled)
2. Observer Pattern - Notify customer/restaurant/delivery partner about order updates
3. Strategy Pattern - Delivery assignment strategies (Nearest, Load balancing)
4. Factory Pattern - Create orders and deliveries
5. Command Pattern - Order operations with undo (cancellation)
6. Template Method - Order processing workflow

Features:
- Restaurant search and filtering
- Order lifecycle management
- Real-time order tracking
- Delivery partner assignment
- Payment processing
- Order cancellation and refunds
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime
from dataclasses import dataclass
from uuid import uuid4
import math


class OrderState(Enum):
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class PaymentStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


# ==================== STATE PATTERN ====================

@dataclass
class Location:
    latitude: float
    longitude: float
    
    def distance_to(self, other: 'Location') -> float:
        """Calculate distance in km (Haversine formula)"""
        R = 6371  # Earth radius in km
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c


class Order:
    """Order with state management"""
    
    def __init__(self, order_id: str, customer_id: str, restaurant_id: str,
                 items: Dict[str, int], customer_location: Location):
        self.order_id = order_id
        self.customer_id = customer_id
        self.restaurant_id = restaurant_id
        self.items = items  # item_name -> quantity
        self.customer_location = customer_location
        self.state = OrderState.PLACED
        self.payment_status = PaymentStatus.PENDING
        self.created_at = datetime.now()
        self.delivery_partner_id: Optional[str] = None
        self.current_location: Optional[Location] = None
    
    def update_state(self, new_state: OrderState):
        """Update order state"""
        valid_transitions = {
            OrderState.PLACED: [OrderState.CONFIRMED, OrderState.CANCELLED],
            OrderState.CONFIRMED: [OrderState.PREPARING, OrderState.CANCELLED],
            OrderState.PREPARING: [OrderState.READY, OrderState.CANCELLED],
            OrderState.READY: [OrderState.OUT_FOR_DELIVERY],
            OrderState.OUT_FOR_DELIVERY: [OrderState.DELIVERED],
            OrderState.DELIVERED: [],
            OrderState.CANCELLED: []
        }
        
        if new_state in valid_transitions.get(self.state, []):
            self.state = new_state
            return True
        return False
    
    def assign_delivery_partner(self, partner_id: str):
        """Assign delivery partner"""
        self.delivery_partner_id = partner_id
    
    def update_location(self, location: Location):
        """Update current order location (for tracking)"""
        self.current_location = location


# ==================== OBSERVER PATTERN ====================

class OrderObserver(ABC):
    """Observer interface"""
    
    @abstractmethod
    def update(self, order: Order, event_type: str, message: str):
        pass


class CustomerNotifier(OrderObserver):
    """Notify customer"""
    
    def update(self, order: Order, event_type: str, message: str):
        print(f"[Customer {order.customer_id}] {message}")


class RestaurantNotifier(OrderObserver):
    """Notify restaurant"""
    
    def update(self, order: Order, event_type: str, message: str):
        print(f"[Restaurant {order.restaurant_id}] {message}")


class DeliveryNotifier(OrderObserver):
    """Notify delivery partner"""
    
    def update(self, order: Order, event_type: str, message: str):
        if order.delivery_partner_id:
            print(f"[Delivery Partner {order.delivery_partner_id}] {message}")


class OrderNotifier:
    """Subject for Observer Pattern"""
    
    def __init__(self):
        self.observers: List[OrderObserver] = []
    
    def attach(self, observer: OrderObserver):
        self.observers.append(observer)
    
    def notify(self, order: Order, event_type: str, message: str):
        for observer in self.observers:
            observer.update(order, event_type, message)


# ==================== STRATEGY PATTERN ====================
# Delivery assignment strategies

class DeliveryAssignmentStrategy(ABC):
    """Delivery assignment strategy interface"""
    
    @abstractmethod
    def assign_delivery_partner(self, order: Order, 
                                available_partners: List['DeliveryPartner']) -> Optional['DeliveryPartner']:
        pass


class NearestPartnerStrategy(DeliveryAssignmentStrategy):
    """Assign nearest available delivery partner"""
    
    def assign_delivery_partner(self, order: Order, 
                                available_partners: List['DeliveryPartner']) -> Optional['DeliveryPartner']:
        if not available_partners:
            return None
        
        restaurant = DeliveryService.instance.get_restaurant(order.restaurant_id)
        if not restaurant:
            return None
        
        nearest = None
        min_distance = float('inf')
        
        for partner in available_partners:
            if partner.is_available():
                distance = partner.location.distance_to(restaurant.location)
                if distance < min_distance:
                    min_distance = distance
                    nearest = partner
        
        return nearest


class LoadBalancingStrategy(DeliveryAssignmentStrategy):
    """Assign partner based on current load"""
    
    def assign_delivery_partner(self, order: Order, 
                                available_partners: List['DeliveryPartner']) -> Optional['DeliveryPartner']:
        if not available_partners:
            return None
        
        available = [p for p in available_partners if p.is_available()]
        if not available:
            return None
        
        # Select partner with least active deliveries
        return min(available, key=lambda p: p.get_active_deliveries())


# ==================== FACTORY PATTERN ====================

class DeliveryPartner:
    """Delivery partner"""
    
    def __init__(self, partner_id: str, name: str, location: Location):
        self.partner_id = partner_id
        self.name = name
        self.location = location
        self.active_orders: List[str] = []
        self.is_active = True
    
    def assign_order(self, order_id: str):
        """Assign order to partner"""
        self.active_orders.append(order_id)
    
    def complete_order(self, order_id: str):
        """Complete order"""
        if order_id in self.active_orders:
            self.active_orders.remove(order_id)
    
    def is_available(self) -> bool:
        """Check if partner is available"""
        return self.is_active and len(self.active_orders) < 5
    
    def get_active_deliveries(self) -> int:
        """Get number of active deliveries"""
        return len(self.active_orders)


class Restaurant:
    """Restaurant"""
    
    def __init__(self, restaurant_id: str, name: str, location: Location, cuisine: str):
        self.restaurant_id = restaurant_id
        self.name = name
        self.location = location
        self.cuisine = cuisine
        self.menu: Dict[str, float] = {}  # item -> price
        self.is_active = True
    
    def add_menu_item(self, item: str, price: float):
        """Add menu item"""
        self.menu[item] = price


class OrderFactory:
    """Factory for creating orders"""
    
    @staticmethod
    def create_order(customer_id: str, restaurant_id: str,
                    items: Dict[str, int], customer_location: Location) -> Order:
        """Create new order"""
        order_id = str(uuid4())
        return Order(order_id, customer_id, restaurant_id, items, customer_location)


# ==================== COMMAND PATTERN ====================

class OrderCommand(ABC):
    """Command interface"""
    
    @abstractmethod
    def execute(self) -> bool:
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        pass


class PlaceOrderCommand(OrderCommand):
    """Command to place order"""
    
    def __init__(self, service: 'OrderService', customer_id: str, restaurant_id: str,
                 items: Dict[str, int], location: Location):
        self.service = service
        self.customer_id = customer_id
        self.restaurant_id = restaurant_id
        self.items = items
        self.location = location
        self.order: Optional[Order] = None
    
    def execute(self) -> bool:
        self.order = self.service.place_order(
            self.customer_id, self.restaurant_id, self.items, self.location
        )
        return self.order is not None
    
    def undo(self) -> bool:
        if self.order:
            return self.service.cancel_order(self.order.order_id)
        return False


# ==================== MAIN SERVICE ====================

class OrderService:
    """Main order service"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.restaurants: Dict[str, Restaurant] = {}
        self.delivery_partners: Dict[str, DeliveryPartner] = {}
        self.notifier = OrderNotifier()
        self.delivery_strategy: DeliveryAssignmentStrategy = NearestPartnerStrategy()
        
        # Attach observers
        self.notifier.attach(CustomerNotifier())
        self.notifier.attach(RestaurantNotifier())
        self.notifier.attach(DeliveryNotifier())
    
    def add_restaurant(self, restaurant: Restaurant):
        """Add restaurant"""
        self.restaurants[restaurant.restaurant_id] = restaurant
    
    def add_delivery_partner(self, partner: DeliveryPartner):
        """Add delivery partner"""
        self.delivery_partners[partner.partner_id] = partner
    
    def set_delivery_strategy(self, strategy: DeliveryAssignmentStrategy):
        """Set delivery assignment strategy"""
        self.delivery_strategy = strategy
    
    def place_order(self, customer_id: str, restaurant_id: str,
                   items: Dict[str, int], location: Location) -> Optional[Order]:
        """Place order"""
        if restaurant_id not in self.restaurants:
            return None
        
        restaurant = self.restaurants[restaurant_id]
        
        # Create order
        order = OrderFactory.create_order(customer_id, restaurant_id, items, location)
        
        # Calculate total
        total = sum(restaurant.menu.get(item, 0) * qty for item, qty in items.items())
        
        # Process payment (simulated)
        order.payment_status = PaymentStatus.COMPLETED
        
        # Update state
        order.update_state(OrderState.CONFIRMED)
        
        self.orders[order.order_id] = order
        
        self.notifier.notify(order, "ORDER_PLACED", f"Order placed: ${total:.2f}")
        
        # Auto-confirm and start preparation
        self._process_order(order)
        
        return order
    
    def _process_order(self, order: Order):
        """Process order workflow"""
        # Confirm
        order.update_state(OrderState.CONFIRMED)
        self.notifier.notify(order, "ORDER_CONFIRMED", "Order confirmed by restaurant")
        
        # Start preparing
        order.update_state(OrderState.PREPARING)
        self.notifier.notify(order, "PREPARING", "Restaurant started preparing")
        
        # When ready, assign delivery partner
        # In real system, this would be triggered by restaurant
        self._assign_delivery(order)
    
    def _assign_delivery(self, order: Order):
        """Assign delivery partner"""
        available = list(self.delivery_partners.values())
        partner = self.delivery_strategy.assign_delivery_partner(order, available)
        
        if partner:
            order.assign_delivery_partner(partner.partner_id)
            partner.assign_order(order.order_id)
            order.update_state(OrderState.READY)
            order.update_state(OrderState.OUT_FOR_DELIVERY)
            self.notifier.notify(order, "ASSIGNED", 
                               f"Assigned to delivery partner {partner.partner_id}")
        else:
            self.notifier.notify(order, "NO_PARTNER", "No delivery partner available")
    
    def update_order_state(self, order_id: str, new_state: OrderState):
        """Update order state"""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.update_state(new_state):
                self.notifier.notify(order, "STATE_CHANGED", 
                                   f"Order state: {new_state.value}")
                
                if new_state == OrderState.DELIVERED:
                    if order.delivery_partner_id:
                        partner = self.delivery_partners.get(order.delivery_partner_id)
                        if partner:
                            partner.complete_order(order_id)
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        if order.state in [OrderState.DELIVERED, OrderState.CANCELLED]:
            return False
        
        order.update_state(OrderState.CANCELLED)
        order.payment_status = PaymentStatus.REFUNDED
        
        if order.delivery_partner_id:
            partner = self.delivery_partners.get(order.delivery_partner_id)
            if partner:
                partner.complete_order(order_id)
        
        self.notifier.notify(order, "CANCELLED", "Order cancelled and refunded")
        return True
    
    def search_restaurants(self, location: Location, cuisine: Optional[str] = None,
                         max_distance: float = 10.0) -> List[Restaurant]:
        """Search restaurants"""
        results = []
        for restaurant in self.restaurants.values():
            if not restaurant.is_active:
                continue
            
            distance = location.distance_to(restaurant.location)
            if distance <= max_distance:
                if cuisine is None or restaurant.cuisine == cuisine:
                    results.append(restaurant)
        
        # Sort by distance
        results.sort(key=lambda r: location.distance_to(r.location))
        return results


# Singleton for delivery service
class DeliveryService:
    instance = None
    
    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance
    
    def __init__(self):
        self.restaurants: Dict[str, Restaurant] = {}
    
    def get_restaurant(self, restaurant_id: str) -> Optional[Restaurant]:
        return self.restaurants.get(restaurant_id)


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("ONLINE FOOD ORDERING SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    service = OrderService()
    
    # Add restaurant
    restaurant = Restaurant("R1", "Pizza Palace", Location(28.6139, 77.2090), "Italian")
    restaurant.add_menu_item("Pizza", 300.0)
    restaurant.add_menu_item("Pasta", 250.0)
    service.add_restaurant(restaurant)
    DeliveryService.instance.restaurants["R1"] = restaurant
    
    # Add delivery partners
    partner1 = DeliveryPartner("DP1", "John", Location(28.6140, 77.2091))
    partner2 = DeliveryPartner("DP2", "Jane", Location(28.6150, 77.2100))
    service.add_delivery_partner(partner1)
    service.add_delivery_partner(partner2)
    
    # Place order
    print("1. Placing order:")
    customer_location = Location(28.6200, 77.2200)
    order = service.place_order("C1", "R1", {"Pizza": 2, "Pasta": 1}, customer_location)
    if order:
        print(f"Order placed: {order.order_id}")
    print()
    
    # Update order state
    print("2. Order delivered:")
    service.update_order_state(order.order_id, OrderState.DELIVERED)
    print()
    
    # Search restaurants
    print("3. Searching restaurants:")
    results = service.search_restaurants(customer_location, max_distance=5.0)
    for r in results:
        print(f"Found: {r.name} ({r.cuisine})")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. State Pattern - Order lifecycle states")
    print("2. Observer Pattern - Notify customer/restaurant/delivery")
    print("3. Strategy Pattern - Delivery assignment (Nearest, Load balancing)")
    print("4. Factory Pattern - Order creation")
    print("5. Command Pattern - Order operations with undo")
    print()
    print("FEATURES:")
    print("- Restaurant search and filtering")
    print("- Real-time order tracking")
    print("- Delivery partner assignment")
    print("- Order cancellation and refunds")
    print("=" * 60)


if __name__ == "__main__":
    main()

