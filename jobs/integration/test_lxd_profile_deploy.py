import asyncio
import pytest
import subprocess
import yaml
import time
import os
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


@log_calls_async
async def test_lxd_profile_deploy_force(model, charm_name, charm_version):
    log('Deploying a the LXD charm')

    # app = await model.deploy(
    #     "cs:~containers/{}-{}".format(
    #         charm_name,
    #         charm_version
    #     )
    # )
    # ##### CHANGE: Testing purposes.
    app = await model.deploy(charm_name, force=False)
    # #####
    time.sleep(20)
    log('waiting...')
    asyncify(_juju_wait)

    machine = app.units[0]
    log('app_info %s' % machine.safe_data)

    model_name = 'juju-{}-{}-{}'.format(
        os.environ['MODEL'],
        machine.safe_data['application'],
        machine.safe_data['name'].split('/')[1]
    )
    log('Checking model for name: %s' % model_name)
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
    # .split(/) -- TESTING -REMOVE
    await model.applications[charm_name.split('/')[-1]].destroy()

    log('Waiting...')
    asyncify(_juju_wait)

    async def test_deploy_fail(model):
        # await model.deploy(
        #     "cs:~containers/{}-{}".format(
        #         charm_name,
        #         charm_version
        #     ),
        #   force=False
        # )
        # ##### CHANGE: Testing purposes.
        await model.deploy(charm_name, force=False)
        # #####
    with pytest.raises(JujuError, match=r"$[a-zA-Z]* invalid lxd-profile [a-zA-Z]*"):
        await test_deploy_fail(model)


@pytest.mark.asyncio
async def test_lxd_profiles(log_dir):
    controller = Controller()
    await controller.connect()
    async with UseModel() as model:
        log('Calling lxd deploy')
        # await test_lxd_profile_deploy_force(
        #     model,
        #     os.environ['CHARM_NAME'],
        #     os.environ['CHARM_VERSION']
        # )
        # ###### TESTING ######
        await test_lxd_profile_deploy_force(
            model,
            "/home/pjds/charms/builds/kubernetes-worker",
            os.environ['CHARM_VERSION']
        )


def test_lxd_profile_upgrade