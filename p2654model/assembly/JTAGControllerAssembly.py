#!/usr/bin/env python
"""
    Top node of a JTAG path.
    Copyright (C) 2020  Bradford G. Van Treuren

    Top node model of a JTAG Path.  It is at this point the requests from the model that are to
    transfored are applied to the JTAG hardware driver.

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
__date__ = "2020/09/26"
__deprecated__ = False
__email__ = "bradvt59@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "Bradford G. Van Treuren"
__status__ = "Alpha/Experimental"
__version__ = "0.0.1"


import logging
from autologging import traced, logged
from myhdl import intbv

from p2654model.assembly.SuperAssembly import SuperAssembly
from p2654model.error.SchedulerError import SchedulerError
from p2654model.interface.RVF import RVF


# create logger
module_logger = logging.getLogger('P2654Model.assembly.JTAGControllerAssembly')


@logged
@traced
class JTAGControllerAssembly(SuperAssembly):
    def __init__(self, name, description, jtag_controller):
        self.logger = logging.getLogger('P2654Model.assembly.JTAGControllerAssembly.JTAGControllerAssembly')
        self.logger.info('Creating an instance of JTAGControllerAssembly')
        self.capture = False
        self.pending_count = 0
        self.pending = False
        self.rvf = None
        self.jtag_controller = jtag_controller
        SuperAssembly.__init__(self, name, description)
        cb = {"SIR": self.hcb_sir, "SIRNC": self.hcb_sirnc, "SDR": self.hcb_sdr, "SDRNC": self.hcb_sdrnc}
        self.hcb_update(cb)

    def apply(self):
        self.capture = False
        self.pending_count = 0
        seg = self.depth()
        while seg is not None:
            seg.apply()
            seg = seg.breadth()
        if self.pending_count > 1:
            raise SchedulerError("Multiple competing paths detected.")
        if self.pending:
            self.local_access_mutex.acquire()
            uid = self.rvf.uid
            command = self.rvf.command
            payload = self.rvf.payload
            self.pending = False
            self.local_access_mutex.release()
            self.logger.debug("self.rvf.command = {:s}.\n".format(command))
            if command == "SIR":
                self.logger.debug("Calling scan_ir().")
                tdo = self.jtag_controller.scan_ir(len(payload),
                                                   str(payload))  # payload must be an intbv type
                resp = RVF()
                resp.command = "SIR"
                resp.uid = uid
                self.logger.debug("SIR tdo={:s}".format(tdo))
                resp.payload = intbv(int(tdo, 16), _nrbits=len(payload))
                self.host_interface.response(resp)
            elif command == "SIRNC":
                # fmt = "{:0" + "{:d}".format((len(self.rvf.payload) + 1) // 4) + "X}"
                # print("fmt = {:s}\n".format(fmt))
                # tdi = fmt.format(int(self.rvf.payload))
                # tdi = "{0:0{1}X}".format(int(payload), (len(payload) + 1) // 4)
                tdi = str(payload)
                self.logger.debug("tdi = {:s}\n".format(tdi))
                self.jtag_controller.scan_ir(len(payload), tdi)  # payload must be an intbv type
                resp = RVF()
                resp.command = "SIRNC"
                resp.uid = self.rvf.uid
                resp.payload = intbv(0)
                self.host_interface.response(resp)
            elif command == "SDR":
                tdo = self.jtag_controller.scan_dr(len(payload),
                                                   str(payload))  # payload must be an intbv type
                resp = RVF()
                resp.command = "SDR"
                resp.uid = uid
                self.logger.debug("SDR tdo={:s}".format(tdo))
                resp.payload = intbv(int(tdo, 16), _nrbits=len(payload))
                self.host_interface.response(resp)
            elif command == "SDRNC":
                self.jtag_controller.scan_dr(len(payload),
                                             str(payload))  # payload must be an intbv type
                resp = RVF()
                resp.command = "SDRNC"
                resp.uid = uid
                resp.payload = intbv(0)
                self.host_interface.response(resp)
            else:
                raise SchedulerError("Invalid command detected. ({:s})".format(command))

    def hcb_sir(self, rvf: RVF):
        self.local_access_mutex.acquire()
        self.rvf = rvf
        self.pending = True
        self.local_access_mutex.release()

    def hcb_sirnc(self, rvf: RVF):
        self.local_access_mutex.acquire()
        self.rvf = rvf
        self.pending = True
        self.local_access_mutex.release()

    def hcb_sdr(self, rvf: RVF):
        self.local_access_mutex.acquire()
        self.rvf = rvf
        self.pending = True
        self.local_access_mutex.release()

    def hcb_sdrnc(self, rvf: RVF):
        self.local_access_mutex.acquire()
        self.rvf = rvf
        self.pending = True
        self.local_access_mutex.release()
