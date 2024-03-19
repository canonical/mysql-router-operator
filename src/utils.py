# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utility functions."""

import secrets
import string


def generate_password() -> str:
    """Generate a random password."""
    choices = string.ascii_letters + string.digits
    return "".join(secrets.choice(choices) for _ in range(24))
