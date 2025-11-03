"""
Logger System
=============

Core Design: Logging framework with configurable log levels and appenders.

Design Patterns & Strategies Used:
1. Strategy Pattern - Different log formatting strategies
2. Chain of Responsibility - Log level filtering
3. Observer Pattern - Multiple log sinks/appenders
4. Singleton Pattern - Logger manager
5. Factory Pattern - Create loggers and appenders
6. Template Method - Common logging operations
7. Decorator Pattern - Log rotation, async logging

Features:
- Multiple log levels (DEBUG, INFO, WARN, ERROR, FATAL)
- Multiple appenders (Console, File, Database, Remote)
- Log rotation based on size or time
- Async logging for performance
- Thread-safe logging
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime
from threading import Lock
from queue import Queue
import threading
import os


class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3
    FATAL = 4


# ==================== CHAIN OF RESPONSIBILITY ====================
# Log level filtering chain

class LogHandler(ABC):
    """Handler in Chain of Responsibility"""
    
    def __init__(self, level: LogLevel):
        self.level = level
        self.next_handler: Optional['LogHandler'] = None
    
    def set_next(self, handler: 'LogHandler') -> 'LogHandler':
        self.next_handler = handler
        return handler
    
    def handle(self, level: LogLevel, message: str):
        """Handle log or pass to next in chain"""
        if level.value >= self.level.value:
            self.write_log(level, message)
        
        if self.next_handler:
            self.next_handler.handle(level, message)
    
    @abstractmethod
    def write_log(self, level: LogLevel, message: str):
        pass


# ==================== STRATEGY PATTERN ====================
# Different formatting strategies

class FormatterStrategy(ABC):
    """Formatter strategy interface"""
    
    @abstractmethod
    def format(self, level: LogLevel, message: str, timestamp: datetime) -> str:
        pass


class SimpleFormatter(FormatterStrategy):
    """Simple formatter"""
    
    def format(self, level: LogLevel, message: str, timestamp: datetime) -> str:
        return f"{timestamp.isoformat()} [{level.name}] {message}"


class DetailedFormatter(FormatterStrategy):
    """Detailed formatter with thread info"""
    
    def format(self, level: LogLevel, message: str, timestamp: datetime) -> str:
        thread_id = threading.current_thread().ident
        return (f"{timestamp.isoformat()} [{level.name}] "
                f"[Thread-{thread_id}] {message}")


class JSONFormatter(FormatterStrategy):
    """JSON formatter"""
    
    def format(self, level: LogLevel, message: str, timestamp: datetime) -> str:
        import json
        return json.dumps({
            "timestamp": timestamp.isoformat(),
            "level": level.name,
            "message": message
        })


# ==================== OBSERVER PATTERN ====================
# Multiple log appenders/sinks

class LogAppender(ABC):
    """Appender interface (Observer)"""
    
    def __init__(self, formatter: FormatterStrategy):
        self.formatter = formatter
    
    @abstractmethod
    def append(self, level: LogLevel, message: str, timestamp: datetime):
        pass
    
    @abstractmethod
    def close(self):
        pass


class ConsoleAppender(LogAppender):
    """Console appender"""
    
    def append(self, level: LogLevel, message: str, timestamp: datetime):
        formatted = self.formatter.format(level, message, timestamp)
        print(formatted)
    
    def close(self):
        pass


class FileAppender(LogAppender):
    """File appender"""
    
    def __init__(self, file_path: str, formatter: FormatterStrategy):
        super().__init__(formatter)
        self.file_path = file_path
        self.file = open(file_path, 'a')
        self.lock = Lock()
    
    def append(self, level: LogLevel, message: str, timestamp: datetime):
        formatted = self.formatter.format(level, message, timestamp)
        with self.lock:
            self.file.write(formatted + '\n')
            self.file.flush()
    
    def close(self):
        with self.lock:
            self.file.close()


class DatabaseAppender(LogAppender):
    """Database appender (simulated)"""
    
    def append(self, level: LogLevel, message: str, timestamp: datetime):
        formatted = self.formatter.format(level, message, timestamp)
        # In real implementation, would insert into database
        print(f"[DB] Would store: {formatted}")
    
    def close(self):
        pass


class RotatingFileAppender(FileAppender):
    """File appender with rotation"""
    
    def __init__(self, file_path: str, formatter: FormatterStrategy, 
                 max_size: int = 1024 * 1024, backup_count: int = 5):
        super().__init__(file_path, formatter)
        self.max_size = max_size
        self.backup_count = backup_count
    
    def append(self, level: LogLevel, message: str, timestamp: datetime):
        # Check file size and rotate if needed
        if os.path.getsize(self.file_path) >= self.max_size:
            self._rotate()
        
        super().append(level, message, timestamp)
    
    def _rotate(self):
        """Rotate log file"""
        with self.lock:
            self.file.close()
            
            # Shift existing backups
            for i in range(self.backup_count - 1, 0, -1):
                old_file = f"{self.file_path}.{i}"
                new_file = f"{self.file_path}.{i + 1}"
                if os.path.exists(old_file):
                    os.rename(old_file, new_file)
            
            # Move current to .1
            if os.path.exists(self.file_path):
                os.rename(self.file_path, f"{self.file_path}.1")
            
            # Open new file
            self.file = open(self.file_path, 'a')


# ==================== DECORATOR PATTERN ====================
# Async logging decorator

class AsyncAppender(LogAppender):
    """Decorator for async logging"""
    
    def __init__(self, appender: LogAppender):
        self.appender = appender
        self.queue = Queue()
        self.running = False
        self.worker_thread = None
    
    def start(self):
        """Start async worker thread"""
        self.running = True
        
        def worker():
            while self.running or not self.queue.empty():
                try:
                    level, message, timestamp = self.queue.get(timeout=1)
                    self.appender.append(level, message, timestamp)
                    self.queue.task_done()
                except:
                    pass
        
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()
    
    def append(self, level: LogLevel, message: str, timestamp: datetime):
        """Queue log for async processing"""
        self.queue.put((level, message, timestamp))
    
    def close(self):
        """Stop async worker and close appender"""
        self.running = False
        if self.worker_thread:
            self.queue.join()
            self.worker_thread.join(timeout=5)
        self.appender.close()


# ==================== SINGLETON PATTERN ====================
# Logger manager

class Logger:
    """Logger class"""
    
    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        self.name = name
        self.level = level
        self.appenders: List[LogAppender] = []
        self.lock = Lock()
    
    def add_appender(self, appender: LogAppender):
        """Add log appender"""
        if isinstance(appender, AsyncAppender):
            appender.start()
        self.appenders.append(appender)
    
    def log(self, level: LogLevel, message: str):
        """Log a message"""
        if level.value < self.level.value:
            return
        
        timestamp = datetime.now()
        
        with self.lock:
            for appender in self.appenders:
                appender.append(level, message, timestamp)
    
    def debug(self, message: str):
        self.log(LogLevel.DEBUG, message)
    
    def info(self, message: str):
        self.log(LogLevel.INFO, message)
    
    def warn(self, message: str):
        self.log(LogLevel.WARN, message)
    
    def error(self, message: str):
        self.log(LogLevel.ERROR, message)
    
    def fatal(self, message: str):
        self.log(LogLevel.FATAL, message)
    
    def close(self):
        """Close all appenders"""
        for appender in self.appenders:
            appender.close()


class LoggerFactory:
    """Factory for creating loggers"""
    
    _loggers: Dict[str, Logger] = {}
    _lock = Lock()
    
    @staticmethod
    def get_logger(name: str, level: LogLevel = LogLevel.INFO) -> Logger:
        """Get or create logger (Singleton per name)"""
        with LoggerFactory._lock:
            if name not in LoggerFactory._loggers:
                LoggerFactory._loggers[name] = Logger(name, level)
            return LoggerFactory._loggers[name]
    
    @staticmethod
    def close_all():
        """Close all loggers"""
        with LoggerFactory._lock:
            for logger in LoggerFactory._loggers.values():
                logger.close()
            LoggerFactory._loggers.clear()


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("LOGGER SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    # Create logger with multiple appenders
    logger = LoggerFactory.get_logger("test", LogLevel.DEBUG)
    
    # Add console appender
    console_formatter = SimpleFormatter()
    console_appender = ConsoleAppender(console_formatter)
    logger.add_appender(console_appender)
    
    # Add file appender with rotation
    file_formatter = DetailedFormatter()
    file_appender = RotatingFileAppender("app.log", file_formatter, max_size=1000)
    logger.add_appender(file_appender)
    
    # Add async database appender
    db_formatter = JSONFormatter()
    db_appender = DatabaseAppender(db_formatter)
    async_db = AsyncAppender(db_appender)
    logger.add_appender(async_db)
    
    print("1. Logging at different levels:")
    logger.debug("This is a debug message")
    logger.info("Application started")
    logger.warn("This is a warning")
    logger.error("An error occurred")
    logger.fatal("Fatal error!")
    print()
    
    print("2. Thread-safe logging:")
    def log_from_thread(thread_id):
        for i in range(3):
            logger.info(f"Message {i} from thread {thread_id}")
    
    threads = []
    for i in range(3):
        t = threading.Thread(target=log_from_thread, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    print()
    
    # Close loggers
    LoggerFactory.close_all()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. Strategy Pattern - Different formatters (Simple, Detailed, JSON)")
    print("2. Chain of Responsibility - Log level filtering")
    print("3. Observer Pattern - Multiple appenders (Console, File, DB)")
    print("4. Singleton Pattern - One logger per name")
    print("5. Factory Pattern - Logger creation")
    print("6. Decorator Pattern - Async logging, rotation")
    print()
    print("FEATURES:")
    print("- Multiple log levels")
    print("- Log rotation by size")
    print("- Async logging for performance")
    print("- Thread-safe operations")
    print("- Multiple output sinks")
    print("=" * 60)


if __name__ == "__main__":
    main()

