#!/usr/bin/env python
"""
    Main scheduling class and tread for an application.
    Copyright (C) 2020  Bradford G. Van Treuren

    Main scheduling class and tread for an application.

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


import threading
from threading import Lock, Condition, Event, Thread
from time import sleep

import logging
from autologging import traced, logged
from myhdl import intbv

from p2654model.error.SchedulerError import SchedulerError
from p2654model.interface.AccessInterface import AccessInterface
from p2654model.topology.Topology import Topology


# create logger
module_logger = logging.getLogger('P2654Model.scheduler.Scheduler')


@logged
@traced
class SchedulerFactory:
    inst = None

    @staticmethod
    def get_scheduler(max_aging=0, watchdog_us=0):
        if SchedulerFactory.inst is None:
            SchedulerFactory.inst = Scheduler(max_aging=max_aging, watchdog_us=watchdog_us)
        return SchedulerFactory.inst


@traced
class Scheduler:
    def __init__(self, max_aging=0, watchdog_us=0):
        '''
        the max aging value for the leaf segments. Passed that, the
        segment is closed by a possible crossroads set to "automatic"
        '''
        self.logger = logging.getLogger('P2654Model.scheduler.Scheduler.Scheduler')
        self.logger.info('Creating an instance of Scheduler')
        self.max_aging = max_aging
        '''
        the period of the watchdog timer, expressed in microseconds.
        if 0, the "full pending" option is not active, and the watchdog
        is therefore unset.
        '''
        self.watchdog_us = watchdog_us
        # Flag to use watchdog timer for operations or not
        self.fullpending_option = False
        if watchdog_us != 0:
            self.fullpending_option = True
        # mutex to regulate the access to the segscan_completed_cv condition variable
        self.release_mutex = Lock()
        # condition variable: notifies the scheduler that the
        # thread related to a segment has finished the scan access
        self.release_cv = Condition(self.release_mutex)
        # variable coupled to release_cv to avoid spurious wakeups
        self.release_v = 0
        # This needs to be fleshed out and explained by Michele and JoseFA
        # self.cycle_threshold = float('inf')
        self.cycle_threshold = -1
        # Used to get out of the watchdog timer wait loop
        self.in_cycle = 0
        # Event used to inform the Scheduler to terminate execution
        self.stop_event = Event()
        '''
        Mutexes and cycle start/end condition variables used to trigger the scheduler as
        well as to avoid concurrent r/w accesses among modules
        '''
        self.cycle_mutex = Lock()
        self.start_cycle_cv = Condition(self.cycle_mutex)
        self.end_cycle_cv = Condition(self.cycle_mutex)

        self.apply_mutex = Lock()
        self.start_apply_cv = Condition(self.apply_mutex)
        self.end_apply_cv = Condition(self.apply_mutex)
        self.apply_v = 0

        self.apply_start = threading.Event()
        self.apply_end = threading.Event()

        self.t = None


        # Number of outstanding leaves that are pending
        self.tot_pending_leaves = 0
        # The topology tree data structure used by this Scheduler
        self.__topology = Topology()
        # Assembly.set_max_aging(max_aging)

    def mark_pending(self):
        self.logger.debug("mark_pending\n")
        self.tot_pending_leaves += 1

    def clear_pending(self):
        self.logger.debug("clear_pending\n")
        if self.tot_pending_leaves == 0:
            return
        self.tot_pending_leaves -= 1

    @property
    def topology(self):
        return self.__topology

    def start(self):
        self.t = Thread(target=self._scan_cycle_handler, args=())
        self.t.start()
        return 0

    def stop(self):
        self.cycle_mutex.acquire()
        self.stop_event.set()
        self.cycle_mutex.release()
        self.apply_start.set()
        AccessInterface.stop()
        self.t.join()
        return 0

    def _scan_cycle_handler(self):
        '''
        Scheduler thread procedure
        '''
        # try:
        #     self.logger.debug(
        #         "[{:d}] _wait_for_cycle() calling self.apply_mutex.acquire()\n".format(threading.get_ident()))
        #     self.apply_mutex.acquire()
        # except RuntimeError as e:
        #     raise SchedulerError(
        #         "Scheduler._wait_for_cycle(): error while locking apply_mutex\n{:s}".format(str(e)))

        while not self.stop_event.is_set():
            '''
            WAIT for the cycle RELEASING the cycle_mutex lock.
            If the watchdog has been set, the wait is timed.
            NOTE: this wait is the only point in which the scheduler
            releases the cycle_mutex lock.
            '''
            self.apply_v = 0
            self._wait_for_cycle()
            # sleep(1)

            # perform a (or a series of) new scan chain cycle(s).
            # self.logger.debug("[{:d}] _scan_cycle_handler() self.tot_pending_leaves = {:d}\n".format(threading.get_ident(), self.tot_pending_leaves))
            while self.tot_pending_leaves > 0:
                self._new_cycle()

            # Broadcast all the waiting threads
            # self.logger.debug("[{:d}] _scan_cycle_handler() calling self.end_apply_cv.notifyAll()\n".format(threading.get_ident()))
            # self.end_apply_cv.notifyAll()
            self.apply_end.set()

        # try:
        #     self.logger.debug(
        #         "[{:d}] _wait_for_cycle() calling self.apply_mutex.release()\n".format(threading.get_ident()))
        #     self.apply_mutex.release()
        # except RuntimeError as e:
        #     raise SchedulerError(
        #         "Scheduler._wait_for_cycle(): error while locking apply_mutex\n{:s}".format(str(e)))

    def _wait_for_cycle(self):
        if self.fullpending_option:
            self.logger.debug(
                "[{:d}] _wait_for_cycle(): self.start_apply_cv.wait(self.watchdog_us / 1000000.0)\n".format(
                    threading.get_ident()))
            # self.start_apply_cv.wait(self.watchdog_us / 1000000.0)
            self.apply_start.wait(self.watchdog_us / 1000000.0)
            self.apply_start.clear()
        else:
            self.logger.debug(
                "[{:d}] _wait_for_cycle(): self.start_apply_cv.wait(self.watchdog_us / 1000000.0)\n".format(
                    threading.get_ident()))
            # self.start_apply_cv.wait()
            self.apply_start.wait()
            self.apply_start.clear()
        # # current_time = 0
        # # watchdog_fire_time = 0
        # self.logger.debug("[{:d}] Entering _wait_for_cycle()\n".format(threading.get_ident()))
        # if self.fullpending_option:
        #     # set the watchdog time
        #     # current_time = time.clock()
        #     # watchdoc_fire_time = current_time
        #     # watchdog_fire_time = (Scheduler.watchdog_us / 1000000.0) + current_time
        #     # Perform a timed wait
        #     while self.in_cycle == 0:
        #         try:
        #             self.logger.debug("[{:d}] _wait_for_cycle(): self.start_cycle_cv.wait(self.watchdog_us / 1000000.0)\n".format(threading.get_ident()))
        #             self.start_cycle_cv.wait(self.watchdog_us / 1000000.0)
        #             self.in_cycle = 1
        #         except Exception:
        #             raise SchedulerError("Scheduler._wait_for_cycle(): error while time waiting on cycle_mutex")
        # else:
        #     # perform a standard wait
        #     while self.in_cycle == 0:
        #         try:
        #             self.logger.debug("[{:d}] _wait_for_cycle(): self.start_cycle_cv.wait()\n".format(threading.get_ident()))
        #             self.start_cycle_cv.wait()
        #         except Exception:
        #             raise SchedulerError("Scheduler._wait_for_cycle(): error while on cycle_mutex")

    def _new_cycle(self):
        # self.logger.debug("[{:d}] Entering _new_cycle()\n".format(threading.get_ident()))
        self.topology.top.apply()

    def lock_request(self, uid):
        from p2654model.assembly.LeafAssembly import LeafAssembly
        seg = self._lookup(uid, LeafAssembly)
        if seg is not None:
            leaf = seg
            try:
                self.logger.debug("[{:d}] lock_request() calling self.cycle_mutex.acquire()\n".format(threading.get_ident()))
                self.cycle_mutex.acquire()
            except RuntimeError as e:
                raise SchedulerError(
                    "Scheduler.lock_request(): error while locking cycle_mutex on leaf {:d}.\n{:s}".format(uid, str(e)))
            if self.tot_pending_leaves >= 0:
                in_cycle = 1
                try:
                    self.logger.debug("[{:d}] lock_request() calling self.start_cycle_cv.notify()\n".format(threading.get_ident()))
                    self.start_cycle_cv.notify()
                except RuntimeError:
                    raise SchedulerError(
                        "Scheduler.lock_request(): error while signalling start_cycle_cv on leaf {:d}.".format(
                            uid))
            try:
                self.logger.debug("[{:d}] lock_request() calling self.cycle_mutex.release()\n".format(threading.get_ident()))
                self.cycle_mutex.release()
            except RuntimeError:
                raise SchedulerError("error while unlocking cycle_mutex on leaf {:d}.".format(uid))

    def lock_release(self, uid):
        from p2654model.experiment7.Assembly import LeafAssembly
        # seg = self._lookup(uid, LeafAssembly)
        # if seg is not None:
        #     leaf = seg
        #     try:
        #         print("[{:d}] lock_release() calling self.cycle_mutex.release()\n".format(threading.get_ident()))
        #         self.cycle_mutex.release()
        #     except RuntimeError as e:
        #         raise SchedulerError(
        #             "Scheduler.lock_release(): error while releasing cycle_mutex on leaf {:d}.\n{:s}".format(uid, str(e)))
        try:
            self.logger.debug("[{:d}] lock_release() calling self.release_mutex.acquire()\n".format(threading.get_ident()))
            self.release_mutex.acquire()
            self.release_v = 1
            try:
                self.logger.debug("[{:d}] lock_release() calling self.release_cv.notify()\n".format(threading.get_ident()))
                self.release_cv.notify()
                try:
                    self.logger.debug("[{:d}] lock_release() calling self.release_mutex.release()\n".format(threading.get_ident()))
                    self.release_mutex.release()
                    return 0
                except RuntimeError as e:
                    raise SchedulerError("error while unlocking release_mutex on leaf {:d}.\n{:s}".format(uid, e))
            except RuntimeError as e:
                raise SchedulerError("error while signalling release_cv on leaf {:s}.\n{:s}".format(uid, e))
        except RuntimeError as e:
            raise SchedulerError("error while locking release_mutex on leaf {:d}.\n{:s}".format(uid, e))

    def _lookup_r(self, node, uid, type_):
        if node is not None:
            s = node
            while s is not None:
                # recurse sublevels
                result = self._lookup_r(s.depth(), uid, type_)
                if result is not None:
                    return result
                if s.uid == uid:
                    if isinstance(s, type_):
                        return s
                s = s.breadth()
        return None

    def _lookup(self, uid, type_):
        result = self._lookup_r(self.topology.top, uid, type_)
        if result is None:
            raise SchedulerError("uid[{:d}] does not exist.".format(uid))
        return result

    def write(self, path, value:intbv):
        try:
            uid = self.topology.getAssemblyUID(path)
            # try:
            #     self.lock_request(uid)
            try:
                inst = self.topology.getAssembly(uid)
                try:
                    inst.write(value)
                    # try:
                    #     self.lock_release(uid)
                    # except SchedulerError as e:
                    #     raise SchedulerError(
                    #         "Scheduler.write: Error detected while releasing mutex lock.\n{:s}".format(str(e)))
                except SchedulerError as e:
                    raise SchedulerError(
                        "Scheduler.write: Error detected while writing to instance.\n{:s}".format(str(e)))
            except SchedulerError as e:
                raise SchedulerError(
                    "Scheduler.write: Error detected while obtaining instance.\n{:s}".format(str(e)))
            # except SchedulerError as e:
            #     raise SchedulerError("Scheduler.write: Error detected while obtaining mutex lock.\n{:s}".format(str(e)))
        except SchedulerError as e:
            raise SchedulerError("Scheduler.write: Error detected while obtaining UID.\n{:s}".format(str(e)))

    def write_read(self, path, value: intbv):
        try:
            uid = self.topology.getAssemblyUID(path)
            # try:
            #     self.lock_request(uid)
            try:
                inst = self.topology.getAssembly(uid)
                try:
                    inst.write_read(value)
                    # try:
                    #     self.lock_release(uid)
                    # except SchedulerError as e:
                    #     raise SchedulerError(
                    #         "Scheduler.write_read: Error detected while releasing mutex lock.\n{:s}".format(str(e)))
                except SchedulerError as e:
                    raise SchedulerError(
                        "Scheduler.write_read: Error detected while writing to instance.\n{:s}".format(str(e)))
            except SchedulerError as e:
                raise SchedulerError(
                    "Scheduler.write_read: Error detected while obtaining instance.\n{:s}".format(str(e)))
            # except SchedulerError as e:
            #     raise SchedulerError("Scheduler.write_read: Error detected while obtaining mutex lock.\n{:s}".format(str(e)))
        except SchedulerError as e:
            raise SchedulerError("Scheduler.write_read: Error detected while obtaining UID.\n{:s}".format(str(e)))

    def apply(self):
        # try:
        #     self.logger.debug(
        #         "[{:d}] apply() calling self.apply_mutex.acquire()\n".format(threading.get_ident()))
        #     self.apply_mutex.acquire()
        # except RuntimeError as e:
        #     raise SchedulerError(
        #         "Scheduler.apply(): error while locking apply_mutex\n{:s}".format(str(e)))
        # self.start_apply_cv.notifyAll()
        self.apply_start.set()
        if self.fullpending_option:
            # self.end_apply_cv.wait(self.watchdog_us / 1000000.0)
            self.apply_end.wait(self.watchdog_us / 1000000.0)
            self.apply_end.clear()
        else:
            # self.end_apply_cv.wait()
            self.apply_end.wait()
            self.apply_end.clear()
        self.apply_v = 1
        # try:
        #     self.logger.debug(
        #         "[{:d}] apply() calling self.apply_mutex.release()\n".format(threading.get_ident()))
        #     self.apply_mutex.release()
        # except RuntimeError as e:
        #     raise SchedulerError(
        #         "Scheduler.apply(): error while unlocking apply_mutex\n{:s}".format(str(e)))

    #     	if (pthread_mutex_lock(&release_mutex) != 0)
	# 	printf_err("ERR(sched-core) unable to lock release_mutex\n");
    #
	# // release the mutual exclusion for the ACK (the segment thread can wake up)
	# if (pthread_mutex_unlock(&leaf->ack_mutex) != 0)
	# 	printf_err("ERR(sched-core) unable to unlock ack_mutex\n");
    #
	# //	wait for the segment thread to release the critical section
	# while(release == 0)
	# 	pthread_cond_wait(&release_cv, &release_mutex);
	# release = 0;
    #
	# if (pthread_mutex_unlock(&release_mutex) != 0)
	# 	printf_err("ERR(sched-core) unable to unlock release_mutex\n");


        # # try:
        #     # self.lock_request(self.topology.top.uid)
        # try:
        #     while self.tot_pending_leaves > 0:
        #         self.topology.top.apply()
        #         sleep(1)
        #     # try:
        #         # self.lock_release(self.topology.top.uid)
        #     # except SchedulerError as e:
        #         # raise SchedulerError(
        #             # "Scheduler.apply: Error detected while releasing mutex lock.\n{:s}".format(str(e)))
        # except SchedulerError as e:
        #     raise SchedulerError(
        #         "Scheduler.apply: Error while processing instance.\n{:s}".format(str(e)))
        # # except SchedulerError as e:
        #     # raise SchedulerError("Scheduler.apply: Error detected while obtaining mutex lock.\n{:s}".format(str(e)))

    def read(self, path):
        try:
            uid = self.topology.getAssemblyUID(path)
            # try:
            #     self.lock_request(uid)
            try:
                inst = self.topology.getAssembly(uid)
                try:
                    value = inst.read()
                    return value
                    # try:
                    #     self.lock_release(uid)
                    #     return value
                    # except SchedulerError as e:
                    #     raise SchedulerError(
                    #         "Scheduler.read: Error detected while releasing mutex lock.\n{:s}".format(str(e)))
                except SchedulerError as e:
                    raise SchedulerError(
                        "Scheduler.read: Error detected while reading from instance.\n{:s}".format(str(e)))
            except SchedulerError as e:
                raise SchedulerError(
                    "Scheduler.read: Error detected while obtaining instance.\n{:s}".format(str(e)))
            # except SchedulerError as e:
            #     raise SchedulerError("Scheduler.read: Error detected while obtaining mutex lock.\n{:s}".format(str(e)))
        except SchedulerError as e:
            raise SchedulerError("Scheduler.read: Error detected while obtaining UID.\n{:s}".format(str(e)))
