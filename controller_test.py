# -*- coding: utf-8 -*-

"""This module contains code examples related to using the message classes."""

import asyncio
import datetime
import logging
from typing import cast, List

from client import get_client
from tools.datetime_tools import to_iso_format_datetime_string
from tools.message.abstract import AbstractMessage
from tools.messages import MessageGenerator, StatusMessage
from tools.tools import FullLogger

from domain_messages.dispatch.dispatch import ResourceForecastStateDispatchMessage
from domain_messages.ControlState.ControlState_Power_Setpoint import ControlStatePowerSetpointMessage

# use the FullLogger for logging to show the output on the screen as well as to store it to a file
# the default file name for the log output is logfile.out
# the file name can be changed by using the environment variable SIMULATION_LOG_FILE
# in python code that can be done by:
#     import os
#     os.environ["SIMULATION_LOG_FILE"] = "my_logs.txt"
LOGGER = FullLogger(__name__, logger_level=logging.INFO)

SIMULATION_ID = "2000-01-01T12:00:00.000Z"
EPOCH_TOPIC = "Epoch"
STATUS_TOPIC = "Status.Ready"
SIMSTATE_TOPIC = "SimState"
DISPATCH_TOPIC = "ResourceForecastState.Dispatch"
WAIT_BETWEEN_MESSAGES = 4.0
INITIAL_START_TIME = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

DISPATCH_NAMES = ["EconomicDispatchA", "EconomicDispatchB"]
#DISPATCH_NAMES = ["EconomicDispatchA"]
RESOURCE_NAMES = {
    "EconomicDispatchA": ["ResourceA1", "ResourceA2"],
    "EconomicDispatchB": ["ResourceB1", "ResourceB2"]
}
TIME_SERIES_LENGTH = 4

# get a RabbitmqClient by using the parameters defined in client.py
client = get_client()

manager_generator = MessageGenerator(
    simulation_id=SIMULATION_ID,
    source_process_id="SimulationManager")


def get_time_string(hours: int) -> str:
    """Returns datetime as string in ISO 8601 format."""
    return cast(str, to_iso_format_datetime_string(INITIAL_START_TIME + datetime.timedelta(hours=hours)))


def get_dispatch_message(message_generator: MessageGenerator, resources: List[str], epoch_number: int) \
        -> AbstractMessage:
    """Returns a dispatch message."""
    return message_generator.get_message(
        ResourceForecastStateDispatchMessage,
        EpochNumber=epoch_number,
        TriggeringMessageIds=["epoch-message-id"],
        Dispatch={
            resource_name: {
                "TimeIndex": [
                    get_time_string(hour_index)
                    for hour_index in range(epoch_number - 1, epoch_number + TIME_SERIES_LENGTH)
                ],
                "Series": {
                    "RealPower": {
                        "UnitOfMeasure": "kW",
                        "Values": [
                            100 + resource_index * 10 + hour_index * 0.1
                            for hour_index in range(epoch_number - 1, epoch_number + TIME_SERIES_LENGTH)
                        ]
                    },
                    "ReactivePower": {
                        "UnitOfMeasure": "kVA.{r}",
                        "Values": [
                            100 + resource_index * 10 + hour_index * 0.1
                            for hour_index in range(epoch_number - 1, epoch_number + TIME_SERIES_LENGTH)
                        ]
                    }

                }
            }
            for resource_index, resource_name in enumerate(resources, start=1)
        }
    )


async def send_epoch_message(epoch_number: int) -> None:
    """Sends an epoch message and waits a couple of seconds."""
    message = manager_generator.get_epoch_message(
        EpochNumber=epoch_number,
        TriggeringMessageIds=["message-id"],
        StartTime=get_time_string(epoch_number - 1),
        EndTime=get_time_string(epoch_number))
    LOGGER.info("Sending an epoch message for epoch {}".format(epoch_number))
    await client.send_message(EPOCH_TOPIC, message.bytes())
    LOGGER.info("")
    await asyncio.sleep(WAIT_BETWEEN_MESSAGES)


async def start_sender() -> None:
    """
    Starts the test sender.
    """

    dispatch_generators = [
        MessageGenerator(
            simulation_id=SIMULATION_ID,
            source_process_id=dispatch_name
        )
        for dispatch_name in DISPATCH_NAMES
    ]
    print(dispatch_generators)

    
    message = manager_generator.get_simulation_state_message("running")
    LOGGER.info("Sending an simulation state message")
    await client.send_message(SIMSTATE_TOPIC, message.bytes())
    LOGGER.info("")
    await asyncio.sleep(WAIT_BETWEEN_MESSAGES)

    epoch_number = 1
    await send_epoch_message(epoch_number)
    for dispatch_name, dispatch_generator in zip(DISPATCH_NAMES, dispatch_generators):
        message = get_dispatch_message(dispatch_generator, RESOURCE_NAMES[dispatch_name], epoch_number)
        await client.send_message(DISPATCH_TOPIC, message.bytes())
        status_message = dispatch_generator.get_status_ready_message(epoch_number, ["epoch-message-id"])
        await client.send_message(STATUS_TOPIC, status_message.bytes())
        await asyncio.sleep(WAIT_BETWEEN_MESSAGES)
       

    epoch_number += 1
    await send_epoch_message(epoch_number)
    for dispatch_name, dispatch_generator in zip(DISPATCH_NAMES, dispatch_generators):
        message = get_dispatch_message(dispatch_generator, RESOURCE_NAMES[dispatch_name], epoch_number)
        await client.send_message(DISPATCH_TOPIC, message.bytes())
        status_message = dispatch_generator.get_status_ready_message(epoch_number, ["epoch-message-id"])
        await client.send_message(STATUS_TOPIC, status_message.bytes())
        await asyncio.sleep(WAIT_BETWEEN_MESSAGES)
    epoch_number += 1
    await send_epoch_message(epoch_number)
    for dispatch_name, dispatch_generator in zip(DISPATCH_NAMES, dispatch_generators):
        message = get_dispatch_message(dispatch_generator, RESOURCE_NAMES[dispatch_name], epoch_number)
        await client.send_message(DISPATCH_TOPIC, message.bytes())
        status_message = dispatch_generator.get_status_ready_message(epoch_number, ["epoch-message-id"])
        await client.send_message(STATUS_TOPIC, status_message.bytes())
        await asyncio.sleep(WAIT_BETWEEN_MESSAGES)

    control_generator = MessageGenerator(SIMULATION_ID, "Controller")
    control_message = control_generator.get_message(
        ControlStatePowerSetpointMessage,
        EpochNumber=epoch_number,
        TriggeringMessageIds=["epoch-message-id"],
        RealPower=1.0,
        ReactivePower=0.1
    )


if __name__ == '__main__':
    asyncio.run(start_sender())
