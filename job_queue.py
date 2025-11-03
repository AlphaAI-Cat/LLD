"""
Notification Scheduler / Job Queue
==================================

Core Design: System to schedule and execute jobs/notifications asynchronously.

Design Patterns & Strategies Used:
1. Priority Queue Pattern - Job prioritization
2. Strategy Pattern - Different job execution strategies
3. Observer Pattern - Job status notifications
4. Factory Pattern - Create jobs
5. Template Method - Job execution workflow
6. Thread Pool Pattern - Concurrent job execution

Features:
- Priority-based job scheduling
- Retry mechanism
- Job status tracking
- Scheduled jobs (cron-like)
- One-time jobs
- Job cancellation
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Callable, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from queue import PriorityQueue
from threading import Thread, Lock
import time
from uuid import uuid4


class JobPriority(Enum):
    LOW = 3
    MEDIUM = 2
    HIGH = 1
    URGENT = 0


class JobStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(Enum):
    ONCE = "ONCE"
    SCHEDULED = "SCHEDULED"
    RECURRING = "RECURRING"


@dataclass
class Job:
    """Job entity"""
    job_id: str
    name: str
    task: Callable
    priority: JobPriority
    job_type: JobType
    scheduled_time: datetime
    created_at: datetime = field(default_factory=datetime.now)
    status: JobStatus = JobStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    interval: Optional[timedelta] = None  # For recurring jobs
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    
    def __lt__(self, other):
        """For priority queue"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.scheduled_time < other.scheduled_time


class JobExecutor(ABC):
    """Job executor strategy"""
    
    @abstractmethod
    def execute(self, job: Job) -> bool:
        pass


class ImmediateExecutor(JobExecutor):
    """Execute job immediately"""
    
    def execute(self, job: Job) -> bool:
        try:
            result = job.task(*job.args, **job.kwargs)
            return True
        except Exception as e:
            print(f"Job {job.job_id} failed: {e}")
            return False


class DelayedExecutor(JobExecutor):
    """Execute job with delay"""
    
    def __init__(self, delay_seconds: float = 0.0):
        self.delay_seconds = delay_seconds
    
    def execute(self, job: Job) -> bool:
        time.sleep(self.delay_seconds)
        try:
            result = job.task(*job.args, **job.kwargs)
            return True
        except Exception as e:
            print(f"Job {job.job_id} failed: {e}")
            return False


class JobObserver(ABC):
    """Observer for job events"""
    
    @abstractmethod
    def on_job_completed(self, job: Job):
        pass
    
    @abstractmethod
    def on_job_failed(self, job: Job):
        pass


class JobLogger(JobObserver):
    """Log job events"""
    
    def on_job_completed(self, job: Job):
        print(f"[JobLogger] Job {job.name} ({job.job_id}) completed")
    
    def on_job_failed(self, job: Job):
        print(f"[JobLogger] Job {job.name} ({job.job_id}) failed")


