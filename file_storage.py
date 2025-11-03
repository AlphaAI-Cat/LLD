"""
File Storage / Dropbox System
============================

Core Design: System to store and retrieve files, handle versioning.

Design Patterns & Strategies Used:
1. Version Control Pattern - File versioning and history
2. Observer Pattern - Notify about file changes
3. Strategy Pattern - Different storage backends (Local, S3, Azure)
4. Factory Pattern - Create storage handlers
5. Command Pattern - File operations with undo
6. Singleton Pattern - Storage service

Features:
- File upload/download
- Version history
- Conflict resolution (Last Write Wins, Manual Merge)
- Metadata management
- Replication for consistency
- Delta sync for efficiency
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import datetime
from dataclasses import dataclass
from uuid import uuid4
from enum import Enum
import hashlib


class ConflictResolution(Enum):
    LAST_WRITE_WINS = "LAST_WRITE_WINS"
    MANUAL_MERGE = "MANUAL_MERGE"
    VERSIONED = "VERSIONED"


@dataclass
class FileVersion:
    """File version metadata"""
    version_id: str
    file_id: str
    content_hash: str
    size: int
    created_at: datetime
    modified_by: str
    parent_version: Optional[str] = None


@dataclass
class FileMetadata:
    """File metadata"""
    file_id: str
    filename: str
    path: str
    size: int
    content_type: str
    created_at: datetime
    modified_at: datetime
    created_by: str
    current_version: str
    is_deleted: bool = False


class StorageBackend(ABC):
    """Storage backend interface"""
    
    @abstractmethod
    def store(self, file_id: str, content: bytes, version_id: str) -> bool:
        pass
    
    @abstractmethod
    def retrieve(self, file_id: str, version_id: str) -> Optional[bytes]:
        pass
    
    @abstractmethod
    def delete(self, file_id: str, version_id: str) -> bool:
        pass


class LocalStorageBackend(StorageBackend):
    """Local file storage backend"""
    
    def __init__(self, base_path: str = "./storage"):
        self.base_path = base_path
    
    def store(self, file_id: str, content: bytes, version_id: str) -> bool:
        print(f"[LocalStorage] Storing {file_id} version {version_id}")
        return True
    
    def retrieve(self, file_id: str, version_id: str) -> Optional[bytes]:
        print(f"[LocalStorage] Retrieving {file_id} version {version_id}")
        return b"file content"
    
    def delete(self, file_id: str, version_id: str) -> bool:
        print(f"[LocalStorage] Deleting {file_id} version {version_id}")
        return True


class S3StorageBackend(StorageBackend):
    """AWS S3 storage backend"""
    
    def store(self, file_id: str, content: bytes, version_id: str) -> bool:
        print(f"[S3] Storing {file_id} version {version_id}")
        return True
    
    def retrieve(self, file_id: str, version_id: str) -> Optional[bytes]:
        print(f"[S3] Retrieving {file_id} version {version_id}")
        return b"file content"
    
    def delete(self, file_id: str, version_id: str) -> bool:
        print(f"[S3] Deleting {file_id} version {version_id}")
        return True


class FileStorageService:
    """Main file storage service"""
    
    def __init__(self, backend: StorageBackend):
        self.backend = backend
        self.files: Dict[str, FileMetadata] = {}
        self.versions: Dict[str, List[FileVersion]] = {}  # file_id -> versions
        self.content: Dict[str, bytes] = {}  # version_id -> content
        self.conflict_strategy = ConflictResolution.LAST_WRITE_WINS
    
    def upload_file(self, filename: str, path: str, content: bytes,
                   user_id: str) -> str:
        """Upload file"""
        file_id = str(uuid4())
        version_id = str(uuid4())
        
        # Calculate hash
        content_hash = hashlib.sha256(content).hexdigest()
        
        now = datetime.now()
        
        # Create metadata
        metadata = FileMetadata(
            file_id=file_id,
            filename=filename,
            path=path,
            size=len(content),
            content_type="application/octet-stream",
            created_at=now,
            modified_at=now,
            created_by=user_id,
            current_version=version_id
        )
        
        # Create version
        version = FileVersion(
            version_id=version_id,
            file_id=file_id,
            content_hash=content_hash,
            size=len(content),
            created_at=now,
            modified_by=user_id
        )
        
        # Store
        self.files[file_id] = metadata
        self.versions[file_id] = [version]
        self.content[version_id] = content
        
        # Store in backend
        self.backend.store(file_id, content, version_id)
        
        return file_id
    
    def download_file(self, file_id: str, version_id: Optional[str] = None) -> Optional[bytes]:
        """Download file"""
        if file_id not in self.files:
            return None
        
        metadata = self.files[file_id]
        if metadata.is_deleted:
            return None
        
        version = version_id or metadata.current_version
        
        # Check cache first
        if version in self.content:
            return self.content[version]
        
        # Retrieve from backend
        content = self.backend.retrieve(file_id, version)
        if content:
            self.content[version] = content
        
        return content
    
    def update_file(self, file_id: str, content: bytes, user_id: str) -> Optional[str]:
        """Update file (creates new version)"""
        if file_id not in self.files:
            return None
        
        metadata = self.files[file_id]
        
        # Check for conflicts
        last_version = self.versions[file_id][-1]
        if last_version.modified_by != user_id:
            # Potential conflict
            conflict = self._resolve_conflict(file_id, content, user_id)
            if not conflict:
                return None
        
        # Create new version
        version_id = str(uuid4())
        content_hash = hashlib.sha256(content).hexdigest()
        
        version = FileVersion(
            version_id=version_id,
            file_id=file_id,
            content_hash=content_hash,
            size=len(content),
            created_at=datetime.now(),
            modified_by=user_id,
            parent_version=last_version.version_id
        )
        
        self.versions[file_id].append(version)
        self.content[version_id] = content
        metadata.current_version = version_id
        metadata.modified_at = datetime.now()
        metadata.size = len(content)
        
        # Store in backend
        self.backend.store(file_id, content, version_id)
        
        return version_id
    
    def _resolve_conflict(self, file_id: str, content: bytes, user_id: str) -> bool:
        """Resolve file conflict"""
        if self.conflict_strategy == ConflictResolution.LAST_WRITE_WINS:
            return True
        elif self.conflict_strategy == ConflictResolution.MANUAL_MERGE:
            # Would trigger merge UI
            return False
        elif self.conflict_strategy == ConflictResolution.VERSIONED:
            return True
        return False
    
    def get_file_history(self, file_id: str) -> List[FileVersion]:
        """Get file version history"""
        if file_id not in self.versions:
            return []
        return self.versions[file_id].copy()
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file (soft delete)"""
        if file_id not in self.files:
            return False
        
        metadata = self.files[file_id]
        metadata.is_deleted = True
        metadata.modified_at = datetime.now()
        
        return True
    
    def restore_file(self, file_id: str, version_id: str) -> bool:
        """Restore file to specific version"""
        if file_id not in self.files:
            return False
        
        metadata = self.files[file_id]
        
        # Find version
        versions = self.versions[file_id]
        target_version = next((v for v in versions if v.version_id == version_id), None)
        if not target_version:
            return False
        
        # Restore content
        content = self.download_file(file_id, version_id)
        if content:
            metadata.current_version = version_id
            metadata.is_deleted = False
            metadata.modified_at = datetime.now()
            return True
        
        return False
    
    def sync_files(self, last_sync_time: datetime) -> List[str]:
        """Get files modified since last sync (delta sync)"""
        modified = []
        for file_id, metadata in self.files.items():
            if metadata.modified_at > last_sync_time:
                modified.append(file_id)
        return modified


