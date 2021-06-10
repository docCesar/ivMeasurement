from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import pyqtgraph as pg
import pyvisa
import numpy as np
from time import sleep
from win32process import SuspendThread, ResumeThread
import matplotlib.pyplot as plt 

from Contents import ivMeasurement_ui
from Contents import ioController
from Contents import Instruments

class MainWidget(QtWidgets.QMainWindow, ivMeasurement_ui.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWidget, self).__init__(parent)
        self.setupUi(self)
        self.runing = False
        self.hold = False
        self.ioController = None
        self.rm = pyvisa.ResourceManager()
        self.rmList = self.rm.list_resources()
        self.cbCurrent.addItems(Instruments.inst_current())
        self.cbVolt.addItems(Instruments.inst_volt())
        self.cbGpibCurrent.addItems(self.rmList)
        self.cbGpibVolt.addItems(self.rmList)
        self.dataPointsI = np.array([0])
        self.dataPointsV = np.array([0])
        self.dataPointsVStds = np.array([0])
        self.displayDataX = np.array([0])
        self.displayDataY = np.array([0])

        self.plot = self.graphMonitor.addPlot()
        self.curve = self.plot.plot(self.displayDataX, self.displayDataY, symbolBrush=(0,114,189), symbolPen='w')
        self.plot.showGrid(x=True, y=True)
        styles = {'color': '#FFF', 'font-size': '24pt'}
        self.plot.setLabel(axis='left',text='V',units='V', **styles)
        self.plot.setLabel(axis='bottom',text='I',units='A', **styles) 
        self.plot.setLabel(axis='right',showValues=False) 
        self.plot.setLabel(axis='top',showValues=False) 
        font=QtGui.QFont()
        font.setPixelSize(25)
        self.plot.getAxis("bottom").setStyle(tickFont = font)
        self.plot.getAxis("left").setStyle(tickFont = font)
        self.plot.getAxis("top").setStyle(showValues=False)
        self.plot.getAxis("right").setStyle(showValues=False)

        def refreshData():
            if not self.hold:
                self.curve.setData(self.displayDataX, self.displayDataY)
                # if self.displayDataY.shape[0] > 1:
                if self.runing:
                    tagNonzero = self.displayDataX.nonzero()
                    resistance = np.absolute(self.displayDataY[tagNonzero]).mean() / np.absolute(self.displayDataX[tagNonzero]).mean()
                    self.lbResistance.setText("R = %.4f Ω" % resistance)
                    rangeX = max(self.displayDataX.min(), self.displayDataX.max(), key=abs)
                    rangeY = max(self.displayDataY.min(), self.displayDataY.max(), key=abs)
                    if not (rangeX * rangeY) == 0:
                        self.plot.setXRange(-rangeX, rangeX)
                        self.plot.setYRange(-rangeY, rangeY)

        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(refreshData)
        self.timer.start(200)

        
    def refresh(self):
        self.currentSource = Instruments.list_resources(self.cbCurrent.currentText(), self.cbGpibCurrent.currentText())
        self.voltSource = Instruments.list_resources(self.cbVolt.currentText(), self.cbGpibVolt.currentText())
        if self.ipCurrent.text() == '':
            QMessageBox.warning(self, "ERROR", "Wrong input I_max value", QMessageBox.Ok) 
            return
        else:
            self.currentMax = float(self.ipCurrent.text())
        if self.ipDeltaCurrent.text() == '':
            QMessageBox.warning(self, "ERROR", "Wrong input Delta I value", QMessageBox.Ok) 
            return
        else:
            self.currentDelta = float(self.ipDeltaCurrent.text())
        self.dataPointsI = np.array([0])
        self.dataPointsV = np.array([0])
        self.dataPointsVStds = np.array([0])
        self.displayDataX = np.array([0])
        self.displayDataY = np.array([0])
        self.lbResistance.setText("R = 0 Ω")
        self.pbStart.setEnabled(True)

    def setToIdle(self):
        if self.ioController != None:
            if not self.ioController.isFinished():
                self.ioController.terminate()
                assert self.ioController.wait(1000)
        self.runing = False

    def resetRuning(self):
        self.pbStart.setEnabled(True)
        self.runing = False

    def creatDataSet(self, size):
        self.dataPointsI = np.zeros(size, dtype=np.float64)
        self.dataPointsV = np.zeros(size, dtype=np.float64)
        self.dataPointsVStds = np.zeros(size, dtype=np.float64)

    def updateData(self, vals):
        self.dataPointsI[vals[0]] = vals[1]
        self.dataPointsV[vals[0]] = vals[2]
        self.dataPointsVStds[vals[0]] = vals[3]

    def displayMonitor(self):
        if self.hold == False:
            self.displayDataX = self.dataPointsI
            self.displayDataY = self.dataPointsV

    def on_pbStop_released(self):
        if self.ioController != None:
            if not self.ioController.isFinished():
                self.ioController.terminate()
                assert self.ioController.wait(1000)
        self.refresh()
        self.dataPointsI = np.zeros(1)
        self.dataPointsV = np.zeros(1)
        self.ioController = ioController.IOController((self.currentSource, self.voltSource),"reset", self)
        self.ioController.finished.connect(self.setToIdle)  
        self.ioController.start()

    def on_pbStart_released(self):
        if self.ioController != None:
            if not self.ioController.isFinished():
                self.ioController.terminate()
                assert self.ioController.wait(1000)
        self.setToIdle()
        self.runing = True
        self.refresh()
        self.pbStart.setEnabled(False)
        self.ioController = ioController.IOController((self.currentSource, self.voltSource),"measure", self, imax=self.currentMax, di=self.currentDelta)
        self.ioController.updateInformer.connect(self.updateData)
        self.ioController.dispInformer.connect(self.displayMonitor)
        self.ioController.sizeInformer.connect(self.creatDataSet)
        self.ioController.finished.connect(self.resetRuning)
        self.ioController.start()

    def on_pbHold_released(self):
        self.hold = not self.hold

    def on_pbPause_released(self):
        if self.ioController != None:
            if self.ioController.handle == -1:
                return print('Handle is wrong')
            self.runing = not self.runing
            if self.runing == False:
                SuspendThread(self.ioController.handle)
            else:
                ResumeThread(self.ioController.handle)
        else:
            return print('Measurement is not runing')

    def on_pbExportPlot_released(self):
        if self.dataPointsV.shape[0] <= 1:
            QMessageBox.warning(self, "ERROR", "No data", QMessageBox.Ok) 
            return
        else:
            currentPoint = self.dataPointsI
            voltPoint = self.dataPointsV
            yerr = self.dataPointsVStds

        fitFunc = np.polyfit(currentPoint, voltPoint, 1)
        resistance = fitFunc[0]
        fitCur = np.poly1d(fitFunc)(currentPoint)
        fig, ax = plt.subplots()
        p1 = plt.errorbar(currentPoint, voltPoint, yerr=yerr, label="Data Points", capsize=4, marker='o', linestyle='')
        p2 = plt.plot(currentPoint, fitCur, 'r--', label="Fitting Curve")
        plt.xlabel("Current (mA)", fontsize='xx-large')
        plt.ylabel("Voltage (mV)", fontsize='xx-large')
        plt.xticks(fontsize='large')
        plt.yticks(fontsize='large')
        plt.legend(bbox_to_anchor=(1, 0), loc='lower right')
        textStr = r'R = %.2f $\Omega$' % resistance
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.05, 0.95, textStr, transform=ax.transAxes, fontsize=18,
                verticalalignment='top', bbox=props)
        plt.show()
        
    def on_pbExportData_released(self):
        filename, filetype =QFileDialog.getSaveFileName(self, 
                                                        'Save Data', 
                                                        'dataTest', 
                                                        'Text Files (*.txt);;CSV Files (*.csv);;Numpy Files (*.npz)')
        if filetype == 'Numpy Files (*.npz)':
            np.savez(filename, Current=self.dataPointsI, Voltage=self.dataPointsV, stdS=self.dataPointsVStds)
        elif filetype == 'Text Files (*.txt)':
            np.savetxt(filename, np.array([self.dataPointsI, self.dataPointsV, self.dataPointsVStds]).transpose(),delimiter=",",newline='\n',header='Current (A),Voltage (V),Std.s')
        elif filetype == 'CSV Files (*.csv)':
            np.savetxt(filename, np.array([self.dataPointsI, self.dataPointsV, self.dataPointsVStds]).transpose(),delimiter=",",newline='\n',header='Current (A),Voltage (V),Std.s')
        else:
            QMessageBox.warning(self, "ERROR", "Wrong files type", QMessageBox.Ok)




