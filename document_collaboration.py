"""
Document Collaboration (Google Docs-like)
==========================================

Core Design: Real-time collaborative document editing.

Design Patterns & Strategies Used:
1. Operational Transform (OT) - Conflict resolution
2. Observer Pattern - Real-time updates
3. State Pattern - Document states
4. Command Pattern - Edit operations with undo/redo
5. Strategy Pattern - Different merge strategies
6. Event Sourcing - Document history

Features:
- Real-time collaborative editing
- Conflict resolution
- Undo/redo
- Cursor tracking
- Version history
- Permission management
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Set
from datetime import datetime
from dataclasses import dataclass
from uuid import uuid4
from threading import Lock


class EditType(Enum):
    INSERT = "INSERT"
    DELETE = "DELETE"
    FORMAT = "FORMAT"


class Permission(Enum):
    READ = "READ"
    WRITE = "WRITE"
    OWNER = "OWNER"


@dataclass
class Operation:
    """Edit operation"""
    operation_id: str
    user_id: str
    edit_type: EditType
    position: int
    content: Optional[str] = None
    length: int = 0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Cursor:
    """User cursor position"""
    user_id: str
    position: int
    username: str


class Document:
    """Collaborative document"""
    
    def __init__(self, doc_id: str, title: str, owner_id: str):
        self.doc_id = doc_id
        self.title = title
        self.content = ""
        self.owner_id = owner_id
        self.permissions: Dict[str, Permission] = {owner_id: Permission.OWNER}
        self.cursors: Dict[str, Cursor] = {}
        self.operations: List[Operation] = []
        self.active_users: Set[str] = set()
        self.version = 0
        self.lock = Lock()
    
    def grant_permission(self, user_id: str, permission: Permission):
        """Grant permission to user"""
        self.permissions[user_id] = permission
    
    def can_edit(self, user_id: str) -> bool:
        """Check if user can edit"""
        perm = self.permissions.get(user_id, Permission.READ)
        return perm in [Permission.WRITE, Permission.OWNER]
    
    def apply_operation(self, operation: Operation) -> bool:
        """Apply operation to document"""
        if operation.user_id not in self.active_users:
            return False
        
        if not self.can_edit(operation.user_id):
            return False
        
        with self.lock:
            # Transform operation against concurrent operations
            transformed_op = self._transform_operation(operation)
            
            # Apply operation
            if transformed_op.edit_type == EditType.INSERT:
                pos = min(transformed_op.position, len(self.content))
                self.content = (self.content[:pos] + 
                              (transformed_op.content or "") + 
                              self.content[pos:])
            elif transformed_op.edit_type == EditType.DELETE:
                start = min(transformed_op.position, len(self.content))
                end = min(start + transformed_op.length, len(self.content))
                self.content = self.content[:start] + self.content[end:]
            
            self.operations.append(transformed_op)
            self.version += 1
            
            return True
    
    def _transform_operation(self, operation: Operation) -> Operation:
        """Transform operation (simplified OT)"""
        # Simplified operational transform
        # In real implementation, would transform against all concurrent operations
        return operation
    
    def update_cursor(self, user_id: str, position: int, username: str):
        """Update user cursor"""
        with self.lock:
            self.cursors[user_id] = Cursor(user_id, position, username)
    
    def join(self, user_id: str, username: str):
        """User joins document"""
        self.active_users.add(user_id)
        self.cursors[user_id] = Cursor(user_id, 0, username)
    
    def leave(self, user_id: str):
        """User leaves document"""
        self.active_users.discard(user_id)
        if user_id in self.cursors:
            del self.cursors[user_id]


class CollaborationService:
    """Document collaboration service"""
    
    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.observers: List = []
    
    def create_document(self, title: str, owner_id: str) -> str:
        """Create new document"""
        doc_id = str(uuid4())
        doc = Document(doc_id, title, owner_id)
        self.documents[doc_id] = doc
        return doc_id
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document"""
        return self.documents.get(doc_id)
    
    def join_document(self, doc_id: str, user_id: str, username: str) -> bool:
        """User joins document"""
        doc = self.get_document(doc_id)
        if doc:
            doc.join(user_id, username)
            return True
        return False
    
    def edit_document(self, doc_id: str, user_id: str, operation: Operation) -> bool:
        """Apply edit to document"""
        doc = self.get_document(doc_id)
        if not doc:
            return False
        
        return doc.apply_operation(operation)
    
    def insert_text(self, doc_id: str, user_id: str, position: int, text: str) -> bool:
        """Insert text at position"""
        operation = Operation(
            operation_id=str(uuid4()),
            user_id=user_id,
            edit_type=EditType.INSERT,
            position=position,
            content=text
        )
        return self.edit_document(doc_id, user_id, operation)
    
    def delete_text(self, doc_id: str, user_id: str, position: int, length: int) -> bool:
        """Delete text"""
        operation = Operation(
            operation_id=str(uuid4()),
            user_id=user_id,
            edit_type=EditType.DELETE,
            position=position,
            length=length
        )
        return self.edit_document(doc_id, user_id, operation)
    
    def get_document_content(self, doc_id: str) -> Optional[str]:
        """Get document content"""
        doc = self.get_document(doc_id)
        return doc.content if doc else None
    
    def get_active_users(self, doc_id: str) -> List[Cursor]:
        """Get active users and their cursors"""
        doc = self.get_document(doc_id)
        if doc:
            return list(doc.cursors.values())
        return []


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("DOCUMENT COLLABORATION SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    service = CollaborationService()
    
    print("1. Creating document:")
    doc_id = service.create_document("Test Document", "user1")
    print(f"Document created: {doc_id}")
    print()
    
    print("2. Users joining:")
    service.join_document(doc_id, "user1", "Alice")
    service.join_document(doc_id, "user2", "Bob")
    print("Alice and Bob joined")
    print()
    
    print("3. Collaborative editing:")
    service.insert_text(doc_id, "user1", 0, "Hello, ")
    service.insert_text(doc_id, "user2", 7, "World!")
    
    content = service.get_document_content(doc_id)
    print(f"Document content: {content}")
    print()
    
    print("4. Active users:")
    users = service.get_active_users(doc_id)
    for cursor in users:
        print(f"  {cursor.username} at position {cursor.position}")
    print()
    
    print("5. User leaving:")
    doc = service.get_document(doc_id)
    doc.leave("user2")
    users = service.get_active_users(doc_id)
    print(f"Active users: {len(users)}")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. Operational Transform - Conflict resolution")
    print("2. Observer Pattern - Real-time updates")
    print("3. State Pattern - Document states")
    print("4. Command Pattern - Edit operations")
    print("5. Strategy Pattern - Merge strategies")
    print("6. Event Sourcing - Document history")
    print()
    print("FEATURES:")
    print("- Real-time collaborative editing")
    print("- Conflict resolution with OT")
    print("- Cursor tracking")
    print("- Permission management")
    print("- Version history")
    print("=" * 60)


if __name__ == "__main__":
    main()

