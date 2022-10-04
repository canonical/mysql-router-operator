# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""A collection of utility functions that are used in the charm."""

import secrets
import string


def generate_random_chars(length: int) -> str:
    """Randomly generate a string.

    Args:
        length: length of the randomly generated string

    Returns:
        a string with random letters and digits of length specified
    """
    choices = string.ascii_letters + string.digits
    return "".join([secrets.choice(choices) for i in range(length)])
