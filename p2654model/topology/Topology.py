#!/usr/bin/env python
"""
    Class managing the model tree structure representing the unit under test.
    Copyright (C) 2020  Bradford G. Van Treuren

    Class managing the model tree structure representing the unit under test.

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
__date__ = "2020/09/19"
__deprecated__ = False
__email__ = "bradvt59@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "Bradford G. Van Treuren"
__status__ = "Alpha/Experimental"
__version__ = "0.0.1"


from threading import Lock

import logging
from autologging import traced, logged

from p2654model.assembly.ScanRegister import ScanRegister
from p2654model.description.JTAGControllerDescription import JTAGControllerDescription
from p2654model.description.ScanMuxDescription import ScanMuxDescription
from p2654model.description.ScanRegisterDescription import ScanRegisterDescription
from p2654model.description.TAPDescription import TAPDescription
from p2654model.error.SchedulerError import SchedulerError


# create logger
module_logger = logging.getLogger('P2654Model.topology.Topology')


@logged
@traced
class Topology(object):
    max_aging = 0  # Doesn't matter right now

    def __init__(self):
        self.logger = logging.getLogger('P2654Model.topology.Topology.Topology')
        self.logger.info('Creating an instance of Topology')
        self.__totleaves = 0  # Overall number of leaf segments in the data structure
        self.__tot_pending_leaves = 0  # TODO
        self.__totpending_mutex = Lock()  # Mutex for processing pending Leaf nodes
        self.__top = None  # root node
        self.__uid_counter = 0  # running assignment for uid's added to the model

    @property
    def top(self):
        return self.__top

    @top.setter
    def top(self, t):
        self.__top = t

    def getLeafCount(self):
        return self.__totleaves

    def defineScanRegister(self, name, direction, entity_name, reg_length, safe_value):
        from p2654model.assembly.ScanRegister import ScanRegister
        if name is None:
            raise SchedulerError("Topology.defineScanRegister(): name was None.")
        reg = ScanRegister(name, direction, ScanRegisterDescription(entity_name, reg_length, safe_value))
        reg.uid = self.__uid_counter
        self.__uid_counter += 1
        self.__totleaves += 1
        return reg

    def defineScanMux(self, name, entity_name, keyreg, rmap):
        from p2654model.assembly.ScanMux import ScanMux
        if name is None:
            raise SchedulerError("Topology.defineScanRegister(): name was None.")
        description = ScanMuxDescription(entity_name, keyreg.reg_length)
        for m in rmap:
            description.add_dr_register(m[1], m[0], m[2])
        mux = ScanMux(name, description)
        mux.set_keyreg(keyreg)
        for m in mux.description.get_drs():
            mux.append_assembly(m)
        mux.uid = self.__uid_counter
        self.__uid_counter += 1
        self.__totleaves += 1
        return mux

    def defineTAP(self, name, entity_name, tir, mux):
        from p2654model.assembly.TAP import TAP
        if name is None:
            raise SchedulerError("Topology.defineTAP(): name was None.")
        description = TAPDescription(entity_name, tir.reg_length)
        tap = TAP(name, description)
        tap.append_assembly(tir)
        tap.append_assembly(mux)
        tap.uid = self.__uid_counter
        self.__uid_counter += 1
        return tap

    def defineJTAGControllerAssembly(self, name, entity_name, jtag_controller, tap):
        from p2654model.assembly.JTAGControllerAssembly import JTAGControllerAssembly
        if name is None:
            raise SchedulerError("Topology.defineJTAGControllerAssembly(): name was None.")
        description = JTAGControllerDescription(entity_name)
        jc = JTAGControllerAssembly(name, description, jtag_controller)
        jc.append_assembly(tap)
        jc.uid = self.__uid_counter
        self.__uid_counter += 1
        return jc

    def getAssembly_r(self, uid, node):
        depth_seg = node
        while depth_seg is not None:
            s = depth_seg
            while s is not None:
                if s.uid == uid:
                    return s
                a = self.getAssembly_r(uid, s.depth())
                if a is not None:
                    return a
                s = s.breadth()
            # depth_seg = depth_seg.depth()
        return None

    def getAssembly(self, uid):
        return self.getAssembly_r(uid, self.top)

    def getAssemblyPath(self, uid):
        period = 0
        tokenized_path = []
        abs_path = ""
        if self._findpath_lifo(self.top, uid, tokenized_path) == 0:
            raise SchedulerError("Topology.getAssemblyPath(): uid does not exist (%d)" % uid)
        try:
            while True:
                token = self._lifo_pop(tokenized_path)
                if period == 0:
                    period = 1
                else:
                    abs_path = abs_path + "."
                abs_path = abs_path + token
        except Exception:
            pass
        return abs_path

    def getAssemblyUID_r(self, abs_path, index, node):
        depth_seg = node
        while depth_seg is not None:
            old_index = index
            terminal, token, index = self._tokenize(abs_path, index)
            found = 0
            s = depth_seg
            while s is not None:
                if not s.is_visible():
                    inv_depth_seg = s.depth()
                    inv_uid = self.getAssemblyUID_r(abs_path, old_index, inv_depth_seg)
                    if inv_uid is not None:
                        return inv_uid
                elif token == s.name:
                    found = 1
                    break
                s = s.breadth()

            if found == 0:
                raise SchedulerError("Topology.getAssemblyUID_r(): Path does not exist (%s)." % abs_path)
            elif terminal == 0:
                depth_seg = depth_seg.depth()
            else:
                return s.uid
        return None

    def getAssemblyUID(self, abs_path):
        index = 0
        depth_seg = self.top
        return self.getAssemblyUID_r(abs_path, index, depth_seg)

    def _tokenize(self, abs_path, index):
        tokens = abs_path[index:].split('.')
        if len(tokens) == 1:
            return 1, tokens[0], index + len(tokens) + 1
        else:
            return 0, tokens[0], index + len(tokens) + 1

    def _lifo_push(self, lifo, name):
        '''
        Internal routine to push data into the LIFO
        '''
        lifo.append(name)

    def _lifo_pop(self, lifo):
        '''
        Internal routine to pop data from the LIFO
        '''
        return lifo.pop()

    def _findpath_lifo(self, node, uid, path):
        '''
        Recursive procedure used to reconstruct the path towards a given
        segment (identified by uid)
        '''
        if node is not None:
            # cycle the segments at the same level
            s = node
            while s is not None:
                if s.uid == uid:
                    if s.is_visible:
                        self._lifo_push(path, s.name)
                    return 1
                # recurse sublevels
                nextlev = s.depth()
                if self._findpath_lifo(nextlev, uid, path) == 1:
                    if s.is_visible:
                        self._lifo_push(path, s.name)
                    return 1
                s = s.breadth()
        return 0

    def show(self):
        self._postorder_print(self.top)

    def _postorder_print(self, node):
        '''
        Print the tree content with postorder strategy.
        NOTE: bypasses the "depth_next" method to traverse the whole data structure.
        '''
        from p2654model.assembly.JTAGControllerAssembly import JTAGControllerAssembly
        from p2654model.assembly.JTAGNetwork import JTAGNetwork
        from p2654model.assembly.LeafAssembly import LeafAssembly
        from p2654model.assembly.LinkerAssembly import LinkerAssembly
        from p2654model.assembly.ScanMux import ScanMux
        from p2654model.assembly.SuperAssembly import SuperAssembly
        from p2654model.assembly.TAP import TAP
        s = node
        while s is not None:
            nextlev = s.depth()
            self._postorder_print(nextlev)
            # print("(%2d)\t%s\t" % (s.uid, s.name))
            if isinstance(s, ScanRegister):
                print("[ScanRegister(%s)]\tlen: %3d\tpending: %s\n" % (s.name, s.reg_length, str(s.pending)))
            elif isinstance(s, TAP):
                print("[TAP(%s)]\tpending: %s\n" % (s.name, str(s.pending)))
            elif isinstance(s, ScanMux):
                print("[ScanMux(%s)]\tpending: %s\n" % (s.name, str(s.pending)))
            elif isinstance(s, JTAGNetwork):
                print("[JTAGNetwork(%s)]\tpending: %s\n" % (s.name, str(s.pending)))
            elif isinstance(s, JTAGControllerAssembly):
                print("[JTAGControllerAssembly(%s)]\tpending: %s\n" % (s.name, str(s.pending)))
            elif isinstance(s, LeafAssembly):
                print("[leaf(%s)]\t(%2d)\tpendings:%3d\n" % (node.name, node.uid, node.pendings))
            elif isinstance(s, LinkerAssembly):
                print("[link(%s)]\tstate: %d\n" % (node.name, node.path_state))
            elif isinstance(s, SuperAssembly):
                print("[super(%s)]\tstate: %d\n" % (node.name, node.path_state))
            s = s.breadth()

    def dump(self):
        '''
        NOTE: does not need a lock on cycle_mutex, as it is supposed
        to be called inside the scheduler procedure (with the mutex locked)
        '''
        self._postorder_print(self.top)
