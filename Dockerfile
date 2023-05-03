# define the version of Python here
FROM python:3.9.1

# optional labels to provide metadata for the Docker image
# (source: address to the repository, description: human-readable description)
LABEL org.opencontainers.image.source https://github.com/simcesplatform/Controller.git
LABEL org.opencontainers.image.description "Docker image for the controller component."

RUN mkdir -p /controller
RUN mkdir -p /init
RUN mkdir -p /logs
RUN mkdir -p /domain-messages


COPY requirements.txt /requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /requirements.txt

COPY controller/ /controller/
COPY init/ /init/
COPY domain-messages/ /domain-messages/

WORKDIR /

CMD [ "python3", "-u", "-m", "controller.component" ]
