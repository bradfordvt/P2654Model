#!/usr/bin/env python
"""
    Model of a ScanRegister.
    Copyright (C) 2020  Bradford G. Van Treuren

    Specialized class modeling the IEEE 1687 ScanRegister primitive.

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


from enum import Enum

import logging
from autologging import traced, logged
from myhdl import intbv

from p2654model.assembly.LeafAssembly import LeafAssembly
from p2654model.description.ScanRegisterDescription import ScanRegisterDescription
from p2654model.error.SchedulerError import SchedulerError
from p2654model.interface.RVF import RVF


# create logger
module_logger = logging.getLogger('P2654Model.assembly.ScanRegister')


@logged
@traced
class ScanRegister(LeafAssembly):
    class Direction(Enum):
        WRITE_ONLY = 0,
        READ_ONLY = 1,
        READ_WRITE = 2

    def __init__(self, name, direction: Direction, description: ScanRegisterDescription):
        self.logger = logging.getLogger('P2654Model.assembly.ScanRegister.ScanRegister')
        self.logger.info('Creating an instance of ScanRegister')
        self.direction = direction
        self.capture = False
        LeafAssembly.__init__(self, name, description)
        self.__value = self.description.safe_value  # current value of the register
        self.__read_value = self.description.safe_value

    def resp_handler(self, rvf: RVF):
        self.logger.debug("ScanRegister.resp_handler(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                    str(rvf.payload)))
        if rvf.command == "SCAN":
            self.__read_value = None
        elif rvf.command == "CAPSCAN":
            self.response_mutex.acquire()
            self.__read_value = rvf.payload
            self.response_mutex.release()
        else:
            raise SchedulerError("Invalid command received.")
        self.request_count -= 1
        if self.request_count == 0:
            pass  # Notify all requests have been satisfied
        from p2654model.scheduler.Scheduler import SchedulerFactory
        SchedulerFactory.get_scheduler().clear_pending()

    def apply(self):
        if self.pending:
            self.local_access_mutex.acquire()
            if self.capture:
                wrvf = RVF()
                wrvf.command = "CAPSCAN"
            else:
                wrvf = RVF()
                wrvf.command = "SCAN"
            wrvf.uid = self.uid
            wrvf.payload = self.__value
            self.client_interface.request(wrvf)
            self.request_count += 1
            self.pending = False
            self.local_access_mutex.release()
            self.logger.debug("ScanRegister.apply(uid={:d}, command={:s}, payload={:s})\n".format(wrvf.uid, wrvf.command,
                                                                                          str(wrvf.payload)))

    def write(self, value):
        if not isinstance(value, intbv):
            raise SchedulerError("val is not of type intbv.")
        if len(value) != self.reg_length:
            raise SchedulerError("Size of value does not match register size.")
        self.logger.debug("ScanRegister.write({:s})\n".format(str(value)))
        self.local_access_mutex.acquire()
        self.__value = value
        self.__read_value = None
        self.pending = True
        self.capture = False
        self.local_access_mutex.release()
        from p2654model.scheduler.Scheduler import SchedulerFactory
        SchedulerFactory.get_scheduler().mark_pending()

    def read(self):
        if self.__read_value is None:
            # apply() should have updated this value if was able to run.  Otherwise, raise error.
            raise SchedulerError("Attempt to read a ScanRegister before synchronized.")
        return self.__read_value

    def write_read(self, value):
        if not isinstance(value, intbv):
            raise SchedulerError("val is not of type intbv.")
        if len(value) != self.reg_length:
            raise SchedulerError("Size of value does not match register size.")
        self.local_access_mutex.acquire()
        self.__value = value
        self.__read_value = None
        self.pending = True
        self.capture = True
        self.local_access_mutex.release()
        self.logger.debug("ScanRegister.write_read({:s})\n".format(str(value)))
        from p2654model.scheduler.Scheduler import SchedulerFactory
        SchedulerFactory.get_scheduler().mark_pending()
        # self.__read_value = self.get_response()
        # return self.__read_value

    def get_value(self):
        return self.__value

    @property
    def safe_value(self):
        return self.description.safe_value

    @property
    def reg_length(self):
        return self.description.reg_length

    @property
    def entity_name(self):
        return self.description.entity_name
