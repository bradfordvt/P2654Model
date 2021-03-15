#!/usr/bin/env python
"""
    Modeling for a DataMux node.
    Copyright (C) 2020  Bradford G. Van Treuren

    Specialized Assembly class derived from a Linker Assembly type used to model parallel bus MUX logic.

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
module_logger = logging.getLogger('P2654Model.assembly.DataMux')


@logged
@traced
class DataMux(LinkerAssembly):
    def __init__(self, name, description):
        self.logger = logging.getLogger('P2654Model.assembly.DataMux.DataMux')
        self.logger.info('Creating an instance of DataMux')
        self.value = None
        self.keyreg = None
        self.capture = False
        self.update = False
        self.selected_seg = None
        self.pending_count = 0
        LinkerAssembly.__init__(self, name, description, DataMux.depth_next)
        self.visible = False
        cb = {"ISACTIVE": self.hcb_isactive, "WRITE": self.hcb_write, "READ": self.hcb_read,
              "WRITE_READ": self.hcb_write_read, "ADDRESS": self.hcb_address}
        self.hcb_update(cb)

    def set_keyreg(self, reg):
        self.keyreg = reg

    def get_keyreg(self):
        return self.keyreg

    def resp_handler(self, rvf: RVF):
        self.logger.debug("DataMux.resp_handler(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                        str(rvf.payload)))
        uid = rvf.uid
        resp = RVF()
        self.response_mutex.acquire()
        resp.payload = rvf.payload
        resp.command = rvf.command
        self.response_mutex.release()
        found = False
        seg = self.depth()
        while seg is not None:
            if seg == self.selected_seg:
                resp.uid = seg.uid
                seg.client_interface.response(resp)
                found = True
                break
            seg = seg.breadth()
        if not found:
            raise SchedulerError("Unable to locate selected_uid assembly.")
        self.request_count -= 1
        if self.request_count == 0:
            pass  # Notify all requests have been satisfied
        SchedulerFactory.get_scheduler().clear_pending()

    def apply(self):
        if self.keyreg is None:
            raise SchedulerError("keyreg must be defined before use.")
        # self.capture = False
        self.pending_count = 0
        seg = self.depth()
        while seg is not None:
            seg.apply()
            seg = seg.breadth()
        if self.pending_count > 1:
            raise SchedulerError("Multiple competing paths detected.")
        try:
            self.selected_seg = self.description.get_addr_dr(self.keyreg.get_value())
        except SchedulerError:
            self.logger.debug("*******************************************************\n")
            self.keyreg.write(self.description.get_default_code())
            self.selected_seg = self.description.get_addr_dr(self.description.get_default_code())
        if self.selected_seg is None:
            raise SchedulerError("No path has been selected.")
        if self.pending:
            self.logger.debug("selected_seg.name = {:s}.".format(self.selected_seg.name))
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
            wrvf.payload = self.value
            self.client_interface.request(wrvf)
            self.request_count += 1
            self.pending = False
            self.capture = False
            self.update = False
            self.logger.debug("DataMux.apply(uid={:d}, command={:s}, payload={:s})\n".format(wrvf.uid, wrvf.command,
                                                                                     str(wrvf.payload)))

    def _select(self, suid):
        if self.keyreg is None:
            raise SchedulerError("keyreg must be defined before use.")
        uid = suid
        try:
            selected_seg = self.description.get_addr_dr(self.keyreg.get_value())
        except SchedulerError:
            self.logger.debug("=====================================================\n")
            self.keyreg.write(self.description.get_default_code())
            return 1
        if selected_seg is not None:
            if selected_seg.uid != uid:
                found = False
                # Find the first match in the table as the default value
                k = self.description.get_first_match(uid)
                if k is not None:
                    self.logger.debug("++++++++++++++++++++++++++++++++++++++++++\n")
                    self.keyreg.write(k)
                    return 1
                else:
                    raise SchedulerError("Unable to locate selector for uid {:d}.".format(uid))
            else:
                return 0  # Already selected_uid
        else:
            raise SchedulerError("Unable to locate a code for value in keyreg {:s}.".format(str(self.keyreg.read())))

    def _deselect(self, suid):
        if self.keyreg is None:
            raise SchedulerError("keyreg must be defined before use.")
        uid = suid
        self.logger.debug("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$\n")
        self.keyreg.write(self.description.get_default_code())  # Use first element as default disable pattern

    def hcb_isactive(self, rvf: RVF):
        if self.keyreg is None:
            raise SchedulerError("keyreg must be defined before use.")
        uid = rvf.uid
        code = self.keyreg.read()
        seldr = self.description.get_addr_dr(code)
        scheduler = SchedulerFactory.get_scheduler()
        assembly = scheduler.topology.getAssembly(uid)
        if seldr is not None:
            if assembly.entity_name == seldr.entity_name:
                self.__send_response(uid, "ISACTIVE", "FALSE")
            else:
                self.__send_response(uid, "ISACTIVE", "TRUE")
        else:
            self.__send_response(uid, "ISACTIVE", "FALSE")

    def __send_response(self, uid, command, payload):
        resp = RVF()
        resp.payload = payload
        resp.command = command
        resp.uid = uid
        found = False
        seg = self.depth()
        while seg is not None:
            if uid == seg.uid:
                seg.client_interface.reponse(resp)
                found = True
                break
            seg = seg.breadth()
        if not found:
            raise SchedulerError("Unable to locate uid assembly.")

    def hcb_write(self, rvf: RVF):
        self.logger.debug("DataMux.hcb_write(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                    str(rvf.payload)))
        uid = rvf.uid
        if uid != self.selected_seg.uid:
            if self.selected_seg.uid is not None:
                self._deselect(self.selected_seg.uid)
            self._select(uid)
        self.local_access_mutex.acquire()
        self.value = rvf.payload
        self.pending = True
        self.capture = False
        self.update = True
        self.pending_count += 1
        self.local_access_mutex.release()
        SchedulerFactory.get_scheduler().mark_pending()

    def hcb_read(self, rvf: RVF):
        self.logger.debug("DataMux.hcb_read(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                       str(rvf.payload)))
        uid = rvf.uid
        if uid != self.selected_seg.uid:
            if self.selected_uid is not None:
                self._deselect(self.selected_seg.uid)
            self._select(uid)
        self.local_access_mutex.acquire()
        self.value = rvf.payload
        self.pending = True
        self.pending_count += 1
        self.capture = True
        self.update = False
        self.local_access_mutex.release()
        SchedulerFactory.get_scheduler().mark_pending()

    def hcb_write_read(self, rvf: RVF):
        self.logger.debug("DataMux.hcb_write_read(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                    str(rvf.payload)))
        uid = rvf.uid
        if uid != self.selected_seg.uid:
            if self.selected_seg.uid is not None:
                self._deselect(self.selected_seg.uid)
            self._select(uid)
        self.local_access_mutex.acquire()
        self.value = rvf.payload
        self.pending = True
        self.capture = True
        self.update = True
        self.pending_count += 1
        self.local_access_mutex.release()
        SchedulerFactory.get_scheduler().mark_pending()

    def hcb_address(self, rvf: RVF):
        self.logger.debug("DataMux.hcb_address(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                    str(rvf.payload)))
        code = rvf.payload
        if len(code) != self.kreg.reg_len:
            raise SchedulerError("Address is invalid length!")
        self.keyreg.write(code)
        self.host_interface.response(rvf)
