#!/usr/bin/env python
"""
    Unit test cases for p2654model.
    Copyright (C) 2020  Bradford G. Van Treuren

    Unit test cases for p2654model.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

__authors__ = ["Bradford G. Van Treuren"]
__contact__ = "bradvt59@gmail.com"
__copyright__ = "Copyright 2020, VT Enterprises Consulting Services"
__credits__ = ["Bradford G. Van Treuren"]
__date__ = "2020/09/28"
__deprecated__ = False
__email__ = "bradvt59@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "Bradford G. Van Treuren"
__status__ = "Alpha/Experimental"
__version__ = "0.0.1"


import unittest
from time import sleep

from myhdl import intbv

from drivers.ate.atesim import ATE, JTAGController
from p2654model.scheduler.Scheduler import SchedulerFactory
from p2654model.assembly.ScanRegister import ScanRegister
from p2654model.interface.JTAGAccessInterface import JTAGAccessInterface
from p2654model.interface.SCANAccessInterface import SCANAccessInterface


class MyTestCase(unittest.TestCase):
    def configure_model(self):
        topology = self.scheduler.topology
        ir = topology.defineScanRegister("IR", ScanRegister.Direction.READ_WRITE, "IR", 8, intbv('11111111'))
        bypass = topology.defineScanRegister("BYPASS", ScanRegister.Direction.READ_WRITE, "BYPASS", 1, intbv('0'))
        bsr = topology.defineScanRegister("BSR", "BSR", ScanRegister.Direction.READ_WRITE, 18,
                                          intbv('000000000000000000'))
        m1 = topology.defineScanMux("M1", "TAP_DRMUX", ir,
                                    [("BYPASS", intbv('11111111'), bypass), ("SAMPLE", intbv('00000010'), bsr), ("EXTEST", intbv('00000000'), bsr)])
        u1 = topology.defineTAP("U1", "sn74abt8244a", ir, m1)
        jc1 = topology.defineJTAGControllerAssembly("JC1", "JTAG", self.jc, u1)
        ai1 = SCANAccessInterface()
        bypass.set_client_interface(ai1)
        bsr.set_client_interface(ai1)
        m1.set_host_interface(ai1)
        ai2 = SCANAccessInterface()
        ir.set_client_interface(ai2)
        m1.set_client_interface(ai2)
        u1.set_host_interface(ai2)
        ai3 = JTAGAccessInterface()
        u1.set_client_interface(ai3)
        jc1.set_host_interface(ai3)
        topology.top = jc1

    # def setUp(self):
    #     ip = "127.0.0.1"
    #     port = 5023
    #     self.ate_inst = ATE(ip=ip, port=port)
    #     sleep(0.05)
    #     self.ate_inst.connect("JTAGBoard1")
    #     sleep(0.05)
    #     self.jc = JTAGController(self.ate_inst)
    #     sleep(1)
    #     self.scheduler = SchedulerFactory.get_scheduler(max_aging=2)
    #     self.configure_model()
    #
    # def tearDown(self):
    #     self.ate_inst.close()
    #
    def test_JTAGBoard1Board(self):
        ip = "127.0.0.1"
        port = 5023
        self.ate_inst = ATE(ip=ip, port=port)
        sleep(0.05)
        self.ate_inst.connect("P2654Board1")
        # self.ate_inst.connect("SPITest")
        sleep(0.05)
        self.jc = JTAGController(self.ate_inst)
        sleep(1)
        self.scheduler = SchedulerFactory.get_scheduler(max_aging=2)
        self.configure_model()
        self.scheduler.topology.show()
        self.scheduler.start()
        self.scheduler.write("JC1.U1.IR", intbv('11111111'))
        self.scheduler.apply()
        self.scheduler.write("JC1.U1.IR", intbv('00000010'))
        self.scheduler.apply()
        self.scheduler.write("JC1.U1.BSR", intbv('000101010101010101'))
        self.scheduler.apply()
        self.scheduler.write("JC1.U1.IR", intbv('00000000'))
        self.scheduler.apply()
        self.scheduler.write_read("JC1.U1.BSR", intbv('000101010101010101'))
        self.scheduler.apply()
        value = self.scheduler.read("JC1.U1.BSR")
        print("value = {:s}\n".format(str(value)))
        # self.assertTrue(value == intbv('000101010101010101'))
        self.assertTrue(value == intbv('000000000000000000'))
        self.scheduler.write_read("JC1.U1.BSR", intbv('000000000000000000'))
        self.scheduler.apply()
        self.scheduler.write_read("JC1.U1.BSR", intbv('001000000010000000'))
        self.scheduler.apply()
        self.scheduler.write_read("JC1.U1.BSR", intbv('000100000001000000'))
        self.scheduler.apply()
        self.scheduler.write_read("JC1.U1.BSR", intbv('000010000000100000'))
        self.scheduler.apply()
        self.scheduler.write_read("JC1.U1.BSR", intbv('000001000000010000'))
        self.scheduler.apply()
        self.scheduler.write_read("JC1.U1.BSR", intbv('000000100000001000'))
        self.scheduler.apply()
        self.scheduler.write_read("JC1.U1.BSR", intbv('000000010000000100'))
        self.scheduler.apply()
        self.scheduler.write_read("JC1.U1.BSR", intbv('000000001000000010'))
        self.scheduler.apply()
        self.scheduler.write_read("JC1.U1.BSR", intbv('000000000100000001'))
        self.scheduler.apply()
        self.scheduler.write_read("JC1.U1.BSR", intbv('000000000000000000'))
        self.scheduler.apply()
        self.scheduler.stop()
        self.ate_inst.close()


if __name__ == '__main__':
    unittest.main()
