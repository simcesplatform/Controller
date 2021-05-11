import asyncio
import datetime
from typing import List, Tuple, Union, cast
import os
# from collections import namedtuple
# import isodate
import json

import unittest
#import aiounittest

from tools.clients import RabbitmqClient
from tools.components import AbstractSimulationComponent, SIMULATION_START_MESSAGE_FILENAME
from tools.tests.components import MessageGenerator, TestAbstractSimulationComponent, MessageStorage, send_message
from tools.tests.components import TestAbstractSimulationComponent
from domain_messages.ControlState.ControlState_Power_Setpoint import ControlStatePowerSetpointMessage
from tools.messages import AbstractMessage, MessageGenerator as GeneralMessageGenerator
from tools.datetime_tools import to_iso_format_datetime_string
# from tools.message.block import TimeSeriesBlock, ValueArrayBlock, QuantityBlock

#from domain_messages.resource import ResourceStateMessage
#from domain_messages.price_forecaster import PriceForecastStateMessage
#from domain_messages.resource_forecast import ResourceForecastPowerMessage

from controller.controller import create_component
from domain_messages.dispatch import ResourceForecastStateDispatchMessage
# from economic_dispatch.simulation.message import DispatchBlock, ResourceForecastStateDispatchMessage

# from economic_dispatch.simulation.tests.message_generators import DispatchMessageGenerator

# test data
#from economic_dispatch.simulation.tests.message_generators import DISPATCHES, #
    #STORAGE_STATES, PRICE_FORECASTS


SIMULATION_EPOCHS = 5
SIMULATION_ID = "2020-01-01T00:00:00.000Z"
INITIAL_START_TIME = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
DISPATCH_TOPIC = "ResourceForecastState.Dispatch"
# DEMO_INPUT_GENERATORS = [
#     DispatchMessageGenerator(simulation_id=SIMULATION_ID, process_id="EconomicDispatchA", dispatches=[]),
#     DispatchMessageGenerator(simulation_id=SIMULATION_ID, process_id="EconomicDispatchB", dispatches=[]),
#     ##ResourceStateMessageGenerator(simulation_id=SIMULATION_ID, process_id="Battery", states=STORAGE_STATES),
# ]
RESOURCE_NAMES = {
    "EconomicDispatchA": ["ResourceA1", "ResourceA2"],
    "EconomicDispatchB": ["ResourceB1", "ResourceB2"]
}
TIME_SERIES_LENGTH = 4
DISPATCH_NAMES = ["EconomicDispatchA", "EconomicDispatchB"]
CONTROLLER_NAME = "controller-test"

START = {
    "ProcessParameters": {
        "EconomicDispatch": {
            "EconomicDispatchA": {},
            "EconomicDispatchB": {}
        },
        "Controller": {
            CONTROLLER_NAME: {}
        }
    }
}


# specify component initialization environment variables.
start_fname = "test_start.json"
with open(start_fname, 'w') as JSON:
    json.dump(START, JSON)
os.environ[SIMULATION_START_MESSAGE_FILENAME] = str(start_fname)


def get_time_string(hours: int) -> str:
    """Returns datetime as string in ISO 8601 format."""
    return cast(str, to_iso_format_datetime_string(INITIAL_START_TIME + datetime.timedelta(hours=hours)))


