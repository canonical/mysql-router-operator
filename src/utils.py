# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utility functions."""

import secrets
import string


def generate_password(password_length: int = 24) -> str:
    """Generate a random password of the provided password length."""
    choices = string.ascii_letters + string.digits
    return "".join(secrets.choice(choices) for _ in range(password_length))
