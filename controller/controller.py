import asyncio
from typing import Any, cast, Set, Union

from tools.components import AbstractSimulationComponent
from tools.exceptions.messages import MessageError
from tools.messages import BaseMessage,StatusMessage
from tools.tools import FullLogger, load_environmental_variables

# import all the required messages from installed libraries
from domain_messages.dispatch.dispatch import ResourceForecastStateDispatchMessage
from domain_messages.ControlState.ControlState_Power_Setpoint import ControlStatePowerSetpointMessage

# initialize logging object for the module
LOGGER = FullLogger(__name__)
RESOURCE_FORECASTE_STATE_DISPTCH_TOPIC = "RESOURCE_FORECASTE_STATE_DISPTCH_TOPIC"
CONTROL_STATE_POWERSETPOINT_TOPIC = 'CONTROL_STATE_POWERSETPOINT_TOPIC'

# time interval in seconds on how often to check whether the component is still running
TIMEOUT = 1.0


class Controller(AbstractSimulationComponent):
    """
    This is a controller, a simulation platform component. The task of this component is to listen ResourceForecasteState.Dispatch
    and publish ControlState.PowerSetpoint messages to corresponding resources.
    """
    def __init__(
            self):
        # This will initialize various variables including the message client for message bus access.
        super().__init__()

        # variables to keep track of the components that have provided input within the current epoch
        self._current_input_components = set()
        # Load environmental variables for those parameters that were not given to the constructor.
        environment = load_environmental_variables(
            (RESOURCE_FORECASTE_STATE_DISPTCH_TOPIC, str, "ResourceForecastState.Dispatch"),
            (CONTROL_STATE_POWERSETPOINT_TOPIC,str,"ControlState.PowerSetpoint")
        )
        self._simple_topic_base = cast(str, environment[CONTROL_STATE_POWERSETPOINT_TOPIC])
        self._simple_topic_output = ".".join([self._simple_topic_base])
        self._other_topics = [
            cast(str, environment[RESOURCE_FORECASTE_STATE_DISPTCH_TOPIC])
        ]
        if self.start_message is None:
            self._dispacth_names = set()
        else:
            self._dispacth_names = set(list(self.start_message.get("ProcessParameters", {}).get("EconomicDispatch", {})))
        if len(self._dispacth_names)<1:
            LOGGER.error("No economic dispatch is found in start messages")
        
        self._resource_forecast_state_dispatches_for_epoch = []

    def clear_epoch_variables(self) -> None:
        """Clears all the variables that are used to store information about the received input within the
           current epoch. This method is called automatically after receiving an epoch message for a new epoch.
        """
        self._resource_forecast_state_dispatches_for_epoch = []
        self._current_input_components = set()

    async def process_epoch(self) -> bool:
        """ return True when the epoch processing is finished and controller is ready to send Status ready message.
        """
        await self._send_control_state_powersetpoint_message()
        return True

    async def all_messages_received_for_epoch(self) -> bool:
        """
        To check all the input components is available for generate ControlState.PowerSetpoint message
        """
        return self._dispacth_names == self._current_input_components

        
    async def general_message_handler(self, message_object: Union[BaseMessage, Any],
                                      message_routing_key: str) -> None:
        """
        TODO: ResourceForecasteStateDispatch message is handled here.
        """

        if isinstance(message_object,ResourceForecastStateDispatchMessage):
            message_object = cast(ResourceForecastStateDispatchMessage, message_object)
            # ignore simple messages from components that have not been registered as input components
            if message_object.source_process_id not in self._dispacth_names:
                LOGGER.debug("Ignoring ResourceForecasteStateDispatch from {}".format(message_object.source_process_id))

            elif message_object.source_process_id in self._current_input_components:
                LOGGER.info("Ignoring new ResourceForecasteStateDispatch from {}".format(message_object.source_process_id))

            else:
                LOGGER.debug("Received ResourceForecasteStateDispatch from {}".format(message_object.source_process_id))
                self._resource_forecast_state_dispatches_for_epoch.append(message_object)
                self._current_input_components.add(message_object.source_process_id)
                self._triggering_message_ids.append(message_object.message_id)
                if not await self.start_epoch():
                    LOGGER.debug("Waiting for other input messages before processing epoch {:d}".format(
                        self._latest_epoch))
        else:
            LOGGER.debug("Received unknown message from {}: {}".format(message_routing_key, message_object))

    async def _send_control_state_powersetpoint_message(self):
        '''
       Send the Control message to the resources.
        '''
        for dispatch_message in self._resource_forecast_state_dispatches_for_epoch:
            for resourceName in dispatch_message.dispatch.keys():
                self._result_topic = '.'.join( [ self._simple_topic_output,resourceName])
                control_state = self._get_control_state_message(resourceName,dispatch_message)
                await self._rabbitmq_client.send_message(self._result_topic, control_state.bytes())


    def _get_control_state_message(self,resource_name,message) -> ControlStatePowerSetpointMessage:
        real_power=message.dispatch[resource_name].series["RealPower"].values[0]
        if 'ReactivePower' in message.dispatch[resource_name].series.keys():
            reactive_power=message.dispatch[resource_name].series["ReactivePower"].values[0]
        else:
            reactive_power=0
        message=self._message_generator.get_message(
                ControlStatePowerSetpointMessage,
                EpochNumber=self._latest_epoch,
                TriggeringMessageIds=self._triggering_message_ids,
                RealPower = real_power,
                ReactivePower = reactive_power
        )

        return message

def create_component() -> Controller:
    """
    Creates and returns a Controller componet 
    """
    return Controller()
        
async def start_component():
    """
    Creates and starts a Controller component.
    """
    Controller = create_component()

    # The controller will only start listening to the message bus once the start() method has been called.
    await Controller.start()

    # Wait in the loop until the controller has stopped itself.
    while not Controller.is_stopped:
        await asyncio.sleep(TIMEOUT)


if __name__ == "__main__":
    asyncio.run(start_component())
