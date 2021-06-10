from PyQt5 import QtCore
from PyQt5.QtCore import QThread
import numpy as np
import ctypes
from pyqtgraph.graphicsItems.ROI import Handle
import win32con

class IOController(QtCore.QThread):
    updateInformer = QtCore.pyqtSignal(list)
    dispInformer = QtCore.pyqtSignal()
    sizeInformer = QtCore.pyqtSignal(int)
    handle = -1 
    def __init__(self, inst, order, parent, **kw):
        super().__init__(parent)
        self.inst = inst
        self.order = order
        self.currentSource = inst[0]
        self.voltSource = inst[1]
        self.args = kw

    def run(self):
        try:
            self.handle = ctypes.windll.kernel32.OpenThread(
                win32con.PROCESS_ALL_ACCESS, False, int(QThread.currentThreadId()))
        except Exception as e:
            print('get thread handle failed', e)

        if self.order == "reset":
            self.reset()
            return
        if self.order == "measure":
            self.measure(self.args)
            return

    def reset(self):
        for item in self.inst:
            item.reset()
        self.msleep(100)
        return

    def measure(self, kw):
        if 'imax' in kw:
            imax = kw['imax']
        else:
            print('No Imax parameter, use the defaut value.')
            imax = 0.1
        if 'di' in kw:
            di = kw['di']
        else:
            print('No Delta I parameter, use the defaut value.')
            di = 0.01
        self.currentSource.settings(currentMax=imax, internal_in_mA=di)
        self.voltSource.settings()
        points = int(imax/di) + 1
        tem = np.linspace(0, imax, num=points, endpoint=True, dtype=np.float64)
        currentPoint = np.hstack((tem, np.flipud(tem), -tem, -np.flipud(tem)))
        voltPoint = np.zeros(np.shape(currentPoint), dtype=np.float64)
        voltPointStds = np.zeros(np.shape(currentPoint), dtype=np.float64)
        self.sizeInformer.emit(np.shape(currentPoint)[0])
        for tag, current in enumerate(currentPoint):
            self.msleep(100)
            self.currentSource.start(current)
            self.voltSource.start()
            voltPoint[tag], voltPointStds[tag] = self.voltSource.get()
            self.updateInformer.emit([tag, currentPoint[tag]/1000, voltPoint[tag], voltPointStds[tag]])
            self.dispInformer.emit()
        self.voltSource.reset()
        self.currentSource.stop()
        self.currentSource.reset()
        return