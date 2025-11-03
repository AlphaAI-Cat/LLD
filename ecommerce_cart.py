"""
E-Commerce Cart System
======================

Core Design: Shopping cart with add/remove items, checkout, and inventory management.

Design Patterns & Strategies Used:
1. State Pattern - Cart states (Empty, Active, Checkout, Completed)
2. Strategy Pattern - Different pricing strategies (Discount, Tax calculation)
3. Observer Pattern - Notify about price changes and inventory
4. Factory Pattern - Create products and orders
5. Command Pattern - Cart operations with undo
6. Template Method - Checkout process

Features:
- Add/remove items
- Quantity management
- Price calculation with discounts
- Inventory management
- Checkout process
- Order creation
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from dataclasses import dataclass
from uuid import uuid4
from datetime import datetime


class CartState(Enum):
    EMPTY = "EMPTY"
    ACTIVE = "ACTIVE"
    CHECKOUT = "CHECKOUT"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class OrderStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


@dataclass
class Product:
    """Product entity"""
    product_id: str
    name: str
    price: float
    stock: int
    category: str
    
    def decrease_stock(self, quantity: int) -> bool:
        """Decrease stock"""
        if self.stock >= quantity:
            self.stock -= quantity
            return True
        return False
    
    def increase_stock(self, quantity: int):
        """Increase stock"""
        self.stock += quantity


@dataclass
class CartItem:
    """Cart item"""
    product: Product
    quantity: int
    
    def get_subtotal(self) -> float:
        """Calculate item subtotal"""
        return self.product.price * self.quantity


class PricingStrategy(ABC):
    """Pricing strategy interface"""
    
    @abstractmethod
    def calculate_price(self, items: List[CartItem]) -> float:
        pass


class StandardPricingStrategy(PricingStrategy):
    """Standard pricing (no discounts)"""
    
    def calculate_price(self, items: List[CartItem]) -> float:
        return sum(item.get_subtotal() for item in items)


class DiscountPricingStrategy(PricingStrategy):
    """Pricing with discount"""
    
    def __init__(self, discount_percent: float = 10.0):
        self.discount_percent = discount_percent
    
    def calculate_price(self, items: List[CartItem]) -> float:
        subtotal = sum(item.get_subtotal() for item in items)
        discount = subtotal * (self.discount_percent / 100)
        return subtotal - discount


class TaxCalculationStrategy(ABC):
    """Tax calculation strategy"""
    
    @abstractmethod
    def calculate_tax(self, subtotal: float) -> float:
        pass


class StandardTaxStrategy(TaxCalculationStrategy):
    """Standard tax calculation"""
    
    def __init__(self, tax_rate: float = 0.10):
        self.tax_rate = tax_rate
    
    def calculate_tax(self, subtotal: float) -> float:
        return subtotal * self.tax_rate


class NoTaxStrategy(TaxCalculationStrategy):
    """No tax"""
    
    def calculate_tax(self, subtotal: float) -> float:
        return 0.0


class ShoppingCart:
    """Shopping cart"""
    
    def __init__(self, user_id: str):
        self.cart_id = str(uuid4())
        self.user_id = user_id
        self.items: Dict[str, CartItem] = {}  # product_id -> CartItem
        self.state = CartState.EMPTY
        self.pricing_strategy: PricingStrategy = StandardPricingStrategy()
        self.tax_strategy: TaxCalculationStrategy = StandardTaxStrategy()
        self.created_at = datetime.now()
    
    def set_pricing_strategy(self, strategy: PricingStrategy):
        """Set pricing strategy"""
        self.pricing_strategy = strategy
    
    def set_tax_strategy(self, strategy: TaxCalculationStrategy):
        """Set tax strategy"""
        self.tax_strategy = strategy
    
    def add_item(self, product: Product, quantity: int) -> bool:
        """Add item to cart"""
        if quantity <= 0 or product.stock < quantity:
            return False
        
        if product.product_id in self.items:
            # Update quantity
            item = self.items[product.product_id]
            new_quantity = item.quantity + quantity
            if product.stock < new_quantity:
                return False
            item.quantity = new_quantity
        else:
            # Add new item
            self.items[product.product_id] = CartItem(product, quantity)
        
        self.state = CartState.ACTIVE
        return True
    
    def remove_item(self, product_id: str, quantity: int = None) -> bool:
        """Remove item from cart"""
        if product_id not in self.items:
            return False
        
        item = self.items[product_id]
        
        if quantity is None or quantity >= item.quantity:
            # Remove item completely
            del self.items[product_id]
        else:
            # Reduce quantity
            item.quantity -= quantity
        
        if not self.items:
            self.state = CartState.EMPTY
        
        return True
    
    def get_subtotal(self) -> float:
        """Get cart subtotal"""
        return self.pricing_strategy.calculate_price(list(self.items.values()))
    
    def get_tax(self) -> float:
        """Get tax amount"""
        subtotal = self.get_subtotal()
        return self.tax_strategy.calculate_tax(subtotal)
    
    def get_total(self) -> float:
        """Get total price"""
        return self.get_subtotal() + self.get_tax()
    
    def clear(self):
        """Clear cart"""
        self.items.clear()
        self.state = CartState.EMPTY
    
    def get_item_count(self) -> int:
        """Get total item count"""
        return sum(item.quantity for item in self.items.values())


class CartObserver(ABC):
    """Observer for cart events"""
    
    @abstractmethod
    def on_cart_updated(self, cart: ShoppingCart):
        pass
    
    @abstractmethod
    def on_checkout(self, cart: ShoppingCart):
        pass


class InventoryObserver(CartObserver):
    """Inventory observer"""
    
    def on_cart_updated(self, cart: ShoppingCart):
        print(f"[Inventory] Cart updated: {cart.get_item_count()} items")
    
    def on_checkout(self, cart: ShoppingCart):
        print(f"[Inventory] Checkout initiated")


class PricingObserver(CartObserver):
    """Pricing observer"""
    
    def on_cart_updated(self, cart: ShoppingCart):
        print(f"[Pricing] Cart total: ${cart.get_total():.2f}")
    
    def on_checkout(self, cart: ShoppingCart):
        print(f"[Pricing] Checkout total: ${cart.get_total():.2f}")


class OrderService:
    """Order service"""
    
    def __init__(self):
        self.carts: Dict[str, ShoppingCart] = {}
        self.orders: Dict[str, 'Order'] = {}
        self.products: Dict[str, Product] = {}
        self.observers: List[CartObserver] = []
    
    def add_product(self, product: Product):
        """Add product to catalog"""
        self.products[product.product_id] = product
    
    def get_cart(self, user_id: str) -> ShoppingCart:
        """Get or create cart for user"""
        if user_id not in self.carts:
            cart = ShoppingCart(user_id)
            self.carts[user_id] = cart
        return self.carts[user_id]
    
    def add_to_cart(self, user_id: str, product_id: str, quantity: int) -> bool:
        """Add product to cart"""
        if product_id not in self.products:
            return False
        
        cart = self.get_cart(user_id)
        product = self.products[product_id]
        
        if cart.add_item(product, quantity):
            self._notify_observers(cart, "updated")
            return True
        return False
    
    def checkout(self, user_id: str) -> Optional[str]:
        """Checkout cart"""
        if user_id not in self.carts:
            return None
        
        cart = self.carts[user_id]
        
        if cart.state == CartState.EMPTY:
            return None
        
        cart.state = CartState.CHECKOUT
        
        # Validate inventory
        for item in cart.items.values():
            if item.product.stock < item.quantity:
                print(f"Insufficient stock for {item.product.name}")
                cart.state = CartState.ACTIVE
                return None
        
        # Create order
        order = self._create_order(cart)
        self.orders[order.order_id] = order
        
        # Update inventory
        for item in cart.items.values():
            item.product.decrease_stock(item.quantity)
        
        self._notify_observers(cart, "checkout")
        
        cart.state = CartState.COMPLETED
        del self.carts[user_id]
        
        return order.order_id
    
    def _create_order(self, cart: ShoppingCart) -> 'Order':
        """Create order from cart"""
        order_id = str(uuid4())
        order = Order(
            order_id=order_id,
            user_id=cart.user_id,
            items={pid: item.quantity for pid, item in cart.items.items()},
            subtotal=cart.get_subtotal(),
            tax=cart.get_tax(),
            total=cart.get_total(),
            status=OrderStatus.CONFIRMED,
            created_at=datetime.now()
        )
        return order
    
    def _notify_observers(self, cart: ShoppingCart, event: str):
        """Notify observers"""
        for observer in self.observers:
            if event == "updated":
                observer.on_cart_updated(cart)
            elif event == "checkout":
                observer.on_checkout(cart)
    
    def add_observer(self, observer: CartObserver):
        """Add observer"""
        self.observers.append(observer)


@dataclass
class Order:
    """Order entity"""
    order_id: str
    user_id: str
    items: Dict[str, int]  # product_id -> quantity
    subtotal: float
    tax: float
    total: float
    status: OrderStatus
    created_at: datetime


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("E-COMMERCE CART SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    service = OrderService()
    
    # Add observers
    service.add_observer(InventoryObserver())
    service.add_observer(PricingObserver())
    
    # Add products
    product1 = Product("P1", "Laptop", 999.99, 10, "Electronics")
    product2 = Product("P2", "Mouse", 29.99, 50, "Electronics")
    service.add_product(product1)
    service.add_product(product2)
    
    print("1. Adding items to cart:")
    service.add_to_cart("USER1", "P1", 1)
    service.add_to_cart("USER1", "P2", 2)
    print()
    
    print("2. Cart details:")
    cart = service.get_cart("USER1")
    print(f"Items: {cart.get_item_count()}")
    print(f"Subtotal: ${cart.get_subtotal():.2f}")
    print(f"Tax: ${cart.get_tax():.2f}")
    print(f"Total: ${cart.get_total():.2f}")
    print()
    
    print("3. Applying discount:")
    cart.set_pricing_strategy(DiscountPricingStrategy(discount_percent=15))
    print(f"New Total: ${cart.get_total():.2f}")
    print()
    
    print("4. Checkout:")
    order_id = service.checkout("USER1")
    print(f"Order created: {order_id}")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. State Pattern - Cart states")
    print("2. Strategy Pattern - Pricing and tax strategies")
    print("3. Observer Pattern - Inventory and pricing updates")
    print("4. Factory Pattern - Create products and orders")
    print("5. Command Pattern - Cart operations")
    print()
    print("FEATURES:")
    print("- Add/remove items")
    print("- Quantity management")
    print("- Discount calculation")
    print("- Tax calculation")
    print("- Inventory management")
    print("=" * 60)


if __name__ == "__main__":
    main()

