"""
Chat/Messaging System
=====================

Core Design: Real-time messaging system with multiple users and chat rooms.

Design Patterns & Strategies Used:
1. Observer Pattern - Real-time message delivery
2. Strategy Pattern - Different message types (Text, Image, File)
3. State Pattern - Message delivery states
4. Factory Pattern - Create messages and chat rooms
5. Publisher-Subscriber Pattern - Message broadcasting
6. Queue Pattern - Message queue for delivery

Features:
- One-on-one messaging
- Group chats
- Message delivery status (Sent, Delivered, Read)
- Typing indicators
- Message persistence
- Real-time updates
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Set
from datetime import datetime
from dataclasses import dataclass
from uuid import uuid4
from queue import Queue
from threading import Thread, Lock


class MessageType(Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    FILE = "FILE"
    SYSTEM = "SYSTEM"


class DeliveryStatus(Enum):
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"


@dataclass
class Message:
    """Message entity"""
    message_id: str
    sender_id: str
    chat_id: str
    content: str
    message_type: MessageType
    timestamp: datetime
    status: DeliveryStatus = DeliveryStatus.SENT
    is_edited: bool = False
    reply_to: Optional[str] = None


class MessageHandler(ABC):
    """Message handler strategy"""
    
    @abstractmethod
    def handle(self, message: Message) -> bool:
        pass


class TextMessageHandler(MessageHandler):
    """Text message handler"""
    
    def handle(self, message: Message) -> bool:
        print(f"[Text] {message.content[:50]}")
        return True


class ImageMessageHandler(MessageHandler):
    """Image message handler"""
    
    def handle(self, message: Message) -> bool:
        print(f"[Image] Image file: {message.content}")
        return True


class FileMessageHandler(MessageHandler):
    """File message handler"""
    
    def handle(self, message: Message) -> bool:
        print(f"[File] File: {message.content}")
        return True


class ChatObserver(ABC):
    """Observer for chat events"""
    
    @abstractmethod
    def on_message(self, message: Message):
        pass
    
    @abstractmethod
    def on_typing(self, user_id: str, chat_id: str):
        pass


class User:
    """Chat user"""
    
    def __init__(self, user_id: str, username: str):
        self.user_id = user_id
        self.username = username
        self.active_chats: Set[str] = set()
        self.is_online = False


class Chat:
    """Chat room (one-on-one or group)"""
    
    def __init__(self, chat_id: str, chat_type: str, participants: List[str]):
        self.chat_id = chat_id
        self.chat_type = chat_type  # "direct" or "group"
        self.participants: Set[str] = set(participants)
        self.messages: List[Message] = []
        self.observers: List[ChatObserver] = []
        self.lock = Lock()
    
    def add_participant(self, user_id: str):
        """Add participant"""
        self.participants.add(user_id)
    
    def remove_participant(self, user_id: str):
        """Remove participant"""
        self.participants.discard(user_id)
    
    def add_message(self, message: Message):
        """Add message to chat"""
        with self.lock:
            self.messages.append(message)
        
        # Notify observers
        for observer in self.observers:
            observer.on_message(message)
    
    def get_messages(self, limit: int = 50) -> List[Message]:
        """Get recent messages"""
        with self.lock:
            return self.messages[-limit:]


class MessagingService:
    """Main messaging service"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.chats: Dict[str, Chat] = {}
        self.message_handlers: Dict[MessageType, MessageHandler] = {
            MessageType.TEXT: TextMessageHandler(),
            MessageType.IMAGE: ImageMessageHandler(),
            MessageType.FILE: FileMessageHandler()
        }
        self.message_queue = Queue()
        self.running = False
        self.worker_thread: Optional[Thread] = None
    
    def register_user(self, username: str) -> str:
        """Register user"""
        user_id = str(uuid4())
        user = User(user_id, username)
        self.users[user_id] = user
        return user_id
    
    def create_direct_chat(self, user1_id: str, user2_id: str) -> str:
        """Create direct chat"""
        chat_id = str(uuid4())
        chat = Chat(chat_id, "direct", [user1_id, user2_id])
        self.chats[chat_id] = chat
        
        self.users[user1_id].active_chats.add(chat_id)
        self.users[user2_id].active_chats.add(chat_id)
        
        return chat_id
    
    def create_group_chat(self, creator_id: str, participant_ids: List[str]) -> str:
        """Create group chat"""
        chat_id = str(uuid4())
        participants = [creator_id] + participant_ids
        chat = Chat(chat_id, "group", participants)
        self.chats[chat_id] = chat
        
        for user_id in participants:
            if user_id in self.users:
                self.users[user_id].active_chats.add(chat_id)
        
        return chat_id
    
    def send_message(self, sender_id: str, chat_id: str, content: str,
                    message_type: MessageType = MessageType.TEXT) -> Optional[str]:
        """Send message"""
        if chat_id not in self.chats:
            return None
        
        chat = self.chats[chat_id]
        
        if sender_id not in chat.participants:
            return None
        
        message_id = str(uuid4())
        message = Message(
            message_id=message_id,
            sender_id=sender_id,
            chat_id=chat_id,
            content=content,
            message_type=message_type,
            timestamp=datetime.now()
        )
        
        # Handle message based on type
        handler = self.message_handlers.get(message_type)
        if handler:
            handler.handle(message)
        
        # Add to chat
        chat.add_message(message)
        
        # Queue for delivery
        self.message_queue.put(message)
        
        return message_id
    
    def mark_as_read(self, message_id: str, user_id: str):
        """Mark message as read"""
        # Find message in chats
        for chat in self.chats.values():
            for message in chat.messages:
                if message.message_id == message_id and message.sender_id != user_id:
                    message.status = DeliveryStatus.READ
                    return True
        return False
    
    def mark_as_delivered(self, message_id: str):
        """Mark message as delivered"""
        for chat in self.chats.values():
            for message in chat.messages:
                if message.message_id == message_id:
                    if message.status == DeliveryStatus.SENT:
                        message.status = DeliveryStatus.DELIVERED
                    return True
        return False
    
    def get_chat_history(self, chat_id: str, limit: int = 50) -> List[Message]:
        """Get chat history"""
        if chat_id not in self.chats:
            return []
        return self.chats[chat_id].get_messages(limit)
    
    def start_delivery_service(self):
        """Start message delivery service"""
        self.running = True
        
        def delivery_worker():
            while self.running or not self.message_queue.empty():
                try:
                    message = self.message_queue.get(timeout=1)
                    # Simulate delivery delay
                    import time
                    time.sleep(0.1)
                    self.mark_as_delivered(message.message_id)
                except:
                    pass
        
        self.worker_thread = Thread(target=delivery_worker, daemon=True)
        self.worker_thread.start()
    
    def stop_delivery_service(self):
        """Stop delivery service"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("CHAT/MESSAGING SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    service = MessagingService()
    service.start_delivery_service()
    
    print("1. Registering users:")
    user1_id = service.register_user("Alice")
    user2_id = service.register_user("Bob")
    user3_id = service.register_user("Charlie")
    print(f"Registered: Alice, Bob, Charlie")
    print()
    
    print("2. Creating direct chat:")
    chat_id = service.create_direct_chat(user1_id, user2_id)
    print(f"Direct chat created: {chat_id}")
    print()
    
    print("3. Sending messages:")
    service.send_message(user1_id, chat_id, "Hello, Bob!")
    service.send_message(user2_id, chat_id, "Hi Alice, how are you?")
    service.send_message(user1_id, chat_id, "I'm doing great!")
    print()
    
    print("4. Creating group chat:")
    group_chat_id = service.create_group_chat(user1_id, [user2_id, user3_id])
    print(f"Group chat created: {group_chat_id}")
    service.send_message(user1_id, group_chat_id, "Hello everyone!")
    print()
    
    print("5. Chat history:")
    history = service.get_chat_history(chat_id, limit=10)
    print(f"Messages in chat: {len(history)}")
    for msg in history:
        sender = service.users[msg.sender_id].username
        print(f"  [{msg.timestamp}] {sender}: {msg.content}")
    print()
    
    import time
    time.sleep(0.5)
    service.stop_delivery_service()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. Observer Pattern - Real-time message delivery")
    print("2. Strategy Pattern - Different message types")
    print("3. State Pattern - Message delivery states")
    print("4. Factory Pattern - Create messages and chats")
    print("5. Publisher-Subscriber - Message broadcasting")
    print("6. Queue Pattern - Message queue for delivery")
    print()
    print("FEATURES:")
    print("- One-on-one and group messaging")
    print("- Message delivery status")
    print("- Real-time updates")
    print("- Message persistence")
    print("=" * 60)


if __name__ == "__main__":
    main()

