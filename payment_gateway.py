"""
Payment Gateway
===============

Core Design: Payment processing system with multiple payment methods and transaction handling.

Design Patterns & Strategies Used:
1. Strategy Pattern - Different payment methods (Credit Card, Debit Card, UPI, Wallet)
2. State Pattern - Transaction states
3. Chain of Responsibility - Payment validation chain
4. Factory Pattern - Create payment processors
5. Observer Pattern - Transaction notifications
6. Template Method - Payment processing workflow
7. Circuit Breaker - Handle payment service failures

Features:
- Multiple payment methods
- Transaction processing
- Refund handling
- Payment gateway integration
- Fraud detection
- Transaction logging
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict
from datetime import datetime
from dataclasses import dataclass
from uuid import uuid4
import random


class PaymentMethod(Enum):
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    UPI = "UPI"
    WALLET = "WALLET"
    NET_BANKING = "NET_BANKING"


class TransactionStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"


@dataclass
class PaymentDetails:
    """Payment details"""
    payment_method: PaymentMethod
    amount: float
    currency: str = "USD"
    card_number: Optional[str] = None
    cvv: Optional[str] = None
    expiry_date: Optional[str] = None
    upi_id: Optional[str] = None
    wallet_id: Optional[str] = None
    account_number: Optional[str] = None


@dataclass
class Transaction:
    """Transaction entity"""
    transaction_id: str
    order_id: str
    payment_method: PaymentMethod
    amount: float
    status: TransactionStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    gateway_response: Optional[Dict] = None


class PaymentProcessor(ABC):
    """Payment processor strategy interface"""
    
    @abstractmethod
    def process_payment(self, payment_details: PaymentDetails) -> bool:
        pass
    
    @abstractmethod
    def process_refund(self, transaction_id: str, amount: float) -> bool:
        pass
    
    @abstractmethod
    def get_payment_method(self) -> PaymentMethod:
        pass


class CreditCardProcessor(PaymentProcessor):
    """Credit card payment processor"""
    
    def process_payment(self, payment_details: PaymentDetails) -> bool:
        print(f"[CreditCard] Processing ${payment_details.amount} payment")
        # Simulate processing
        return random.random() > 0.1  # 90% success rate
    
    def process_refund(self, transaction_id: str, amount: float) -> bool:
        print(f"[CreditCard] Refunding ${amount} for transaction {transaction_id}")
        return True
    
    def get_payment_method(self) -> PaymentMethod:
        return PaymentMethod.CREDIT_CARD


class DebitCardProcessor(PaymentProcessor):
    """Debit card payment processor"""
    
    def process_payment(self, payment_details: PaymentDetails) -> bool:
        print(f"[DebitCard] Processing ${payment_details.amount} payment")
        return random.random() > 0.15
    
    def process_refund(self, transaction_id: str, amount: float) -> bool:
        print(f"[DebitCard] Refunding ${amount} for transaction {transaction_id}")
        return True
    
    def get_payment_method(self) -> PaymentMethod:
        return PaymentMethod.DEBIT_CARD


class UPIProcessor(PaymentProcessor):
    """UPI payment processor"""
    
    def process_payment(self, payment_details: PaymentDetails) -> bool:
        print(f"[UPI] Processing ${payment_details.amount} payment")
        return random.random() > 0.2
    
    def process_refund(self, transaction_id: str, amount: float) -> bool:
        print(f"[UPI] Refunding ${amount} for transaction {transaction_id}")
        return True
    
    def get_payment_method(self) -> PaymentMethod:
        return PaymentMethod.UPI


class WalletProcessor(PaymentProcessor):
    """Wallet payment processor"""
    
    def process_payment(self, payment_details: PaymentDetails) -> bool:
        print(f"[Wallet] Processing ${payment_details.amount} payment")
        return random.random() > 0.12
    
    def process_refund(self, transaction_id: str, amount: float) -> bool:
        print(f"[Wallet] Refunding ${amount} for transaction {transaction_id}")
        return True
    
    def get_payment_method(self) -> PaymentMethod:
        return PaymentMethod.WALLET


class PaymentValidator(ABC):
    """Chain of Responsibility - Payment validator"""
    
    def __init__(self):
        self.next_validator: Optional['PaymentValidator'] = None
    
    def set_next(self, validator: 'PaymentValidator'):
        self.next_validator = validator
        return validator
    
    def validate(self, payment_details: PaymentDetails) -> bool:
        """Validate payment"""
        if self.check(payment_details):
            if self.next_validator:
                return self.next_validator.validate(payment_details)
            return True
        return False
    
    @abstractmethod
    def check(self, payment_details: PaymentDetails) -> bool:
        pass


class AmountValidator(PaymentValidator):
    """Validate amount"""
    
    def check(self, payment_details: PaymentDetails) -> bool:
        if payment_details.amount <= 0:
            print("Invalid amount")
            return False
        if payment_details.amount > 100000:
            print("Amount exceeds limit")
            return False
        return True


class CardValidator(PaymentValidator):
    """Validate card details"""
    
    def check(self, payment_details: PaymentDetails) -> bool:
        if payment_details.payment_method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
            if not payment_details.card_number or not payment_details.cvv:
                print("Card details missing")
                return False
            if len(payment_details.card_number) != 16:
                print("Invalid card number")
                return False
        return True


class FraudDetector(PaymentValidator):
    """Fraud detection"""
    
    def check(self, payment_details: PaymentDetails) -> bool:
        # Simplified fraud detection
        if payment_details.amount > 10000:
            print("Large amount - additional verification required")
            # Would trigger additional checks in real system
        return True


class PaymentGateway:
    """Payment gateway service"""
    
    def __init__(self):
        self.processors: Dict[PaymentMethod, PaymentProcessor] = {
            PaymentMethod.CREDIT_CARD: CreditCardProcessor(),
            PaymentMethod.DEBIT_CARD: DebitCardProcessor(),
            PaymentMethod.UPI: UPIProcessor(),
            PaymentMethod.WALLET: WalletProcessor()
        }
        self.transactions: Dict[str, Transaction] = {}
        self.validator: Optional[PaymentValidator] = None
        self.observers: List = []
    
    def set_validator_chain(self, validator: PaymentValidator):
        """Set validation chain"""
        self.validator = validator
    
    def process_payment(self, order_id: str, payment_details: PaymentDetails) -> Optional[str]:
        """Process payment"""
        # Validate payment
        if self.validator and not self.validator.validate(payment_details):
            return None
        
        # Create transaction
        transaction_id = str(uuid4())
        transaction = Transaction(
            transaction_id=transaction_id,
            order_id=order_id,
            payment_method=payment_details.payment_method,
            amount=payment_details.amount,
            status=TransactionStatus.PROCESSING,
            created_at=datetime.now()
        )
        
        self.transactions[transaction_id] = transaction
        
        # Get processor
        processor = self.processors.get(payment_details.payment_method)
        if not processor:
            transaction.status = TransactionStatus.FAILED
            transaction.failure_reason = "Payment method not supported"
            return None
        
        # Process payment
        transaction.status = TransactionStatus.PROCESSING
        success = processor.process_payment(payment_details)
        
        if success:
            transaction.status = TransactionStatus.SUCCESS
            transaction.completed_at = datetime.now()
        else:
            transaction.status = TransactionStatus.FAILED
            transaction.failure_reason = "Payment processing failed"
        
        return transaction_id
    
    def refund_payment(self, transaction_id: str, amount: Optional[float] = None) -> bool:
        """Process refund"""
        if transaction_id not in self.transactions:
            return False
        
        transaction = self.transactions[transaction_id]
        
        if transaction.status != TransactionStatus.SUCCESS:
            print("Can only refund successful transactions")
            return False
        
        refund_amount = amount or transaction.amount
        
        # Get processor
        processor = self.processors.get(transaction.payment_method)
        if not processor:
            return False
        
        # Process refund
        success = processor.process_refund(transaction_id, refund_amount)
        
        if success:
            transaction.status = TransactionStatus.REFUNDED
            transaction.completed_at = datetime.now()
        
        return success
    
    def get_transaction_status(self, transaction_id: str) -> Optional[TransactionStatus]:
        """Get transaction status"""
        if transaction_id in self.transactions:
            return self.transactions[transaction_id].status
        return None


class PaymentProcessorFactory:
    """Factory for creating payment processors"""
    
    @staticmethod
    def create_processor(method: PaymentMethod) -> PaymentProcessor:
        """Create payment processor"""
        processors = {
            PaymentMethod.CREDIT_CARD: CreditCardProcessor(),
            PaymentMethod.DEBIT_CARD: DebitCardProcessor(),
            PaymentMethod.UPI: UPIProcessor(),
            PaymentMethod.WALLET: WalletProcessor()
        }
        return processors.get(method)


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("PAYMENT GATEWAY DEMONSTRATION")
    print("=" * 60)
    print()
    
    gateway = PaymentGateway()
    
    # Set up validation chain
    validator = AmountValidator()
    validator.set_next(CardValidator()).set_next(FraudDetector())
    gateway.set_validator_chain(validator)
    
    print("1. Processing credit card payment:")
    payment = PaymentDetails(
        payment_method=PaymentMethod.CREDIT_CARD,
        amount=100.0,
        card_number="1234567890123456",
        cvv="123",
        expiry_date="12/25"
    )
    txn_id = gateway.process_payment("ORDER1", payment)
    print(f"Transaction ID: {txn_id}")
    status = gateway.get_transaction_status(txn_id)
    print(f"Status: {status.value if status else 'Unknown'}")
    print()
    
    print("2. Processing UPI payment:")
    upi_payment = PaymentDetails(
        payment_method=PaymentMethod.UPI,
        amount=50.0,
        upi_id="user@upi"
    )
    txn_id2 = gateway.process_payment("ORDER2", upi_payment)
    print(f"Transaction ID: {txn_id2}")
    print()
    
    print("3. Processing refund:")
    if txn_id:
        gateway.refund_payment(txn_id)
        status = gateway.get_transaction_status(txn_id)
        print(f"Refund status: {status.value if status else 'Unknown'}")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. Strategy Pattern - Different payment methods")
    print("2. State Pattern - Transaction states")
    print("3. Chain of Responsibility - Payment validation")
    print("4. Factory Pattern - Create processors")
    print("5. Observer Pattern - Transaction notifications")
    print("6. Template Method - Payment workflow")
    print()
    print("FEATURES:")
    print("- Multiple payment methods")
    print("- Transaction processing")
    print("- Refund handling")
    print("- Validation chain")
    print("- Fraud detection")
    print("=" * 60)


if __name__ == "__main__":
    main()

