# -*- coding: utf-8 -*-

"""This module contains a class for creating and holding messages for the RabbitMQ message bus."""

# import these for backwards compatibility
from tools.message.abstract import BaseMessage, AbstractMessage      # pylint: disable=unused-import
from tools.message.abstract import AbstractResultMessage, get_json   # pylint: disable=unused-import
from tools.message.block import QuantityBlock                        # pylint: disable=unused-import
from tools.message.block import ValueArrayBlock, QuantityArrayBlock  # pylint: disable=unused-import
from tools.message.block import TimeSeriesBlock                      # pylint: disable=unused-import
from tools.message.epoch import EpochMessage                         # pylint: disable=unused-import
from tools.message.factory import MessageFactory                     # pylint: disable=unused-import
from tools.message.general import GeneralMessage, ResultMessage      # pylint: disable=unused-import
from tools.message.generator import MessageGenerator                 # pylint: disable=unused-import
from tools.message.simulation_state import SimulationStateMessage    # pylint: disable=unused-import
from tools.message.status import StatusMessage                       # pylint: disable=unused-import
from tools.message.utils import get_next_message_id                  # pylint: disable=unused-import

from tools.tools import FullLogger

LOGGER = FullLogger(__name__)