def get_dispatch_message(message_generator: GeneralMessageGenerator, resources: List[str], epoch_number: int, triggering_message_ids:List[str]) \
        -> AbstractMessage:
    """Returns a dispatch message."""
    return message_generator.get_message(
        ResourceForecastStateDispatchMessage,
        EpochNumber=epoch_number,
        TriggeringMessageIds=triggering_message_ids,
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


def get_controller_messages(message_generator: GeneralMessageGenerator, epoch_number: int,
        triggering_message_ids: List[str]) -> List[Tuple[AbstractMessage, str]]:
    messages = []
    topics = []
    all_resources = [resource for resource_list in list(RESOURCE_NAMES.values()) for resource in resource_list]
    for resource_index, resource_name in enumerate(all_resources, start=1):
        message = message_generator.get_message(
            ControlStatePowerSetpointMessage,
            EpochNumber=epoch_number,
            TriggeringMessageIds=triggering_message_ids,
            RealPower=100 + resource_index * 10 + (epoch_number - 1) * 0.1,
            ReactivePower=10 + resource_index * 1 + (epoch_number - 1) * 0.1
        )
        topic = '.'.join(["ControlStatePowersetpoint", resource_name])
        messages.append(message)
        topics.append(topic)
    return [(m, t) for m, t in zip(messages, topics) if m is not None]


class TestController(TestAbstractSimulationComponent):
    """Unit tests for Controller component."""

    simulation_id = SIMULATION_ID
    component_name = CONTROLLER_NAME

    short_wait = 1.0
    long_wait = 4.0

    # the method which initializes the component
    component_creator = create_component

    dispatch_generators = [
        GeneralMessageGenerator(
            simulation_id=SIMULATION_ID,
            source_process_id=dispatch_name
        )
        for dispatch_name in DISPATCH_NAMES
    ]
    print(zip(DISPATCH_NAMES, dispatch_generators))
    controller_generator = GeneralMessageGenerator(simulation_id=SIMULATION_ID, source_process_id=CONTROLLER_NAME)

    normal_simulation_epochs = SIMULATION_EPOCHS

    def get_input_messages(self, dispatch_generators: List[GeneralMessageGenerator], epoch_number: int,
                           triggering_message_ids: List[str]) -> List[Tuple[AbstractMessage, str]]:
        """Get the messages and topics the component is expected to publish in given epoch."""
        if epoch_number == 0:
            return []
        messages = []
        topics = []
        for dispatch_name, dispatch_generator in zip(DISPATCH_NAMES, dispatch_generators):
            message = get_dispatch_message(dispatch_generator, RESOURCE_NAMES[dispatch_name], epoch_number, triggering_message_ids)
            messages.append(message)
            topics.append(DISPATCH_TOPIC)

        return [(m, t) for m, t in zip(messages, topics) if m is not None]

    def get_expected_messages(self, component_message_generator: GeneralMessageGenerator, epoch_number: int,
                              triggering_message_ids: List[str]) -> List[Tuple[AbstractMessage, str]]:
        """Get the messages and topics the component is expected to publish in given epoch."""
        if epoch_number == 0:
            return [
                (component_message_generator.get_status_ready_message(epoch_number, triggering_message_ids), "Status.Ready")
            ]

        return [
            *(get_controller_messages(component_message_generator, epoch_number, triggering_message_ids)),
            (component_message_generator.get_status_ready_message(epoch_number, triggering_message_ids), "Status.Ready")
        ]

    async def start_tester(self) -> Tuple[RabbitmqClient, MessageStorage,
                                          MessageGenerator, AbstractSimulationComponent]:
        """Tests the creation of the test component at the start of the simulation and returns a 5-tuple containing
           the message bus client, message storage object, test component message generator object,
           test input message generator object and the test component object for the use of further tests."""

        await asyncio.sleep(self.__class__.long_wait)

        message_storage = MessageStorage(self.__class__.test_manager_name)
        message_client = RabbitmqClient()
        message_client.add_listener("#", message_storage.callback)

        # input_message_generator = self.__class__.input_message_generator_type(self.input_generators)
        component_message_generator = self.__class__.message_generator_type(
            self.__class__.simulation_id, self.__class__.component_name)
        test_component = self.__class__.component_creator(**self.__class__.component_creator_params)
        await test_component.start()
        # Wait for a few seconds to allow the component to setup.
        await asyncio.sleep(self.__class__.short_wait)
        self.assertFalse(message_client.is_closed)
        self.assertFalse(test_component.is_stopped)
        self.assertFalse(test_component.is_client_closed)
        self.assertEqual(test_component.simulation_id, self.__class__.simulation_id)
        self.assertEqual(test_component.component_name, self.__class__.component_name)
        return (message_client, message_storage, component_message_generator, test_component)

    async def epoch_tester(self, epoch_number: int, last_status_message_id: str, message_client: RabbitmqClient,
                           message_storage: MessageStorage) -> str:
        """Test the behavior of the test_component in one epoch."""

        number_of_previous_messages = len(message_storage.messages_and_topics)
        if epoch_number == 0:
            # Epoch number 0 corresponds to the start of the simulation.
            manager_message = self.__class__.manager_message_generator.\
                get_simulation_state_message(True)
            component_inputs = []
            expected_responds = []
        else:
            manager_message = self.__class__.manager_message_generator.get_epoch_message(
                epoch_number, [last_status_message_id])
            component_inputs = self.get_input_messages(
                self.dispatch_generators, epoch_number, [manager_message.message_id])
            input_message_ids = [message.message_id for message, _ in component_inputs]
            expected_responds = self.get_expected_messages(
                self.controller_generator, epoch_number, [manager_message.message_id, *input_message_ids])

        await send_message(message_client, manager_message, manager_message.message_type)

        # Clear epoch variables

        for input_message, topic_name in component_inputs:
            await send_message(message_client, input_message, topic_name)

        # Wait to allow the message storage to store the respond. Wait epoch processing? (not ready)
        #if epoch_number != 0:
        #    await test_component._event.wait()
        await asyncio.sleep(self.__class__.long_wait)

        received_messages = message_storage.messages_and_topics
        self.assertEqual(len(received_messages), number_of_previous_messages + len(component_inputs) + len(expected_responds))

        # Compare the received messages to the expected messages.
        # TODO: implement message checking that does not care about the order of the received messages
        for index, (received_responce, expected_responce) in enumerate(
                zip(received_messages[-len(expected_responds):], expected_responds),
                start=1):
            with self.subTest(message_index=index):
                received_message, received_topic = received_responce
                expected_message, expected_topic = expected_responce
                self.assertEqual(received_topic, expected_topic)
                self.assertTrue(self.compare_message(received_message, expected_message))

        return expected_responds[-1][0].message_id

    async def test_normal_simulation(self):
        """A test with a normal input in a simulation containing only manager and test component."""
        # Test the creation of the test component.
        message_client, message_storage, component_message_generator, test_component = \
            await self.start_tester()

        last_status_message_id = "no-message-1"
        # Test the component with the starting simulation state message (epoch 0) and n normal epochs.
        for epoch_number in range(0, self.__class__.normal_simulation_epochs + 1):
            with self.subTest(epoch_number=epoch_number):
                last_status_message_id = await self.epoch_tester(
                    epoch_number, last_status_message_id, message_client, message_storage)

        # Test the closing down of the test component after simulation state message "stopped".
        await self.end_tester(message_client, test_component)

    @unittest.skip("not implemented")
    async def test_error_message(self):
        """Unit test for simulation component sending an error message."""
        # Setup the component and start the simulation.
        """
        message_client, message_storage, component_message_generator, input_message_generator, test_component = \
            await self.start_tester()
        await self.epoch_tester(0, message_client, message_storage, component_message_generator, input_message_generator)

        # Generate the expected error message and check if it matches to the one the test component sends.
        error_description = "Testing error message"
        expected_message = component_message_generator.get_error_message(
            epoch_number=0,
            triggering_message_ids=[self.__class__.manager_message_generator.latest_message_id],
            description=error_description)
        number_of_previous_messages = len(message_storage.messages_and_topics)
        await test_component.send_error_message(error_description)

        # Wait a short time to ensure that the message receiver has received the error message.
        await asyncio.sleep(self.__class__.short_wait)

        # Check that the correct error message was received.
        self.assertEqual(len(message_storage.messages_and_topics), number_of_previous_messages + 1)
        received_message, received_topic = message_storage.messages_and_topics[-1]
        self.assertEqual(received_topic, "Status.Error")
        self.assertTrue(self.compare_message(received_message, expected_message))

        await self.end_tester(message_client, test_component) """
        return

    def compare_control_message(self, first_message: ControlStatePowerSetpointMessage, second_message: ControlStatePowerSetpointMessage):
        """Check that the two ControlStatePowerSetpointMessage messages have the same content."""
        self.compare_abstract_result_message(first_message, second_message)
        self.assertAlmostEqual(first_message.real_power.value, second_message.real_power.value)

    def compare_message(self, first_message: AbstractMessage, second_message: AbstractMessage) -> bool:
        """Override the super class implementation to add the comparison of ControlStatePowerSetpointMessage messages."""
        if super().compare_message(first_message, second_message):
            return True

        if isinstance(second_message, ControlStatePowerSetpointMessage):
            self.compare_control_message(cast(ControlStatePowerSetpointMessage, first_message), second_message)
            return True

        return False


# # To skip baseclass tests
del TestAbstractSimulationComponent
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_zero_time']
    unittest.main()

