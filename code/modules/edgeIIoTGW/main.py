#!/usr/bin/env python

# MIT License

# Copyright (c) Microsoft Corporation. All rights reserved.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE

import asyncio
import logging.config
import sys
import signal
import threading
import json
import traceback
import logging
import os
import time
import uuid

#application modules import
import gw

#azure modules
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import MethodResponse, Message
from azure.iot.device.aio import ProvisioningDeviceClient

IIoTEdgeGW = None

# Event indicating client stop
stop_event = threading.Event()

def create_client():
    global IIoTEdgeGW

    client = None
    client = IoTHubModuleClient.create_from_edge_environment()

    # Define function for handling received messages
    async def receive_message_handler(message):
        print("message", message)
        if not IIoTEdgeGW is None:
            await IIoTEdgeGW.receive_message_handler(message)

    async def method_request_received_handler(method_request):       
        if not IIoTEdgeGW is None:
            await IIoTEdgeGW.method_request_received_handler(method_request)

    try:
        # Set handler on the client
        #set to the GWApp handlers
        if not client is None:
            client.on_message_received = receive_message_handler
            client.on_method_request_received   = method_request_received_handler

    except:
        # Cleanup if failure occurs
        # if not client is None:
        #     client.shutdown()
        raise

    return client

async def run_sample():
    while True:
        if not IIoTEdgeGW is None:
            IIoTEdgeGW.run()
        time.sleep(10)

def main():
    global IIoTEdgeGW
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    print ("Sys.version", sys.version)
    if not sys.version >= "3.5.3":
        raise Exception( "The sample requires python 3.5.3+. Current version of Python: %s" % sys.version )
    logger.info("Application info:" + gw.APP_MODULE_NAME + " v" + gw.APP_MODULE_VER + "")

    # NOTE: Client is implicitly connected due to the handler being set on it
    print("Client")
    client = create_client()

    if client is None:
        logger.info("Local mode (no client)")

    # Define a handler to cleanup when module is is terminated by Edge
    def module_termination_handler(signal, frame):
        if not IIoTEdgeGW is None:
            IIoTEdgeGW.termination_handler()
        stop_event.set()

    # Set the Edge termination handler
    signal.signal(signal.SIGTERM, module_termination_handler)

    # Run the sample
    loop = asyncio.get_event_loop()
    try:
        IIoTEdgeGW = gw.GWApp(client)
        if IIoTEdgeGW is None:
            raise Exception("No gateway object created")
        loop.run_until_complete(run_sample())
    except Exception as e:
        print ( "Unexpected error %s " % e )
        raise
    finally:
        print("Shutting down IoT Hub Client...")
        if not IIoTEdgeGW is None:
            loop.run_until_complete(IIoTEdgeGW.shutdown())
        loop.close()


if __name__ == "__main__":
    main()

