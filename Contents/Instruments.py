#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pyvisa
import numpy as np
from time import sleep


# Index. Need to be updated when new models are added.
def inst_volt():
    return ("Agilent 34411A",)

def inst_current():
    return ("Yokogawa GS200",)

def list_resources(name, address):
    if not isinstance(address, str):
        print("Wrong address")
        return
    dict = {
        "Agilent 34411A": (Agilent34411A(address=address)), 
        "Yokogawa GS200": (YokogawaGS200(address=address))
    }
    return dict[name]
    

# Voltage Meter

class Agilent34411A(object):
    def __init__(self, address):
        self.__name = "Agilent 34411A"
        self.__type = "Voltage Meter"
        self.address = address          # Should be a string
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(self.address)

    def get_name(self):
        return self.__name

    def get_type(self):
        return self.__type

    def reset(self):
        self.inst.write("*RST; SYSTem:PRESet; *CLS")

    def settings(self, internal_in_s=0.1, trigDel_in_s=0.005, number_of_readings = 5):
        self.inst.write("SAMP:SOUR TIM")
        self.inst.write("SAMP:COUN %d" % number_of_readings)
        self.inst.write("SAMP:TIM %d" % internal_in_s)
        self.inst.write("TRIGger:SOURce BUS")
        self.inst.write("TRIG:DEL %f" % trigDel_in_s)
        self.inst.write("SYST:BEEP:STAT OFF")
        self.waitTime = trigDel_in_s + internal_in_s * number_of_readings + 0.1

    def start(self):                    # Should be used after settings
        self.inst.write("INIT")
        self.inst.write("*TRG")
        sleep(self.waitTime)
        
    def get(self):
        data = self.inst.query("FETC?")
        dataTem = data.replace('\n','').split(',')
        dataTem = np.array(dataTem).astype(float)
        voltPoint = np.mean(dataTem)    
        voltPointStds = np.std(dataTem, ddof = 1)
        return voltPoint, voltPointStds

    def close(self):
        self.inst.write("*RST; SYSTem:PRESet; *CLS")


# Current Source

class YokogawaGS200(object):
    def __init__(self, address):
        self.__name = "Yokogawa GS200"
        self.__type = "Current Source"
        self.address = address          # Should be a string
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(self.address)

    def get_name(self):
        return self.__name

    def get_type(self):
        return self.__type

    def reset(self):
        self.inst.write("*RST; *CLS")

    def stop(self):
        self.inst.write(":SOUR:LEV:FIX 0")
        self.inst.write(":SOUR:FUNC CURR; :OUTP OFF")

    def settings(self, currentMax=0.01, internal_in_mA=0.001):
        points = int(currentMax/internal_in_mA) + 1
        tem = np.linspace(0, currentMax, num=points, endpoint=True, dtype=np.float)
        self.currentPoint = np.hstack((tem, np.flipud(tem), -tem, -np.flipud(tem)))
        self.inst.write(":SOUR:PROT:CURR 10mA")
        self.inst.write(":SOUR:FUNC CURR; :OUTP ON")

    def start(self, current):           # Should be used after settings
        self.inst.write(":SOUR:LEV:FIX %fmA" % current)
        sleep(0.1)
        readValue = self.inst.query(":SOUR:LEV:FIX?")
        readValue = np.float(readValue.replace('\n', ''))
        if abs(current - readValue * 1000) > abs(current * 0.01):
            print("Current value error")
            print("current = %f" % current)
            print("readValue = %f" % (readValue * 1000))
            return

    def close(self):
        self.inst.write(":SOUR:LEV:FIX 0")
        self.inst.write(":SOUR:FUNC CURR; :OUTP OFF")
        self.inst.write("*RST; *CLS")
