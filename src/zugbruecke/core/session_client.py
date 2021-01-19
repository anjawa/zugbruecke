# -*- coding: utf-8 -*-

"""

ZUGBRUECKE
Calling routines in Windows DLLs from Python scripts running on unixlike systems
https://github.com/pleiszenburg/zugbruecke

    src/zugbruecke/core/session.py: Classes for managing zugbruecke sessions

    Required to run on platform / side: [UNIX]

    Copyright (C) 2017-2021 Sebastian M. Ernst <ernst@pleiszenburg.de>

<LICENSE_BLOCK>
The contents of this file are subject to the GNU Lesser General Public License
Version 2.1 ("LGPL" or "License"). You may not use this file except in
compliance with the License. You may obtain a copy of the License at
https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt
https://github.com/pleiszenburg/zugbruecke/blob/master/LICENSE

Software distributed under the License is distributed on an "AS IS" basis,
WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License for the
specific language governing rights and limitations under the License.
</LICENSE_BLOCK>

"""


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# IMPORT
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import atexit
from ctypes import _FUNCFLAG_CDECL, _FUNCFLAG_USE_ERRNO, _FUNCFLAG_USE_LASTERROR
import os
import signal
import time

from .const import _FUNCFLAG_STDCALL
from .config import config_class
from .data import data_class
from .dll_client import dll_client_class
from .interpreter import Interpreter
from .lib import get_free_port
from .log import log_class
from .rpc import mp_client_safe_connect, mp_server_class
from .wenv import Env


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# SESSION CLIENT CLASS
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


