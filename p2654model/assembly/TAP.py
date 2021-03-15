#!/usr/bin/env python
"""
    Model of an IEEE 1149.1 TAP.
    Copyright (C) 2020  Bradford G. Van Treuren

    Model of an IEEE 1149.1 TAP.

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
__date__ = "2020/09/30"
__deprecated__ = False
__email__ = "bradvt59@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "Bradford G. Van Treuren"
__status__ = "Alpha/Experimental"
__version__ = "0.0.1"


import logging
from autologging import traced, logged

from p2654model.assembly.LinkerAssembly import LinkerAssembly
from p2654model.error.SchedulerError import SchedulerError
from p2654model.interface.RVF import RVF
from p2654model.scheduler.Scheduler import SchedulerFactory


# create logger
module_logger = logging.getLogger('P2654Model.assembly.TAP')


@logged
@traced
class TAP(LinkerAssembly):
    def __init__(self, name, description):
        self.logger = logging.getLogger('P2654Model.assembly.TAP.TAP')
        self.logger.info('Creating an instance of TAP')
        self.capture = False
        self.pending_count = 0
        self.value = None
        self.command = None
        LinkerAssembly.__init__(self, name, description, TAP.depth_next)
        cb = {"SCAN": self.hcb_scan, "CAPSCAN": self.hcb_capscan}
        self.hcb_update(cb)

    def resp_handler(self, rvf: RVF):
        self.logger.debug("TAP.resp_handler(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                    str(rvf.payload)))
        uid = rvf.uid
        resp = RVF()
        self.response_mutex.acquire()
        resp.payload = rvf.payload
        self.response_mutex.release()
        if rvf.command == "SIR":
            resp.uid = self.depth().uid
            resp.command = "CAPSCAN"
            self.host_interface.response(resp)
        elif rvf.command == "SIRNC":
            resp.uid = self.depth().uid
            resp.command = "SCAN"
            self.host_interface.response(resp)
        elif rvf.command == "SDR":
            resp.uid = self.depth().breadth().uid
            resp.command = "CAPSCAN"
            self.host_interface.response(resp)
        elif rvf.command == "SDRNC":
            resp.uid = self.depth().breadth().uid
            resp.command = "SCAN"
            self.host_interface.response(resp)
        else:
            raise SchedulerError("Invalid command received.")
        self.request_count -= 1
        if self.request_count == 0:
            pass  # Notify all requests have been satisfied
        SchedulerFactory.get_scheduler().clear_pending()

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
            wrvf = RVF()
            self.local_access_mutex.acquire()
            wrvf.uid = self.uid
            wrvf.payload = self.value
            if self.capture:
                wrvf.command = self.command
            else:
                wrvf.command = self.command
            self.client_interface.request(wrvf)
            self.request_count += 1
            self.pending = False
            self.local_access_mutex.release()

    def hcb_scan(self, rvf: RVF):
        # if not self.pending:
        self.logger.debug("TAP.hcb_scan(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                str(rvf.payload)))
        self.local_access_mutex.acquire()
        self.pending_count += 1
        self.value = rvf.payload
        if rvf.uid == self.depth().uid:  # This rvf is from the IR register
            self.command = "SIRNC"
        else:
            self.command = "SDRNC"
        self.pending = True
        self.local_access_mutex.release()
        SchedulerFactory.get_scheduler().mark_pending()

    def hcb_capscan(self, rvf: RVF):
        # if not self.pending:
        self.local_access_mutex.acquire()
        self.logger.debug("TAP.hcb_capscan(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                   str(rvf.payload)))
        self.pending_count += 1
        self.value = rvf.payload
        if rvf.uid == self.depth().uid:  # This rvf is from the IR register
            self.command = "SIR"
        else:
            self.command = "SDR"
        self.pending = True
        self.capture = True
        self.local_access_mutex.release()
        SchedulerFactory.get_scheduler().mark_pending()
