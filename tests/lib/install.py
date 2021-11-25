# -*- coding: utf-8 -*-

"""

ZUGBRUECKE
Calling routines in Windows DLLs from Python scripts running on unixlike systems
https://github.com/pleiszenburg/zugbruecke

    tests/lib/install.py: Sets Wine Python environments up

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

from json import dumps
import os
from subprocess import Popen
from typing import Dict, List

from wenv import (
    EnvConfig,
    PythonVersion,
    get_available_python_builds,
    get_latest_python_build,
)

from .const import (
    ARCHS,
    PYTHONBUILDS_FN,
    PYTHON_MINOR_MAX,
    PYTHON_MINOR_MIN,
)

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ROUTINES
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def install():

    cfg = EnvConfig()
    builds = _get_latest_python_builds()

    _write_python_builds(fn = os.path.join(cfg['prefix'], PYTHONBUILDS_FN), builds = builds)

    for arch in ARCHS:
        for build in builds[arch]:
            _install_env(arch, build)


def _get_latest_python_builds() -> Dict[str, List[PythonVersion]]:

    _builds = get_available_python_builds()

    builds = {
        arch: [
            get_latest_python_build(arch, 3, minor, builds = _builds)
            for minor in range(
                PYTHON_MINOR_MIN,  # min minor version
                PYTHON_MINOR_MAX + 1,  # max major version
            )
        ]
        for arch in ARCHS
    }
    for value in builds.values():
        value.sort()

    return builds


def _install_env(arch: str, build: PythonVersion):

    envvars = os.environ.copy()
    envvars.update({
        'WENV_DEBUG': '1',
        'WENV_ARCH': arch,
        'WENV_PYTHONVERSION': str(build),
    })

    for cmd in (
        ['wenv', 'init'],
        ['wenv', 'pip', 'install', '-r', 'requirements_test.txt'],
        ['wenv', 'init_coverage'],
    ):
        proc = Popen(cmd, env = envvars)
        proc.wait()
        if proc.returncode != 0:
            raise SystemError('wenv setup command failed', arch, build, cmd)


def _write_python_builds(fn: str, builds: Dict[str, List[PythonVersion]]):

    with open(fn, mode = "w", encoding="utf-8") as f:
        f.write(dumps({
            arch: [
                build.as_config() for build in _builds
            ] for arch, _builds in builds.items()
        }))

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# MODULE ENTRY POINT
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

if __name__ == "__main__":

    install()