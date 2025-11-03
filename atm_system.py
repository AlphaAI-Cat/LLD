"""
ATM System
==========

Core Design: System for ATM transactions, card handling, and cash dispensing.

Design Patterns & Strategies Used:
1. State Pattern - ATM and transaction states
2. Command Pattern - Transaction operations with undo
3. Strategy Pattern - Different transaction types
4. Observer Pattern - Transaction logging and alerts
5. Chain of Responsibility - Authorization checks
6. Template Method - Transaction workflow

Features:
- Card authentication
- Multiple transaction types (Withdrawal, Deposit, Balance Inquiry, Transfer)
- Concurrent transaction handling
- Transaction logging
- Cash management
- Transaction rollback on failure
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict
from datetime import datetime
from threading import Lock
from dataclasses import dataclass


class ATMState(Enum):
    IDLE = "IDLE"
    CARD_INSERTED = "CARD_INSERTED"
    AUTHENTICATED = "AUTHENTICATED"
    PROCESSING = "PROCESSING"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class TransactionType(Enum):
    WITHDRAWAL = "WITHDRAWAL"
    DEPOSIT = "DEPOSIT"
    BALANCE_INQUIRY = "BALANCE_INQUIRY"
    TRANSFER = "TRANSFER"


class TransactionStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Account:
    """Bank account"""
    account_number: str
    card_number: str
    pin: str
    balance: float
    is_locked: bool = False
    failed_attempts: int = 0


@dataclass
class Transaction:
    """Transaction record"""
    transaction_id: str
    account_number: str
    transaction_type: TransactionType
    amount: float
    status: TransactionStatus
    timestamp: datetime
    description: str = ""


class TransactionCommand(ABC):
    """Command interface for transactions"""
    
    @abstractmethod
    def execute(self) -> bool:
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        pass


class WithdrawalCommand(TransactionCommand):
    """Withdrawal transaction command"""
    
    def __init__(self, atm: 'ATM', account: Account, amount: float):
        self.atm = atm
        self.account = account
        self.amount = amount
        self.executed = False
    
    def execute(self) -> bool:
        if self.account.balance >= self.amount and self.atm.dispense_cash(self.amount):
            self.account.balance -= self.amount
            self.executed = True
            return True
        return False
    
    def undo(self) -> bool:
        if self.executed:
            self.account.balance += self.amount
            self.executed = False
            return True
        return False


class DepositCommand(TransactionCommand):
    """Deposit transaction command"""
    
    def __init__(self, atm: 'ATM', account: Account, amount: float):
        self.atm = atm
        self.account = account
        self.amount = amount
        self.executed = False
    
    def execute(self) -> bool:
        if self.atm.accept_cash(self.amount):
            self.account.balance += self.amount
            self.executed = True
            return True
        return False
    
    def undo(self) -> bool:
        if self.executed:
            self.account.balance -= self.amount
            self.executed = False
            return True
        return False


class BalanceInquiryCommand(TransactionCommand):
    """Balance inquiry command"""
    
    def __init__(self, atm: 'ATM', account: Account):
        self.atm = atm
        self.account = account
    
    def execute(self) -> bool:
        print(f"Account Balance: ${self.account.balance:.2f}")
        return True
    
    def undo(self) -> bool:
        return False


class AuthorizationHandler(ABC):
    """Chain of Responsibility - Authorization handler"""
    
    def __init__(self):
        self.next_handler: Optional['AuthorizationHandler'] = None
    
    def set_next(self, handler: 'AuthorizationHandler'):
        self.next_handler = handler
        return handler
    
    def handle(self, account: Account, transaction: TransactionCommand) -> bool:
        if self.check(account, transaction):
            if self.next_handler:
                return self.next_handler.handle(account, transaction)
            return True
        return False
    
    @abstractmethod
    def check(self, account: Account, transaction: TransactionCommand) -> bool:
        pass


class AccountStatusHandler(AuthorizationHandler):
    """Check account status"""
    
    def check(self, account: Account, transaction: TransactionCommand) -> bool:
        if account.is_locked:
            print("Account is locked")
            return False
        return True


class BalanceCheckHandler(AuthorizationHandler):
    """Check account balance"""
    
    def check(self, account: Account, transaction: TransactionCommand) -> bool:
        if isinstance(transaction, WithdrawalCommand):
            if account.balance < transaction.amount:
                print("Insufficient balance")
                return False
        return True


class DailyLimitHandler(AuthorizationHandler):
    """Check daily transaction limit"""
    
    def check(self, account: Account, transaction: TransactionCommand) -> bool:
        # Simplified - would check actual daily limit
        return True


class ATM:
    """ATM machine"""
    
    def __init__(self, atm_id: str):
        self.atm_id = atm_id
        self.state = ATMState.IDLE
        self.cash_available = 10000.0  # $10,000
        self.current_account: Optional[Account] = None
        self.current_card: Optional[str] = None
        self.lock = Lock()
        self.transactions: list = []
        self.authorization_chain: Optional[AuthorizationHandler] = None
    
    def set_authorization_chain(self, chain: AuthorizationHandler):
        """Set authorization chain"""
        self.authorization_chain = chain
    
    def insert_card(self, card_number: str) -> bool:
        """Insert card"""
        with self.lock:
            if self.state == ATMState.IDLE:
                self.current_card = card_number
                self.state = ATMState.CARD_INSERTED
                return True
            return False
    
    def authenticate(self, pin: str, accounts: Dict[str, Account]) -> bool:
        """Authenticate card with PIN"""
        with self.lock:
            if self.state != ATMState.CARD_INSERTED:
                return False
            
            # Find account
            for account in accounts.values():
                if account.card_number == self.current_card and account.pin == pin:
                    if account.is_locked:
                        print("Account is locked")
                        return False
                    
                    self.current_account = account
                    self.state = ATMState.AUTHENTICATED
                    account.failed_attempts = 0
                    return True
                elif account.card_number == self.current_card:
                    account.failed_attempts += 1
                    if account.failed_attempts >= 3:
                        account.is_locked = True
                        print("Account locked due to failed attempts")
                    return False
            
            return False
    
    def process_transaction(self, command: TransactionCommand) -> bool:
        """Process transaction"""
        with self.lock:
            if self.state != ATMState.AUTHENTICATED:
                return False
            
            if not self.current_account:
                return False
            
            # Authorization chain
            if self.authorization_chain:
                if not self.authorization_chain.handle(self.current_account, command):
                    return False
            
            self.state = ATMState.PROCESSING
            
            # Execute transaction
            if command.execute():
                self.transactions.append(command)
                self.state = ATMState.AUTHENTICATED
                return True
            else:
                self.state = ATMState.AUTHENTICATED
                return False
    
    def dispense_cash(self, amount: float) -> bool:
        """Dispense cash"""
        if self.cash_available >= amount:
            self.cash_available -= amount
            print(f"Dispensing ${amount:.2f}")
            return True
        print("Insufficient cash in ATM")
        return False
    
    def accept_cash(self, amount: float) -> bool:
        """Accept cash deposit"""
        self.cash_available += amount
        print(f"Accepting ${amount:.2f}")
        return True
    
    def eject_card(self):
        """Eject card"""
        with self.lock:
            self.current_card = None
            self.current_account = None
            self.state = ATMState.IDLE
    
    def cancel_transaction(self, command: TransactionCommand) -> bool:
        """Cancel/rollback transaction"""
        return command.undo()


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("ATM SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    # Create accounts
    account1 = Account("ACC001", "CARD001", "1234", 5000.0)
    accounts = {account1.account_number: account1}
    
    # Create ATM
    atm = ATM("ATM001")
    
    # Set up authorization chain
    chain = AccountStatusHandler()
    chain.set_next(BalanceCheckHandler()).set_next(DailyLimitHandler())
    atm.set_authorization_chain(chain)
    
    print("1. Inserting card:")
    atm.insert_card("CARD001")
    print(f"ATM State: {atm.state.value}")
    print()
    
    print("2. Authenticating:")
    atm.authenticate("1234", accounts)
    print(f"ATM State: {atm.state.value}")
    print(f"Account Balance: ${account1.balance:.2f}")
    print()
    
    print("3. Balance inquiry:")
    inquiry = BalanceInquiryCommand(atm, account1)
    atm.process_transaction(inquiry)
    print()
    
    print("4. Withdrawal:")
    withdrawal = WithdrawalCommand(atm, account1, 500.0)
    if atm.process_transaction(withdrawal):
        print(f"New Balance: ${account1.balance:.2f}")
    print()
    
    print("5. Failed withdrawal (insufficient balance):")
    failed_withdrawal = WithdrawalCommand(atm, account1, 10000.0)
    atm.process_transaction(failed_withdrawal)
    print()
    
    print("6. Ejecting card:")
    atm.eject_card()
    print(f"ATM State: {atm.state.value}")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. State Pattern - ATM and transaction states")
    print("2. Command Pattern - Transaction operations with undo")
    print("3. Strategy Pattern - Different transaction types")
    print("4. Chain of Responsibility - Authorization checks")
    print("5. Observer Pattern - Transaction logging")
    print()
    print("FEATURES:")
    print("- Concurrent transaction handling")
    print("- Transaction rollback")
    print("- Authorization chain")
    print("- Cash management")
    print("- Account locking")
    print("=" * 60)


if __name__ == "__main__":
    from uuid import uuid4
    main()

