#!/usr/bin/env python
"""
    Class to transmit messages between nodes.
    Copyright (C) 2020  Bradford G. Van Treuren

    Class used to transfer messages between model nodes.  This class represents the edges of a model tree.

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
__date__ = "2020/09/15"
__deprecated__ = False
__email__ = "bradvt59@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "Bradford G. Van Treuren"
__status__ = "Alpha/Experimental"
__version__ = "0.0.1"


from queue import Queue
from threading import Thread, Event

import logging
from autologging import traced, logged

from p2654model.interface.RVF import RVF


# create logger
module_logger = logging.getLogger('P2654Model.interface.AccessInterface')


@logged
@traced
class AccessInterface:
    stop_event = Event()

    @staticmethod
    def stop():
        AccessInterface.stop_event.set()

    def __init__(self, protocol):
        self.logger = logging.getLogger('P2654Model.interface.AccessInterface.AccessInterface')
        self.logger.info('Creating an instance of AccessInterface')
        self.reqQ = Queue(maxsize=0)
        self.respQ = Queue(maxsize=0)
        self.req_cb = None
        self.resp_cb = {}
        self.current_uid = None
        self.protocol = protocol
        req = Thread(target=self.__req_handler)
        req.setDaemon(True)
        req.start()
        resp = Thread(target=self.__resp_handler)
        resp.setDaemon(True)
        resp.start()

    def __req_handler(self):
        while not AccessInterface.stop_event.is_set():
            if self.req_cb is not None:
                rvf = self.reqQ.get(block=True, timeout=None)
                self.current_uid = rvf.uid
                self.logger.debug("AccessInterface: Dispatching Request(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid,
                                                                                                               rvf.command,
                                                                                                               str(rvf.payload)))
                self.logger.debug("dump of req_cb\n{:s}\n".format(str(self.req_cb)))
                self.req_cb(rvf)
                self.reqQ.task_done()

    def __resp_handler(self):
        while not AccessInterface.stop_event.is_set():
            if self.resp_cb is not None:
                # if self.current_uid is None:
                    # raise SchedulerError("Received an unrequested response for uid.")
                rvf = self.respQ.get(block=True, timeout=None)
                self.logger.debug("AccessInterface: Dispatching Response(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid,
                                                                                                               rvf.command,
                                                                                                               str(rvf.payload)))
                self.resp_cb[self.current_uid](rvf)
                self.respQ.task_done()

    def request(self, rvf: RVF):
        if rvf is None:
            self.logger.debug("(((((((((((((((((((((((((((((((((rvf is None))))))))))))))))))))))))))))))))\n")
        if rvf.uid is None:
            self.logger.debug("(((((((((((((((((((((((((((((((((rvf.uid is None))))))))))))))))))))))))))))))))\n")
        if rvf.command is None:
            self.logger.debug("(((((((((((((((((((((((((((((((((rvf.command is None))))))))))))))))))))))))))))))))\n")
        if rvf.payload is None:
            self.logger.debug("(((((((((((((((((((((((((((((((((rvf.payload is None))))))))))))))))))))))))))))))))\n")
        self.logger.debug("AccessInterface: Request(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                       str(rvf.payload)))
        self.reqQ.put(rvf)

    def set_req_callback(self, uid, cb):
        self.logger.debug("set_req_callback({:d}, {:s})\n".format(uid, str(cb)))
        self.req_cb = cb

    def response(self, rvf: RVF):
        self.logger.debug("AccessInterface: Response(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                            str(rvf.payload)))
        self.respQ.put(rvf)

    def set_resp_callback(self, uid, cb):
        self.resp_cb.update({uid: cb})
