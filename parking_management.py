from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass

class Observer(ABC):


    @abstractmethod
    def update(self, event_type: str, message: str):
        pass

class ParkingEventNotifier:

    def __init__(self):
        self._observers: List[Observer] = []

    def attach(self, observer: Observer):
        if observer not in self._observers: 
            self._observers.append(observer)

    def detach(self, observer: Observer):
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event_type: str, message: str):
        for observer in self._observers:
            observer.update(event_type, message)


class ParkingDisplayBoard(Observer):

    def __init__(self):
        self.availability: Dict[str, int] = {}
    
    def update(self, event_type: str, message: str):
        if event_type == "PARKING_UPDATE":
            print(f"[Display Board] {message}")
            self._update_availability(message)
    
    def _update_availability(self, message: str):
        if "available" in message.lower():
            self.availability[message.split(" ")[1]] += 1
        else:
            self.availability[message.split(" ")[1]] -= 1


class SMSNotifier(Observer):
    def update(self, event_type: str, message: str):
        if event_type in ["PARKING_FULL", "VEHICLE_PARKED", "PAYMENT_RECEIVED"]:
            print(f"[SMS] {message}")