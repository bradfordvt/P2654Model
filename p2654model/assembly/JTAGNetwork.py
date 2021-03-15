#!/usr/bin/env python
"""
    Class to model a IEEE 1149.1 JTAG network.
    Copyright (C) 2020  Bradford G. Van Treuren

    Class to model an IEEE 1149.1 JTAG network consisting of one or more JTAG devices.

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
__date__ = "2020/09/29"
__deprecated__ = False
__email__ = "bradvt59@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "Bradford G. Van Treuren"
__status__ = "Alpha/Experimental"
__version__ = "0.0.1"


from enum import Enum

import logging
from autologging import traced, logged
from myhdl import intbv, concat

from p2654model.assembly.SuperAssembly import SuperAssembly
from p2654model.description.JTAGNetworkDescription import JTAGNetworkDescription
from p2654model.error.SchedulerError import SchedulerError
from p2654model.interface.RVF import RVF
from p2654model.scheduler.Scheduler import SchedulerFactory


# create logger
module_logger = logging.getLogger('P2654Model.assembly.JTAGNetwork')


@logged
@traced
class JTAGNetwork(SuperAssembly):
    def __init__(self, name, description: JTAGNetworkDescription):
        self.logger = logging.getLogger('P2654Model.assembly.JTAGNetwork.JTAGNetwork')
        self.logger.info('Creating an instance of JTAGNetwork')
        self.__value = None  # current value of the register
        self.__read_value = None
        self.segments = None
        self.cached = False
        self.capture = False
        self.responses = None
        self.response = None
        self.data_mode = None
        SuperAssembly.__init__(self, name, description)
        self.visible = False
        self.pending = False
        cb = {"SIR": self.hcb_sir, "SIRNC": self.hcb_sirnc, "SDR": self.hcb_sdr, "SDRNC": self.hcb_sdrnc}
        self.hcb_update(cb)

    def resp_handler(self, rvf: RVF):
        self.logger.debug("JTAGNetwork.resp_handler(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                            str(rvf.payload)))
        self.response_mutex.acquire()
        self.response = rvf.payload
        self.response_mutex.release()
        i = 0
        start = 0
        end = 0
        seg = self.depth()
        while seg is not None:
            end = len(self.segments[i]) + end
            resp = RVF()
            resp.uid = seg.uid
            resp.payload = intbv(self.response[start:end])
            resp.command = rvf.command

            seg.client_interface.response(rvf)
            start = end
            i += 1
            seg = seg.breadth()
        self.request_count -= 1
        if self.request_count == 0:
            self.response_cv.notify()  # Notify all requests have been satisfied
        SchedulerFactory.get_scheduler().clear_pending()

    def __subsegment_count(self):
        seg_count = 0
        seg = self.depth()
        while seg is not None:
            seg_count += 1
            seg = seg.breadth()
        return seg_count

    def __init_segments(self):
        scsize = self.__subsegment_count()
        self.segments = []
        for i in range(scsize):
            self.segments.append(intbv(0))

    def apply(self):
        self.capture = False
        if not self.cached:
            self.__init_segments()
            self.cached = True
        seg = self.depth()
        while seg is not None:
            seg.apply()
            seg = seg.breadth()
        if self.pending:
            if self.data_mode is None:
                raise SchedulerError("Pending conflict with data_mode!")
            # Concatenate vectors together into a single vector to scan
            value = concat([v for v in self.segments])
            wrvf = RVF()
            if self.capture and self.data_mode:
                wrvf.command = "SDR"
            elif self.capture and not self.data_mode:
                wrvf.command = "SIR"
            elif self.data_mode:
                wrvf.command = "SDRNC"
            elif not self.data_mode:
                wrvf.command = "SIRNC"
            else:
                raise SchedulerError("Invalid data_mode detected.")
            wrvf.uid = self.uid
            wrvf.payload = value
            self.client_interface.request(wrvf)
            self.request_count += 1
            self.pending = False
            self.data_mode = None
            self.logger.debug("JTAGNetwork.apply(uid={:d}, command={:s}, payload={:s})\n".format(wrvf.uid, wrvf.command,
                                                                                         str(wrvf.payload)))

    def hcb_sirnc(self, rvf: RVF):
        if self.data_mode is not None and self.data_mode:
            raise SchedulerError("Conflict in scan mode!")
        self.data_mode = False
        if not self.cached:
            self.__init_segments()
            self.cached = True
        self.pending = True
        self.logger.debug("JTAGNetwork.hcb_sirnc(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                         str(rvf.payload)))
        uid = rvf.uid
        seg = self.depth()
        i = 0
        while seg is not None:
            if seg.uid == uid:
                self.segments[i] = rvf.payload  # fill in the appropriate subsegment with intbv value
                break
            seg = seg.breadth()
            i += 1
        self.data_mode = False
        SchedulerFactory.get_scheduler().mark_pending()

    def hcb_sir(self, rvf: RVF):
        if self.data_mode is not None and self.data_mode:
            raise SchedulerError("Conflict in scan mode!")
        self.data_mode = False
        if not self.cached:
            self.__init_segments()
            self.cached = True
        self.pending = True
        self.capture = True
        self.logger.debug("JTAGNetwork.hcb_sir(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                       str(rvf.payload)))
        uid = rvf.uid
        seg = self.depth()
        i = 0
        while seg is not None:
            if seg.uid == uid:
                self.segments[i] = rvf.payload  # fill in the appropriate subsegment with intbv value
                break
            seg = seg.breadth()
            i += 1
        self.data_mode = False
        SchedulerFactory.get_scheduler().mark_pending()

    def hcb_sdrnc(self, rvf: RVF):
        if self.data_mode is not None and not self.data_mode:
            raise SchedulerError("Conflict in scan mode!")
        if not self.cached:
            self.__init_segments()
            self.cached = True
        self.pending = True
        self.logger.debug("JTAGNetwork.hcb_sdrnc(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                         str(rvf.payload)))
        uid = rvf.uid
        seg = self.depth()
        i = 0
        while seg is not None:
            if seg.uid == uid:
                self.segments[i] = rvf.payload  # fill in the appropriate subsegment with intbv value
                break
            seg = seg.breadth()
            i += 1
        self.data_mode = True
        SchedulerFactory.get_scheduler().mark_pending()

    def hcb_sdr(self, rvf: RVF):
        if self.data_mode is not None and not self.data_mode:
            raise SchedulerError("Conflict in scan mode!")
        if not self.cached:
            self.__init_segments()
            self.cached = True
        self.pending = True
        self.capture = True
        self.logger.debug("JTAGNetwork.hcb_sdr(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                       str(rvf.payload)))
        uid = rvf.uid
        seg = self.depth()
        i = 0
        while seg is not None:
            if seg.uid == uid:
                self.segments[i] = rvf.payload  # fill in the appropriate subsegment with intbv value
                break
            seg = seg.breadth()
            i += 1
        self.data_mode = True
        SchedulerFactory.get_scheduler().mark_pending()
