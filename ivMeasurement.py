#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File        :ivMeasurement.py
@Time        :2021/06/01 23:35:48
@Author      :César Liao
@License     :MIT LICENSE
@Copyright   :2021 César Liao. All rights reserved.
               Use of this source code is governed by a MIT-style
               license that can be found in the LICENSE file.
'''


import sys
sys.path.insert(0, '.\Contents')
from PyQt5 import QtWidgets
from Contents import MainWidget

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    mw = MainWidget.MainWidget()
    mw.show()

    exit(app.exec_())

