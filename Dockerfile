# define the version of Python here
FROM python:3.9.1
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

CMD [ "python", "-u", "-m", "controller.controller" ]
