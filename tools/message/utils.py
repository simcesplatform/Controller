# -*- coding: utf-8 -*-

"""This module contains general utils for working with simulation platform message classes."""

from typing import Iterator


def get_next_message_id(source_process_id: str, start_number: int = 1) -> Iterator[str]:
    """Generator for getting unique message ids."""
    message_number = start_number
    while True:
        yield "{:s}-{:d}".format(source_process_id, message_number)
        message_number += 1
