# Controller

A component for simulating a controller for sending control information to the resources.The task of this component is to listen ResourceForecasteState.Dispatch and publish ControlState.PowerSetpoint messages to corresponding resources.

## Requirements

- python 3.7
- pip for installing requirements

Install requirements:
# install required packages
pip install -r requirements.txt
```


The test can be executed by using docker compose file  

```html
docker-compose -f docker-compose-test.yml up --build
```
