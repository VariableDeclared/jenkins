import asyncio
import pytest
import subprocess
import yaml
import time
import os
import re
from .base import (
    UseModel,
    _juju_wait,
    run_test
)
from .utils import (
    asyncify,
    verify_ready,
    verify_completed,
    verify_deleted,
    retry_async_with_timeout
)
from .logger import log, log_calls_async
from juju.controller import Controller
from juju.errors import JujuError

LXD_PROFILE = {
    'config': {
        'boot.autostart': 'true',
        'linux.kernel_modules': 'ip_tables,ip6_tables,netlink_diag,nf_nat,overlay',
        'raw.lxc': 'lxc.apparmor.profile=unconfined\nlxc.mount.auto=proc:rw sys:rw\nlxc.cap.drop=\n',
        'security.nesting': 'true',
        'security.privileged': 'true'
    },
    'description': '',
    'devices': {
        'aadisable': {
            'path': '/sys/module/nf_conntrack/parameters/hashsize',
            'source': '/dev/null',
            'type': 'disk'
        },
        'aadisable1': {
            'path': '/sys/module/apparmor/parameters/enabled',
            'source': '/dev/null',
            'type': 'disk'
        },
        'aadisable2': {
            'path': '/dev/kmsg',
            'source': '/dev/kmsg',
            'type': 'unix-char'
        }
    }
}


async def check_charm_profile_deployed(app, charm_name):
    machine = app.units[0]
    log('app_info %s' % machine.safe_data)
    # Assume that the only profile with juju-* is
    # the one we're looking for.
    result = subprocess.run(
        ['lxc', 'profile', 'list'],
        stdout=subprocess.PIPE
    )
    for profile_line in result.stdout.decode('utf-8').split('\n'):
        match = re.search(
            r"juju-(([a-zA-Z0-9])+-)*{}-[a-zA-Z0-9]*".format(
                charm_name.split('-')[-1]
            ),
            profile_line
        )
        if match is not None:
            model_name = match.group()
            break

    log('Checking profile for name: %s' % model_name)
    # In 3.7 stdout=subprocess.PIPE
    # can be replaced with capture_output... :-]
    result = subprocess.run(
        ['lxc', 'profile', 'show', model_name],
        stdout=subprocess.PIPE
    )

    config = result.stdout.decode('utf-8')

    loaded_yaml = yaml.load(config)

    # Remove these keys as they differ at run time and are
    # not related to the configuration.
    loaded_yaml.pop("name", None)
    loaded_yaml.pop("used_by", None)

    log('Deployed Profile: %s' % loaded_yaml)
    log('Expected Profile: %s' % LXD_PROFILE)
    assert loaded_yaml == LXD_PROFILE


@log_calls_async
async def test_lxd_profile_deployed(**kwargs):
    model = kwargs['model']
    for name in kwargs['charm_names']:
        app = model.applications[name]
        await check_charm_profile_deployed(app, name)


@log_calls_async
async def test_lxd_profile_deployed_upgrade(**kwargs):
    model = kwargs['model']
    for name in kwargs['charm_names']:
        app = model.applications[name]
        log('Upgrading charm to edge channel')
        await app.upgrade_charm(channel='edge')
        log('Waiting for model settle.')
        asyncify(_juju_wait)()
        await check_charm_profile_deployed(app, name)


@pytest.mark.asyncio
async def test_lxd_profiles(log_dir):
    await run_test(
        test_function=test_lxd_profile_deployed,
        charm_names=['kubernetes-worker', 'kubernetes-master'],
        charm_version=os.environ['CHARM_VERSION']
    )


@pytest.mark.asyncio
async def test_lxd_profile_upgrade():
    await run_test(
        test_function=test_lxd_profile_deployed_upgrade,
        charm_names=['kubernetes-master', 'kubernetes-worker'],
        charm_version=os.environ['CHARM_VERSION']
    )
