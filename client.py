"""This module contains code example to instantiate RabbitmqClient object."""
import init
from tools.clients import RabbitmqClient


def get_client() -> RabbitmqClient:
    """Returns a RabbitmqClient instance."""
    # Replace the parameters with proper values for host, port, login and password
    # Change the value of exchange if needed.
    #
    # For any parameter that is not given here, the client tries to use a value from an environment variable
    # and most of the parameters also have a default value that is used if neither the constructor parameter
    # nor the environmental variable exist.
    # See tools/clients.py for details about the environmental variables and the default values.
    return RabbitmqClient(
        exchange="procem.test",
        exchange_autodelete=True,
        exchange_durable=False
    )
