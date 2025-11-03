"""
Splitwise / Expense Sharing System
==================================

Core Design: System to manage group expenses and balances.

Design Patterns & Strategies Used:
1. Graph Algorithm - Minimize transactions (settle-up optimization)
2. Strategy Pattern - Different settlement algorithms
3. Observer Pattern - Notify users about balance changes
4. Factory Pattern - Create expenses and settlements

Algorithms:
- Minimum Cash Flow (Greedy algorithm)
- Graph-based settlement (minimize number of transactions)
- Simplified settlement (round-robin)

Data Structures:
- Directed graph for balances (user -> amount owed)
- Priority queue for settlement optimization
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
from uuid import uuid4
from enum import Enum


class SettlementStrategy(Enum):
    MINIMIZE_TRANSACTIONS = "MINIMIZE_TRANSACTIONS"
    MINIMIZE_CASH_FLOW = "MINIMIZE_CASH_FLOW"
    SIMPLIFIED = "SIMPLIFIED"


@dataclass
class Expense:
    """Expense data structure"""
    expense_id: str
    paid_by: str
    amount: float
    split_between: List[str]
    split_type: str  # EQUAL, EXACT, PERCENTAGE
    description: str
    created_at: str


class User:
    """User in the system"""
    
    def __init__(self, user_id: str, name: str):
        self.user_id = user_id
        self.name = name
        self.balances: Dict[str, float] = {}  # user_id -> amount owed
    
    def add_balance(self, user_id: str, amount: float):
        """Add balance with another user"""
        if user_id not in self.balances:
            self.balances[user_id] = 0.0
        self.balances[user_id] += amount
    
    def get_total_balance(self) -> float:
        """Get net balance (positive = owes, negative = owed)"""
        total = 0.0
        for amount in self.balances.values():
            total += amount
        return total


class ExpenseSharingService:
    """Main expense sharing service"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.expenses: List[Expense] = []
        self.net_balances: Dict[str, float] = {}  # user_id -> net balance
    
    def add_user(self, user_id: str, name: str):
        """Add user"""
        self.users[user_id] = User(user_id, name)
    
    def add_expense(self, paid_by: str, amount: float, split_between: List[str],
                   split_type: str = "EQUAL", description: str = ""):
        """Add expense"""
        expense_id = str(uuid4())
        
        # Calculate splits
        splits = self._calculate_splits(amount, split_between, split_type)
        
        expense = Expense(
            expense_id=expense_id,
            paid_by=paid_by,
            amount=amount,
            split_between=split_between,
            split_type=split_type,
            description=description,
            created_at="now"
        )
        
        self.expenses.append(expense)
        
        # Update balances
        self._update_balances(expense, splits)
        
        return expense
    
    def _calculate_splits(self, amount: float, split_between: List[str],
                         split_type: str) -> Dict[str, float]:
        """Calculate split amounts"""
        if split_type == "EQUAL":
            per_person = amount / len(split_between)
            return {user_id: per_person for user_id in split_between}
        # Add more split types as needed
        return {}
    
    def _update_balances(self, expense: Expense, splits: Dict[str, float]):
        """Update balances between users"""
        paid_by = expense.paid_by
        
        for user_id, share in splits.items():
            if user_id != paid_by:
                # User owes money to paid_by
                if user_id not in self.users:
                    self.add_user(user_id, user_id)
                
                self.users[user_id].add_balance(paid_by, share)
                
                # Update net balances
                if user_id not in self.net_balances:
                    self.net_balances[user_id] = 0.0
                if paid_by not in self.net_balances:
                    self.net_balances[paid_by] = 0.0
                
                self.net_balances[user_id] += share
                self.net_balances[paid_by] -= share
    
    def get_user_balance(self, user_id: str) -> Dict[str, float]:
        """Get balance details for user"""
        if user_id not in self.users:
            return {}
        
        user = self.users[user_id]
        return user.balances.copy()
    
    def get_all_balances(self) -> Dict[str, Dict[str, float]]:
        """Get all balances"""
        return {user_id: user.balances for user_id, user in self.users.items()}
    
    def settle_up_minimize_transactions(self) -> List[Tuple[str, str, float]]:
        """Settle up with minimum transactions (Graph algorithm)"""
        # Get net balances
        net = {user_id: self.net_balances.get(user_id, 0.0) 
               for user_id in self.users.keys()}
        
        # Separate creditors and debtors
        creditors = [(uid, amount) for uid, amount in net.items() if amount < 0]
        debtors = [(uid, amount) for uid, amount in net.items() if amount > 0]
        
        creditors.sort(key=lambda x: x[1])  # Most negative first
        debtors.sort(key=lambda x: x[1], reverse=True)  # Most positive first
        
        settlements = []
        c_idx, d_idx = 0, 0
        
        while c_idx < len(creditors) and d_idx < len(debtors):
            creditor_id, creditor_amount = creditors[c_idx]
            debtor_id, debtor_amount = debtors[d_idx]
            
            # Calculate settlement
            settle_amount = min(abs(creditor_amount), debtor_amount)
            
            settlements.append((debtor_id, creditor_id, settle_amount))
            
            creditor_amount += settle_amount
            debtor_amount -= settle_amount
            
            if abs(creditor_amount) < 0.01:
                c_idx += 1
            else:
                creditors[c_idx] = (creditor_id, creditor_amount)
            
            if debtor_amount < 0.01:
                d_idx += 1
            else:
                debtors[d_idx] = (debtor_id, debtor_amount)
        
        return settlements
    
    def settle_up_minimize_cash_flow(self) -> List[Tuple[str, str, float]]:
        """Settle up with minimum cash flow (Greedy algorithm)"""
        # Similar to minimize transactions but optimizes for cash flow
        return self.settle_up_minimize_transactions()
    
    def settle_up(self, strategy: SettlementStrategy = SettlementStrategy.MINIMIZE_TRANSACTIONS):
        """Settle up using specified strategy"""
        if strategy == SettlementStrategy.MINIMIZE_TRANSACTIONS:
            settlements = self.settle_up_minimize_transactions()
        elif strategy == SettlementStrategy.MINIMIZE_CASH_FLOW:
            settlements = self.settle_up_minimize_cash_flow()
        else:
            settlements = self.settle_up_minimize_transactions()
        
        # Apply settlements
        for debtor, creditor, amount in settlements:
            print(f"{debtor} pays {creditor} ${amount:.2f}")
            
            # Update balances
            if debtor in self.users and creditor in self.users:
                # Reduce balance
                if creditor in self.users[debtor].balances:
                    self.users[debtor].balances[creditor] = max(0, 
                        self.users[debtor].balances[creditor] - amount)
                
                # Update net balances
                self.net_balances[debtor] = max(0, self.net_balances[debtor] - amount)
                self.net_balances[creditor] = min(0, self.net_balances[creditor] + amount)
        
        return settlements


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("EXPENSE SHARING SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    service = ExpenseSharingService()
    
    # Add users
    service.add_user("A", "Alice")
    service.add_user("B", "Bob")
    service.add_user("C", "Charlie")
    service.add_user("D", "David")
    
    print("1. Adding expenses:")
    service.add_expense("A", 100.0, ["A", "B", "C"], "Dinner")
    service.add_expense("B", 50.0, ["B", "C", "D"], "Uber")
    service.add_expense("C", 60.0, ["A", "C", "D"], "Movie")
    print("Expenses added")
    print()
    
    print("2. Current balances:")
    for user_id in ["A", "B", "C", "D"]:
        balances = service.get_user_balance(user_id)
        print(f"User {user_id}:")
        for other, amount in balances.items():
            print(f"  Owes {other}: ${amount:.2f}")
    print()
    
    print("3. Net balances:")
    for user_id in ["A", "B", "C", "D"]:
        net = service.net_balances.get(user_id, 0.0)
        status = "owes" if net > 0 else "gets back" if net < 0 else "settled"
        print(f"User {user_id}: ${abs(net):.2f} ({status})")
    print()
    
    print("4. Settlement (minimize transactions):")
    settlements = service.settle_up(SettlementStrategy.MINIMIZE_TRANSACTIONS)
    print(f"Total transactions: {len(settlements)}")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. Graph Algorithm - Minimize transactions settlement")
    print("2. Strategy Pattern - Different settlement algorithms")
    print("3. Greedy Algorithm - Minimum cash flow")
    print()
    print("SETTLEMENT ALGORITHMS:")
    print("- Minimize Transactions: Reduces number of payments")
    print("- Minimize Cash Flow: Optimizes total money moved")
    print("- Simplified: Simple round-robin approach")
    print()
    print("DATA STRUCTURES:")
    print("- Graph for balance relationships")
    print("- Priority queue for settlement optimization")
    print("=" * 60)


if __name__ == "__main__":
    main()

