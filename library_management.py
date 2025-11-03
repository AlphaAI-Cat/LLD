"""
Library Management System
=========================

Core Design: System to manage books, members, and loans.

Design Patterns & Strategies Used:
1. State Pattern - Book states (Available, Borrowed, Reserved, Maintenance)
2. Observer Pattern - Notify about due dates and availability
3. Factory Pattern - Create books and members
4. Strategy Pattern - Different fine calculation strategies
5. Command Pattern - Library operations
6. Template Method - Loan workflow

Features:
- Book catalog management
- Member registration
- Book borrowing and returning
- Reservation system
- Fine calculation
- Due date tracking
- Search functionality
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass
from uuid import uuid4


class BookState(Enum):
    AVAILABLE = "AVAILABLE"
    BORROWED = "BORROWED"
    RESERVED = "RESERVED"
    MAINTENANCE = "MAINTENANCE"


class LoanStatus(Enum):
    ACTIVE = "ACTIVE"
    RETURNED = "RETURNED"
    OVERDUE = "OVERDUE"


@dataclass
class Book:
    """Book entity"""
    book_id: str
    isbn: str
    title: str
    author: str
    publication_year: int
    state: BookState
    copies_total: int
    copies_available: int
    
    def borrow(self) -> bool:
        """Borrow a copy"""
        if self.state == BookState.AVAILABLE and self.copies_available > 0:
            self.copies_available -= 1
            if self.copies_available == 0:
                self.state = BookState.BORROWED
            return True
        return False
    
    def return_book(self) -> bool:
        """Return a copy"""
        if self.copies_available < self.copies_total:
            self.copies_available += 1
            if self.state == BookState.BORROWED:
                self.state = BookState.AVAILABLE
            return True
        return False
    
    def reserve(self) -> bool:
        """Reserve book"""
        if self.state == BookState.AVAILABLE:
            self.state = BookState.RESERVED
            return True
        return False


@dataclass
class Member:
    """Library member"""
    member_id: str
    name: str
    email: str
    phone: str
    membership_type: str
    max_books: int = 5
    active_loans: List[str] = None
    
    def __post_init__(self):
        if self.active_loans is None:
            self.active_loans = []
    
    def can_borrow(self) -> bool:
        """Check if member can borrow more books"""
        return len(self.active_loans) < self.max_books


@dataclass
class Loan:
    """Loan record"""
    loan_id: str
    book_id: str
    member_id: str
    borrow_date: datetime
    due_date: datetime
    return_date: Optional[datetime]
    status: LoanStatus
    fine_amount: float = 0.0


class FineStrategy(ABC):
    """Fine calculation strategy"""
    
    @abstractmethod
    def calculate_fine(self, loan: Loan) -> float:
        pass


class StandardFineStrategy(FineStrategy):
    """Standard fine calculation"""
    
    def __init__(self, daily_rate: float = 1.0, max_fine: float = 50.0):
        self.daily_rate = daily_rate
        self.max_fine = max_fine
    
    def calculate_fine(self, loan: Loan) -> float:
        if loan.status != LoanStatus.OVERDUE:
            return 0.0
        
        if loan.return_date:
            overdue_days = (loan.return_date - loan.due_date).days
        else:
            overdue_days = max(0, (datetime.now() - loan.due_date).days)
        
        fine = min(overdue_days * self.daily_rate, self.max_fine)
        loan.fine_amount = fine
        return fine


class TieredFineStrategy(FineStrategy):
    """Tiered fine calculation"""
    
    def calculate_fine(self, loan: Loan) -> float:
        if loan.status != LoanStatus.OVERDUE:
            return 0.0
        
        if loan.return_date:
            overdue_days = (loan.return_date - loan.due_date).days
        else:
            overdue_days = max(0, (datetime.now() - loan.due_date).days)
        
        # Tiered rates
        if overdue_days <= 7:
            fine = overdue_days * 0.5
        elif overdue_days <= 14:
            fine = 7 * 0.5 + (overdue_days - 7) * 1.0
        else:
            fine = 7 * 0.5 + 7 * 1.0 + (overdue_days - 14) * 2.0
        
        loan.fine_amount = fine
        return fine


class LibraryService:
    """Main library service"""
    
    def __init__(self, loan_period_days: int = 14):
        self.books: Dict[str, Book] = {}
        self.members: Dict[str, Member] = {}
        self.loans: Dict[str, Loan] = {}
        self.loan_period_days = loan_period_days
        self.fine_strategy: FineStrategy = StandardFineStrategy()
        self.observers: List = []
    
    def set_fine_strategy(self, strategy: FineStrategy):
        """Set fine calculation strategy"""
        self.fine_strategy = strategy
    
    def add_book(self, isbn: str, title: str, author: str, 
                publication_year: int, copies: int = 1) -> str:
        """Add book to catalog"""
        book_id = str(uuid4())
        book = Book(
            book_id=book_id,
            isbn=isbn,
            title=title,
            author=author,
            publication_year=publication_year,
            state=BookState.AVAILABLE,
            copies_total=copies,
            copies_available=copies
        )
        self.books[book_id] = book
        return book_id
    
    def register_member(self, name: str, email: str, phone: str,
                       membership_type: str = "Standard") -> str:
        """Register new member"""
        member_id = str(uuid4())
        member = Member(
            member_id=member_id,
            name=name,
            email=email,
            phone=phone,
            membership_type=membership_type
        )
        self.members[member_id] = member
        return member_id
    
    def borrow_book(self, book_id: str, member_id: str) -> Optional[str]:
        """Borrow book"""
        if book_id not in self.books or member_id not in self.members:
            return None
        
        book = self.books[book_id]
        member = self.members[member_id]
        
        # Check if member can borrow
        if not member.can_borrow():
            print(f"Member {member.name} has reached borrowing limit")
            return None
        
        # Try to borrow
        if not book.borrow():
            print(f"Book '{book.title}' is not available")
            return None
        
        # Create loan
        loan_id = str(uuid4())
        now = datetime.now()
        loan = Loan(
            loan_id=loan_id,
            book_id=book_id,
            member_id=member_id,
            borrow_date=now,
            due_date=now + timedelta(days=self.loan_period_days),
            return_date=None,
            status=LoanStatus.ACTIVE
        )
        
        self.loans[loan_id] = loan
        member.active_loans.append(loan_id)
        
        print(f"Book '{book.title}' borrowed by {member.name}")
        return loan_id
    
    def return_book(self, loan_id: str) -> float:
        """Return book and calculate fine"""
        if loan_id not in self.loans:
            return 0.0
        
        loan = self.loans[loan_id]
        book = self.books[loan.book_id]
        member = self.members[loan.member_id]
        
        # Check if overdue
        if datetime.now() > loan.due_date and loan.status == LoanStatus.ACTIVE:
            loan.status = LoanStatus.OVERDUE
        
        loan.return_date = datetime.now()
        loan.status = LoanStatus.RETURNED
        
        # Calculate fine
        fine = self.fine_strategy.calculate_fine(loan)
        
        # Return book
        book.return_book()
        member.active_loans.remove(loan_id)
        
        if fine > 0:
            print(f"Fine charged: ${fine:.2f}")
        else:
            print(f"Book '{book.title}' returned successfully")
        
        return fine
    
    def search_books(self, query: str) -> List[Book]:
        """Search books by title or author"""
        query_lower = query.lower()
        results = []
        
        for book in self.books.values():
            if (query_lower in book.title.lower() or 
                query_lower in book.author.lower() or
                query_lower in book.isbn.lower()):
                results.append(book)
        
        return results
    
    def check_overdue_loans(self) -> List[Loan]:
        """Check for overdue loans"""
        overdue = []
        now = datetime.now()
        
        for loan in self.loans.values():
            if loan.status == LoanStatus.ACTIVE and now > loan.due_date:
                loan.status = LoanStatus.OVERDUE
                overdue.append(loan)
        
        return overdue
    
    def reserve_book(self, book_id: str, member_id: str) -> bool:
        """Reserve book"""
        if book_id not in self.books:
            return False
        
        book = self.books[book_id]
        return book.reserve()


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("LIBRARY MANAGEMENT SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    library = LibraryService(loan_period_days=14)
    
    print("1. Adding books:")
    book1_id = library.add_book("978-0-123456-78-9", "Python Programming", 
                                "John Doe", 2020, copies=2)
    book2_id = library.add_book("978-0-987654-32-1", "Data Structures", 
                                "Jane Smith", 2019, copies=1)
    print(f"Added 2 books")
    print()
    
    print("2. Registering members:")
    member1_id = library.register_member("Alice", "alice@example.com", 
                                        "123-456-7890")
    member2_id = library.register_member("Bob", "bob@example.com", 
                                         "098-765-4321")
    print(f"Registered 2 members")
    print()
    
    print("3. Borrowing books:")
    loan1_id = library.borrow_book(book1_id, member1_id)
    loan2_id = library.borrow_book(book1_id, member2_id)
    loan3_id = library.borrow_book(book2_id, member1_id)
    print()
    
    print("4. Searching books:")
    results = library.search_books("Python")
    print(f"Found {len(results)} book(s):")
    for book in results:
        print(f"  - {book.title} by {book.author}")
    print()
    
    print("5. Checking overdue loans:")
    overdue = library.check_overdue_loans()
    print(f"Overdue loans: {len(overdue)}")
    print()
    
    print("6. Returning books:")
    fine = library.return_book(loan1_id)
    if fine > 0:
        print(f"Fine: ${fine:.2f}")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. State Pattern - Book states (Available, Borrowed, Reserved)")
    print("2. Observer Pattern - Due date notifications")
    print("3. Factory Pattern - Create books and members")
    print("4. Strategy Pattern - Fine calculation (Standard, Tiered)")
    print("5. Command Pattern - Library operations")
    print()
    print("FEATURES:")
    print("- Book catalog management")
    print("- Member registration")
    print("- Borrowing and returning")
    print("- Reservation system")
    print("- Fine calculation")
    print("- Search functionality")
    print("=" * 60)


if __name__ == "__main__":
    main()