class session_client_class:
    def __init__(self, parameter=None, force=False):

        if parameter is None:
            parameter = {}

        self.__init_stage_1__(parameter, force)

    def ctypes_FormatError(self, code=None):

        # If in stage 1, fire up stage 2
        if self.stage == 1:
            self.__init_stage_2__()

        # Ask the server
        return self.rpc_client.ctypes_FormatError(code)

    def ctypes_get_last_error(self):

        # If in stage 1, fire up stage 2
        if self.stage == 1:
            self.__init_stage_2__()

        # Ask the server
        return self.rpc_client.ctypes_get_last_error()

    def ctypes_GetLastError(self):

        # If in stage 1, fire up stage 2
        if self.stage == 1:
            self.__init_stage_2__()

        # Ask the server
        return self.rpc_client.ctypes_GetLastError()

    def ctypes_set_last_error(self, value):

        # If in stage 1, fire up stage 2
        if self.stage == 1:
            self.__init_stage_2__()

        # Ask the server
        return self.rpc_client.ctypes_set_last_error(value)

    def ctypes_WinError(self, code=None, descr=None):

        # If in stage 1, fire up stage 2
        if self.stage == 1:
            self.__init_stage_2__()

        # Ask the server
        return self.rpc_client.ctypes_WinError(code, descr)

    def ctypes_find_msvcrt(self):

        # If in stage 1, fire up stage 2
        if self.stage == 1:
            self.__init_stage_2__()

        # Ask the server
        return self.rpc_client.ctypes_find_msvcrt()

    def ctypes_find_library(self, name):

        # If in stage 1, fire up stage 2
        if self.stage == 1:
            self.__init_stage_2__()

        # Ask the server
        return self.rpc_client.ctypes_find_library(name)

    def ctypes_CFUNCTYPE(self, restype, *argtypes, **kw):

        # If in stage 1, fire up stage 2
        if self.stage == 1:
            self.__init_stage_2__()

        flags = _FUNCFLAG_CDECL

        if kw.pop("use_errno", False):
            flags |= _FUNCFLAG_USE_ERRNO
        if kw.pop("use_last_error", False):
            flags |= _FUNCFLAG_USE_LASTERROR
        if kw:
            raise ValueError("unexpected keyword argument(s) %s" % kw.keys())

        return self.data.generate_callback_decorator(flags, restype, *argtypes)

    def ctypes_WINFUNCTYPE(self, restype, *argtypes, **kw):  # EXPORT

        # If in stage 1, fire up stage 2
        if self.stage == 1:
            self.__init_stage_2__()

        flags = _FUNCFLAG_STDCALL

        if kw.pop("use_errno", False):
            flags |= _FUNCFLAG_USE_ERRNO
        if kw.pop("use_last_error", False):
            flags |= _FUNCFLAG_USE_LASTERROR
        if kw:
            raise ValueError("unexpected keyword argument(s) %s" % kw.keys())

        return self.data.generate_callback_decorator(flags, restype, *argtypes)

    def load_library(self, dll_name, dll_type, dll_param={}):

        # If in stage 1, fire up stage 2
        if self.stage == 1:
            self.__init_stage_2__()

        # Check whether dll has already been touched
        if dll_name in self.dll_dict.keys():

            # Return reference on existing dll object
            return self.dll_dict[dll_name]

        # Is DLL type known?
        if dll_type not in ["cdll", "windll", "oledll"]:

            # Raise error if unknown
            raise ValueError("unknown dll type")

        # Fix parameters dict with defauls values
        if "mode" not in dll_param.keys():
            dll_param["mode"] = 0
        if "use_errno" not in dll_param.keys():
            dll_param["use_errno"] = False
        if "use_last_error" not in dll_param.keys():
            dll_param["use_last_error"] = False

        # Log status
        self.log.out(
            '[session-client] Attaching to DLL file "%s" with calling convention "%s" ...'
            % (dll_name, dll_type)
        )

        try:

            # Tell wine about the dll and its type
            hash_id = self.rpc_client.load_library(dll_name, dll_type, dll_param)

        except OSError as e:

            # Log status
            self.log.out("[session-client] ... failed!")

            # If DLL was not found, reraise error
            raise e

        # Fire up new dll object
        self.dll_dict[dll_name] = dll_client_class(self, dll_name, dll_type, hash_id)

        # Log status
        self.log.out("[session-client] ... attached.")

        # Return reference on existing dll object
        return self.dll_dict[dll_name]

    def path_unix_to_wine(self, in_path):

        if not isinstance(in_path, str):
            raise TypeError("in_path must by of type str")

        # If in stage 1, fire up stage 2
        if self.stage == 1:
            self.__init_stage_2__()

        # Ask the server
        return self.rpc_client.path_unix_to_wine(in_path)

    def path_wine_to_unix(self, in_path):

        if not isinstance(in_path, str):
            raise TypeError("in_path must by of type str")

        # If in stage 1, fire up stage 2
        if self.stage == 1:
            self.__init_stage_2__()

        # Ask the server
        return self.rpc_client.path_wine_to_unix(in_path)

    def get_parameter(self, key):

        return self.p[key]

    def set_parameter(self, key, value):

        self.p[key] = value

        if self.stage > 1:
            self.rpc_client.set_parameter(parameter)

    def terminate(self, signum=None, frame=None):

        # Run only if session is still up
        if not self.up:
            return

        # Log status
        self.log.out("[session-client] TERMINATING ...")

        # Only if in stage 2:
        if self.stage == 2:

            try:

                # Tell server via message to terminate
                self.rpc_client.terminate()

            except EOFError:

                # EOFError is raised if server socket is closed - ignore it
                self.log.out("[session-client] Remote socket closed.")

            # Wait for server to appear
            self.__wait_for_server_status_change__(target_status=False)

            # Destruct interpreter session
            self.interpreter_session.terminate()

        # Terminate callback server
        self.rpc_server.terminate()

        # Log status
        self.log.out("[session-client] TERMINATED.")

        # Terminate log
        self.log.terminate()

        # Session down
        self.up = False

    def __init_stage_1__(self, parameter, force_stage_2):

        # Fill empty parameters with default values and/or config file contents
        self.p = config_class(**parameter)

        # Get and set session id
        self.id = self.p["id"]

        # Start RPC server for callback routines
        self.__start_rpc_server__()

        # Start session logging
        self.log = log_class(self.id, self.p, rpc_server=self.rpc_server)

        # Log status
        self.log.out("[session-client] STARTING (STAGE 1) ...")
        self.log.out(
            "[session-client] Configured Wine-Python version is %s for %s."
            % (self.p["pythonversion"], self.p["arch"])
        )
        self.log.out(
            "[session-client] Log socket port: %d." % self.p["port_socket_unix"]
        )

        # Store current working directory
        self.dir_cwd = os.getcwd()

        # Set data cache and parser
        self.data = data_class(
            self.log, is_server=False, callback_server=self.rpc_server
        )

        # Set up a dict for loaded dlls
        self.dll_dict = {}

        # Mark session as up
        self.up = True

        # Marking server component as down
        self.server_up = False

        # Set current stage to 1
        self.stage = 1

        # Register session destructur
        atexit.register(self.terminate)
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)

        # Log status
        self.log.out("[session-client] STARTED (STAGE 1).")

        # If stage 2 shall start with force ...
        if force_stage_2:
            self.__init_stage_2__()

    def __init_stage_2__(self):

        # Log status
        self.log.out("[session-client] STARTING (STAGE 2) ...")

        # Ensure a working Wine-Python environment
        env = Env(**self.p)
        env.ensure()
        env.setup_zugbruecke()

        # Prepare python command for ctypes server or interpreter
        self.__prepare_python_command__()

        # Initialize interpreter session
        self.interpreter_session = Interpreter(self.id, self.p, self.log)

        # Wait for server to appear
        self.__wait_for_server_status_change__(target_status=True)

        # Try to connect to Wine side
        self.__start_rpc_client__()

        # Set current stage to 2
        self.stage = 2

        # Log status
        self.log.out("[session-client] STARTED (STAGE 2).")

    def __set_server_status__(self, status):

        # Interface for session server through RPC
        self.server_up = status

    def __start_rpc_client__(self):

        # Fire up xmlrpc client
        self.rpc_client = mp_client_safe_connect(
            socket_path=("localhost", self.p["port_socket_wine"]),
            authkey="zugbruecke_wine",
            timeout_after_seconds=self.p["timeout_start"],
        )

    def __start_rpc_server__(self):

        # Get socket for callback bridge
        self.p["port_socket_unix"] = get_free_port()

        # Create server
        self.rpc_server = mp_server_class(
            ("localhost", self.p["port_socket_unix"]), "zugbruecke_unix"
        )  # Log is added later

        # Interface to server to indicate its status
        self.rpc_server.register_function(
            self.__set_server_status__, "set_server_status"
        )

        # Start server into its own thread
        self.rpc_server.server_forever_in_thread()

    def __prepare_python_command__(self):

        # Get socket for ctypes bridge
        self.p["port_socket_wine"] = get_free_port()

        # Prepare command with minimal meta info. All other info can be passed via sockets.
        self.p["server_command_list"] = [
            "-m",
            "zugbruecke._server_",
            "--id",
            self.id,
            "--port_socket_wine",
            str(self.p["port_socket_wine"]),
            "--port_socket_unix",
            str(self.p["port_socket_unix"]),
            "--log_level",
            str(self.p["log_level"]),
            "--log_write",
            str(int(self.p["log_write"])),
            "--timeout_start",
            str(int(self.p["timeout_start"])),
        ]

    def __wait_for_server_status_change__(self, target_status):

        # Does the status have to change?
        if target_status == self.server_up:

            # No, so get out of here
            return

        # Debug strings
        STATUS_DICT = {True: "up", False: "down"}
        # Config keys for timeouts
        CONFIG_DICT = {True: "timeout_start", False: "timeout_stop"}

        # Log status
        self.log.out(
            "[session-client] Waiting for session-server to be %s ..."
            % STATUS_DICT[target_status]
        )

        # Time-step
        wait_for_seconds = 0.01
        # Timeout
        timeout_after_seconds = self.p[CONFIG_DICT[target_status]]
        # Already waited for ...
        started_waiting_at = time.time()

        # Run loop until socket appears
        while target_status != self.server_up:

            # Wait before trying again
            time.sleep(wait_for_seconds)

            # Time out
            if time.time() >= (started_waiting_at + timeout_after_seconds):
                break

        # Handle timeout
        if target_status != self.server_up:

            # Log status
            self.log.out(
                "[session-client] ... wait timed out (after %0.2f seconds)."
                % (time.time() - started_waiting_at)
            )

            if target_status:
                raise TimeoutError("session server did not appear")
            else:
                raise TimeoutError("session server could not be stopped")

        # Log status
        self.log.out(
            "[session-client] ... session server is %s (after %0.2f seconds)."
            % (STATUS_DICT[target_status], time.time() - started_waiting_at)
        )
