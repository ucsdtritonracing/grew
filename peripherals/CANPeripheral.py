import can
from abc import ABC, abstractmethod
from PySide6.QtCore import QObject, Slot

class CANListner(can.Listener):
    def __init__(self, func):
        super().__init__()
        self.func = func
    def on_message_received(self, msg):
        self.func(msg)

class CANPeripheral(QObject):
    def __init__(self, id, isExtended, bus, func):
        self.id = id # id identifying the peripheral
        self.isExtended = isExtended
        self.bus = bus
        self.periodics = {}
        self.state = {}
        self.txData = []
        self.listner = CANListner(func)
        self.setup() # implement to setup state 

    @Slot() 
    def setup(self):
        raise NotImplementedError("Must be implemented by subclass")
        pass # setup state dict and/or other stuff
    
    @Slot()
    def enable(self):
        raise NotImplementedError("Must be implemented by subclass")
        pass # implement to start periodics and take control from vcu

    @Slot()
    def disable(self):
        raise NotImplementedError("Must be implemented by subclass")
        pass # implement to pause periodics and hand control back to vcu
    
    @Slot()
    def enableVCU(self):
        raise NotImplementedError("Must be implemented by subclass")
        pass # implement to start periodics and take control from vcu

    @Slot()
    def disableVCU(self):
        raise NotImplementedError("Must be implemented by subclass")
        pass # implement to pause periodics and hand control back to vcu

    @Slot()
    def shutdown(self):
        raise NotImplementedError("Must be implemented by subclass")
        pass # implement to fully cleanup and hand control back to vcu
    
    def processMessage(self, msg):
        raise NotImplementedError("Must be implemented by subclass")
        pass # implement to process incoming messages and update state
    
    def getListner(self):
        return self.listner
    
    def send_message(self, data):
        # data to be passed in through GUI
        msg = can.Message(arbitration_id=self.id,
                          is_extended_id=self.isExtended,
                          data=data)
        self.bus.send(msg)

    def send_message(self, data, id, isExtended):
        # data to be passed in through GUI
        msg = can.Message(arbitration_id=id,
                          is_extended_id=isExtended,
                          data=data)
        self.bus.send(msg)

    def start_periodic(self, data, interval, name):
        if(name not in self.periodics):
            msg = can.Message(arbitration_id=self.id,
                              is_extended_id=self.isExtended,
                              data=data)
            task = self.bus.send_periodic(msg, interval) 
            self.periodics[name] = task
        else:
            print("ERROR: Periodic already started!") #find better way to do this?

    def stop_periodic(self, name):
        task = self.periodics.get(name)
        if task:
            task.stop()
            del self.periodics[name]
            
            
    def stop_all_periodics(self):
        for task in self.periodics.values():
            task.stop()
        self.periodics.clear()

    def update_periodic(self, name, data):
        task = self.periodics.get(name)
        if task:
            msg = can.Message(arbitration_id=self.id,
                              is_extended_id=self.isExtended,
                              data=data)
            task.modify_data(msg)
        else:
            print("ERROR: Periodic doesn't exist!")
    