class JobScheduler:
    """Job scheduler service"""
    
    def __init__(self, worker_count: int = 3):
        self.job_queue = PriorityQueue()
        self.jobs: Dict[str, Job] = {}
        self.running = False
        self.workers: List[Thread] = []
        self.worker_count = worker_count
        self.executor: JobExecutor = ImmediateExecutor()
        self.observers: List[JobObserver] = []
        self.lock = Lock()
    
    def set_executor(self, executor: JobExecutor):
        """Set job executor"""
        self.executor = executor
    
    def add_observer(self, observer: JobObserver):
        """Add observer"""
        self.observers.append(observer)
    
    def schedule_job(self, name: str, task: Callable, scheduled_time: datetime,
                     priority: JobPriority = JobPriority.MEDIUM,
                     job_type: JobType = JobType.ONCE,
                     interval: Optional[timedelta] = None,
                     max_retries: int = 3,
                     args: tuple = (),
                     kwargs: dict = None) -> str:
        """Schedule a job"""
        job_id = str(uuid4())
        
        job = Job(
            job_id=job_id,
            name=name,
            task=task,
            priority=priority,
            job_type=job_type,
            scheduled_time=scheduled_time,
            interval=interval,
            max_retries=max_retries,
            args=args,
            kwargs=kwargs or {}
        )
        
        with self.lock:
            self.jobs[job_id] = job
        
        if scheduled_time <= datetime.now():
            # Schedule immediately
            self.job_queue.put(job)
        else:
            # Will be added by scheduler thread
            pass
        
        return job_id
    
    def schedule_recurring_job(self, name: str, task: Callable,
                              interval: timedelta,
                              priority: JobPriority = JobPriority.MEDIUM,
                              max_retries: int = 3,
                              args: tuple = (),
                              kwargs: dict = None) -> str:
        """Schedule recurring job"""
        return self.schedule_job(
            name, task, datetime.now(),
            priority=priority,
            job_type=JobType.RECURRING,
            interval=interval,
            max_retries=max_retries,
            args=args,
            kwargs=kwargs
        )
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel job"""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if job.status in [JobStatus.PENDING, JobStatus.RUNNING]:
                    job.status = JobStatus.CANCELLED
                    return True
        return False
    
    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get job status"""
        with self.lock:
            if job_id in self.jobs:
                return self.jobs[job_id].status
        return None
    
    def start(self):
        """Start scheduler"""
        self.running = True
        
        # Start scheduler thread (checks for scheduled jobs)
        scheduler_thread = Thread(target=self._scheduler_loop, daemon=True)
        scheduler_thread.start()
        
        # Start worker threads
        for i in range(self.worker_count):
            worker = Thread(target=self._worker_loop, daemon=True, name=f"Worker-{i+1}")
            worker.start()
            self.workers.append(worker)
    
    def _scheduler_loop(self):
        """Scheduler loop - adds scheduled jobs to queue"""
        while self.running:
            with self.lock:
                now = datetime.now()
                for job in self.jobs.values():
                    if (job.status == JobStatus.PENDING and 
                        job.scheduled_time <= now):
                        self.job_queue.put(job)
            time.sleep(1)  # Check every second
    
    def _worker_loop(self):
        """Worker loop - executes jobs"""
        while self.running:
            try:
                job = self.job_queue.get(timeout=1)
                
                if job.status == JobStatus.CANCELLED:
                    continue
                
                job.status = JobStatus.RUNNING
                
                # Execute job
                success = self.executor.execute(job)
                
                if success:
                    job.status = JobStatus.COMPLETED
                    for observer in self.observers:
                        observer.on_job_completed(job)
                    
                    # Reschedule if recurring
                    if job.job_type == JobType.RECURRING and job.interval:
                        job.status = JobStatus.PENDING
                        job.scheduled_time = datetime.now() + job.interval
                else:
                    # Retry logic
                    if job.retry_count < job.max_retries:
                        job.retry_count += 1
                        job.status = JobStatus.PENDING
                        job.scheduled_time = datetime.now() + timedelta(seconds=5)
                    else:
                        job.status = JobStatus.FAILED
                        for observer in self.observers:
                            observer.on_job_failed(job)
                
            except:
                pass
    
    def stop(self):
        """Stop scheduler"""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=5)


# ==================== DEMONSTRATION ====================

def sample_task(message: str):
    """Sample task function"""
    print(f"Executing: {message}")
    return True

def failing_task():
    """Task that fails"""
    raise Exception("Task failed")

def main():
    print("=" * 60)
    print("JOB QUEUE SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    scheduler = JobScheduler(worker_count=2)
    scheduler.add_observer(JobLogger())
    scheduler.start()
    
    print("1. Scheduling immediate jobs:")
    job1_id = scheduler.schedule_job(
        "Task 1", sample_task, datetime.now(),
        priority=JobPriority.HIGH,
        kwargs={"message": "High priority task"}
    )
    job2_id = scheduler.schedule_job(
        "Task 2", sample_task, datetime.now(),
        priority=JobPriority.MEDIUM,
        kwargs={"message": "Medium priority task"}
    )
    print(f"Scheduled jobs: {job1_id}, {job2_id}")
    print()
    
    print("2. Scheduling future job:")
    future_time = datetime.now() + timedelta(seconds=2)
    job3_id = scheduler.schedule_job(
        "Task 3", sample_task, future_time,
        priority=JobPriority.LOW,
        kwargs={"message": "Future task"}
    )
    print(f"Scheduled future job: {job3_id}")
    print()
    
    print("3. Scheduling recurring job:")
    job4_id = scheduler.schedule_recurring_job(
        "Recurring Task", sample_task,
        interval=timedelta(seconds=3),
        kwargs={"message": "Recurring task"}
    )
    print(f"Scheduled recurring job: {job4_id}")
    print()
    
    print("4. Waiting for jobs to execute...")
    time.sleep(5)
    print()
    
    print("5. Job statuses:")
    for job_id in [job1_id, job2_id, job3_id, job4_id]:
        status = scheduler.get_job_status(job_id)
        print(f"Job {job_id[:8]}...: {status.value if status else 'Unknown'}")
    print()
    
    scheduler.stop()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. Priority Queue - Job prioritization")
    print("2. Strategy Pattern - Different executors")
    print("3. Observer Pattern - Job status notifications")
    print("4. Factory Pattern - Create jobs")
    print("5. Thread Pool - Concurrent execution")
    print()
    print("FEATURES:")
    print("- Priority-based scheduling")
    print("- Retry mechanism")
    print("- Scheduled and recurring jobs")
    print("- Job cancellation")
    print("=" * 60)


if __name__ == "__main__":
    main()

