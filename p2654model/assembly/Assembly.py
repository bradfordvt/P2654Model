#!/usr/bin/env python
"""
    Base class for all types of model nodes.
    Copyright (C) 2020  Bradford G. Van Treuren

    Base class of all Assembly type nodes containing shared code for these model nodes.

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
__date__ = "2020/09/20"
__deprecated__ = False
__email__ = "bradvt59@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "Bradford G. Van Treuren"
__status__ = "Alpha/Experimental"
__version__ = "0.0.1"


from enum import Enum
from threading import Lock, Condition

import logging
from autologging import logged, traced

from p2654model.assembly.PathState import PathState
from p2654model.error.SchedulerError import SchedulerError
from p2654model.interface.RVF import RVF


# create logger
module_logger = logging.getLogger('P2654Model.assembly.Assembly')


@logged
@traced
class Assembly:
    class Actions(Enum):
        NO_ACTION = 0
        ACTIVATE_PATH = 1
        DEACTIVATE_PATH = 2

    def __init__(self, name, description, depth_next):
        self.logger = logging.getLogger('P2654Model.assembly.Assembly.Assembly')
        self.logger.info('Creating an instance of Assembly')
        self.__name = name
        self.__description = description
        self.client_interface = None
        self.host_interface = None
        self.host_callbacks = {"LISTCB": self.__list_callbacks}
        self.resp_callbacks = {}
        self.__path_state = PathState.INACTIVE
        self.__uid = None  # universal identifier as int
        self.__pending = False
        self._breadth_next = None  # Reference to next 'brother' segment
        self._depth_ref = None
        self.depth_next = depth_next  # reference to the procedure that handles the tree descent
        self.visible = True  # if assembly is included in path name or just a placeholder
        self.request_count = 0  # tally of number of pending requests without a received response
        # mutex to regulate the access to the response_received_cv variable
        self.response_mutex = Lock()
        # condition variable: notifies the host callback that the
        # thread related to a client response has finished the request
        self.response_cv = Condition(self.response_mutex)
        # variable coupled to response_cv to avoid spurious wakeups
        self.response_v = 0
        self.response = None

        self.local_access_mutex = Lock()

    def __list_callbacks(self, rvf: RVF):
        if self.host_interface is None:
            raise SchedulerError("host_interface must be defined.")
        cbs = self.host_callbacks.keys()
        msg = ""
        first = True
        for c in cbs:
            if first:
                msg = c
                first = False
            else:
                msg = msg + ", " + c
        rvf.payload = msg
        seg = self.depth()
        while seg is not None:
            if seg.uid == rvf.uid:
                seg.client_interface.response(rvf)
                break
            seg = seg.breadth()

    def set_client_interface(self, client):
        self.client_interface = client
        self.client_interface.set_resp_callback(self.uid, self.resp_handler)

    def set_host_interface(self, host):
        self.host_interface = host
        self.host_interface.set_req_callback(self.uid, self.hcb_handler)

    def hcb_handler(self, rvf: RVF):
        cb = self.host_callbacks[rvf.command]
        if cb is None:
            raise SchedulerError("Unidentified callback command has been called {:s}.".format(rvf.command))
        self.logger.debug("hcb_handler({:s})\t{:s}\n".format(rvf.command, str(cb)))
        cb(rvf)

    def resp_handler(self, rvf: RVF):
        if rvf.uid == self.uid:
            self.response_mutex.acquire()
            self.response = rvf.payload
            self.response_cv.notify()
            self.response_mutex.release()

    def hcb_update(self, cb):
        self.host_callbacks.update(cb)

    def depth(self):
        return self._depth_ref

    def breadth(self):
        return self._breadth_next

    def depth_next(self):
        from p2654model.assembly.LinkerAssembly import LinkerAssembly
        action = Assembly.Actions.NO_ACTION
        ret = None
        if isinstance(self, LinkerAssembly):
            if self.path_state == PathState.ACTIVE:
                ret = self._depth_ref
            elif self.path_state == PathState.INACTIVE:
                pass
            else:
                # unreachable
                pass
            action = self.explore_cross_subpath()
        return ret, action

    def set_depth_next(self, next_):
        from p2654model.assembly.LinkerAssembly import LinkerAssembly
        from p2654model.assembly.SuperAssembly import SuperAssembly
        if isinstance(self, LinkerAssembly):
            self._depth_ref = next_
        elif isinstance(self, SuperAssembly):
            self._depth_ref = next_
        return None

    def append_assembly(self, child):
        from p2654model.assembly.LeafAssembly import LeafAssembly
        if isinstance(self, LeafAssembly):
            raise SchedulerError("LeafAssembly is unable to append children.")
        if child is None:
            raise SchedulerError("child has not been defined.")
        if self.depth() is None:
            # the parent has no children
            self.set_depth_next(child)
        else:
            s = self.depth()
            last = None
            while s is not None:
                last = s
                if child.name == s.name:
                    raise SchedulerError("Duplicate child name {:s}.".format(child.name))
                s = last._breadth_next
            # last points to the last of the parent subsegments
            if last is not None:
                last._breadth_next = child
        return self

    def get_response(self):
        self.response_cv.wait()
        self.response_mutex.acquire()
        resp = self.response
        self.response_mutex.release()
        return resp

    def explore_cross_subpath(self):
        # default action
        action = Assembly.Actions.DEACTIVATE_PATH
        return action

    @property
    def uid(self):
        return self.__uid

    @uid.setter
    def uid(self, uid):
        if not isinstance(uid, int):
            raise SchedulerError("uid is not of type int.")
        self.__uid = uid

    @property
    def path_state(self):
        return self.__path_state

    @path_state.setter
    def path_state(self, state):
        if not isinstance(state, PathState):
            raise SchedulerError("state is not an Assembly.PathState.")
        self.__path_state = state

    @property
    def pending(self):
        return self.__pending

    @pending.setter
    def pending(self, p):
        if isinstance(p, bool) and p:
            self.__pending = True
        else:
            self.__pending = False

    def is_pending(self):
        return True if self.pending else False

    def is_visible(self):
        return True if self.visible else False

    @property
    def name(self):
        return self.__name

    @property
    def description(self):
        return self.__description
