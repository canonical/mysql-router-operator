# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import juju.unit


async def run_action(unit: juju.unit.Unit, action_name, **params):
    action = await unit.run_action(action_name=action_name, **params)
    result = await action.wait()

    assert result.results.get("return-code") == 0
    return result.results
