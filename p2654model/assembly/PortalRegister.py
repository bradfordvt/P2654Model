#!/usr/bin/env python
"""
    Model for a Portal Register.
    Copyright (C) 2020  Bradford G. Van Treuren

    Model for a Portal Register.

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
from enum import Enum

from autologging import traced, logged
from myhdl import intbv

from p2654model.assembly.DataRegister import DataRegister
from p2654model.assembly.SuperAssembly import SuperAssembly
from p2654model.description.PortalRegisterDescription import PortalRegisterDescription
from p2654model.error.SchedulerError import SchedulerError
from p2654model.interface.RVF import RVF


# create logger
module_logger = logging.getLogger('P2654Model.assembly.PortalRegister')


@logged
@traced
class PortalRegister(SuperAssembly):
    def __init__(self, name, description: PortalRegisterDescription, address: intbv):
        self.logger = logging.getLogger('P2654Model.assembly.PortalRegister.PortalRegister')
        self.logger.info('Creating an instance of PortalRegister')
        self.address = address
        self.rvf = None
        self.capture = False
        self.update = False
        self.current_uid = None
        self.pending = False
        SuperAssembly.__init__(self, name, description)
        cb = {"WRITE": self.hcb_write, "READ": self.hcb_read, "WRITE_READ": self.hcb_write_read}
        self.hcb_update(cb)

    def get_address(self):
        return self.address

    def resp_handler(self, rvf: RVF):
        self.logger.debug("PortalRegister.resp_handler(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                    str(rvf.payload)))
        resp = RVF()
        self.local_access_mutex.acquire()
        resp.uid = self.current_uid
        self.local_access_mutex.release()
        resp.payload = rvf.payload
        if rvf.command == "WRITE" or rvf.command == "READ" or rvf.command == "WRITE_READ":
            resp.command = rvf.command
        elif rvf.command == "ADDRESS":
            self.response_cv.notify()
        else:
            raise SchedulerError("Invalid command received.")
        self.host_interface.response(resp)
        self.request_count -= 1
        if self.request_count == 0:
            pass  # Notify all requests have been satisfied
        from p2654model.scheduler.Scheduler import SchedulerFactory
        SchedulerFactory.get_scheduler().clear_pending()

    def apply(self):
        if self.pending:
            arvf = RVF()
            arvf.command = "ADDRESS"
            arvf.uid = self.uid
            arvf.payload = self.address
            self.client_interface.request(arvf)
            self.response_cv.wait()
            wrvf = RVF()
            if self.capture and not self.update:
                wrvf.command = "READ"
            elif self.capture and self.update:
                wrvf.command = "WRITE_READ"
            elif self.update and not self.capture:
                wrvf.command = "WRITE"
            else:
                raise SchedulerError("Invalid command state!")
            wrvf.uid = self.uid
            self.local_access_mutex.acquire()
            wrvf.payload = self.rvf.payload
            self.local_access_mutex.release()
            self.client_interface.request(wrvf)
            self.local_access_mutex.acquire()
            self.request_count += 1
            self.pending = False
            self.local_access_mutex.release()
            self.logger.debug("PortalRegister.apply(uid={:d}, command={:s}, payload={:s})\n".format(wrvf.uid, wrvf.command,
                                                                                          str(wrvf.payload)))

    def hcb_write(self, rvf: RVF):
        self.logger.debug("PortalRegister.hcb_write(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                    str(rvf.payload)))
        self.local_access_mutex.acquire()
        self.rvf = rvf
        self.current_uid = rvf.uid
        self.local_access_mutex.release()
        self.pending = True
        self.capture = False
        self.update = True
        self.pending_count += 1
        from p2654model.scheduler.Scheduler import SchedulerFactory
        SchedulerFactory.get_scheduler().mark_pending()

    def hcb_read(self, rvf: RVF):
        self.logger.debug("PortalRegister.hcb_read(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                       str(rvf.payload)))
        self.local_access_mutex.acquire()
        self.rvf = rvf
        self.current_uid = rvf.uid
        self.local_access_mutex.release()
        self.pending = True
        self.pending_count += 1
        self.capture = True
        self.update = False
        from p2654model.scheduler.Scheduler import SchedulerFactory
        SchedulerFactory.get_scheduler().mark_pending()

    def hcb_write_read(self, rvf: RVF):
        self.logger.debug("PortalRegister.hcb_write_read(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                    str(rvf.payload)))
        self.local_access_mutex.acquire()
        self.rvf = rvf
        self.current_uid = rvf.uid
        self.local_access_mutex.release()
        self.pending = True
        self.capture = True
        self.update = True
        self.pending_count += 1
        from p2654model.scheduler.Scheduler import SchedulerFactory
        SchedulerFactory.get_scheduler().mark_pending()
