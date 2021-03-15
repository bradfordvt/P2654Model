#!/usr/bin/env python
"""
    Stub class for an Parallel to Serial architecture node. -- Work in Progress
    Copyright (C) 2020  Bradford G. Van Treuren

    Model for an Parallel to Serial used to control access to interfaces managed by this interface.

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
__date__ = "2020/10/01"
__deprecated__ = False
__email__ = "bradvt59@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "Bradford G. Van Treuren"
__status__ = "Alpha/Experimental"
__version__ = "0.0.1"


from p2654model.assembly.SuperAssembly import SuperAssembly


class ParallelToSerial(SuperAssembly):
    def __init(self, name, description):
        SuperAssembly.__init__(self, name, description)
        cb = {"SCAN": self.hcb_scan, "CAPSCAN": self.hcb_capscan}
        self.hcb_update(cb)

    def resp_handler(self, rvf: RVF):
        self.logger.debug("ParallelToSerial.resp_handler(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                    str(rvf.payload)))

    def apply(self):
        self.logger.debug("ParallelToSerial.apply(uid={:d}, command={:s}, payload={:s})\n".format(wrvf.uid, wrvf.command,
                                                                                                str(wrvf.payload)))

    def hcb_scan(self, rvf: RVF):
        self.logger.debug("ParallelToSerial.hcb_scan(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                    str(rvf.payload)))

    def hcb_capscan(self, rvf: RVF):
        self.logger.debug("ParallelToSerial.hcb_capscan(uid={:d}, command={:s}, payload={:s})\n".format(rvf.uid, rvf.command,
                                                                                    str(rvf.payload)))