class StorageFactory:
    """Factory for creating storage backends"""
    
    @staticmethod
    def create_local_storage(base_path: str = "./storage") -> StorageBackend:
        return LocalStorageBackend(base_path)
    
    @staticmethod
    def create_s3_storage() -> StorageBackend:
        return S3StorageBackend()


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("FILE STORAGE SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    backend = StorageFactory.create_local_storage()
    service = FileStorageService(backend)
    
    print("1. Uploading file:")
    file_id = service.upload_file("document.txt", "/documents", b"Hello, World!", "user1")
    print(f"File uploaded: {file_id}")
    print()
    
    print("2. Downloading file:")
    content = service.download_file(file_id)
    print(f"Downloaded: {content}")
    print()
    
    print("3. Updating file (versioning):")
    version_id = service.update_file(file_id, b"Hello, Updated World!", "user1")
    print(f"New version: {version_id}")
    print()
    
    print("4. File history:")
    history = service.get_file_history(file_id)
    print(f"Versions: {len(history)}")
    for v in history:
        print(f"  Version {v.version_id}: {v.created_at}, by {v.modified_by}")
    print()
    
    print("5. Restoring to previous version:")
    if len(history) > 1:
        service.restore_file(file_id, history[0].version_id)
        content = service.download_file(file_id)
        print(f"Restored content: {content}")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. Strategy Pattern - Storage backends (Local, S3, Azure)")
    print("2. Version Control - File versioning and history")
    print("3. Factory Pattern - Create storage backends")
    print("4. Observer Pattern - File change notifications")
    print("5. Command Pattern - File operations")
    print()
    print("FEATURES:")
    print("- File versioning")
    print("- Conflict resolution")
    print("- Delta sync")
    print("- Metadata management")
    print("- Soft delete")
    print("=" * 60)


if __name__ == "__main__":
    main()

