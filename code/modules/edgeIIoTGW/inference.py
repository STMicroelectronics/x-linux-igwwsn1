#!/usr/bin/python3
#
# File:    inference.py
# Author:  STMicroelectronics.
# Version: 1.0.0
# Date:    16-December-2024
# Brief:   Wrapper to manage the identity translation
#
# Copyright (c) 2024 STMicroelectronics. All rights reserved.
#
# This software component is licensed by ST under ODE SOFTWARE LICENSE AGREEMENT
# SLA0094, the "License"; You may not use this file except in compliance with
# the License. You may obtain a copy of the License at:
# http://www.st.com/SLA0094
#

from collections import OrderedDict
import logging
import time
import uuid
import os

#azure modules
from azure.iot.device import Message

class Inference():

    #
    # Constructor.
    #
    def __init__(self, module_client):
        self._module_client = module_client

    #
    # Set method parameters.
    #
    def _set_method_parameters(self, method_name, payload):

        return {
            "methodName": method_name,
            "payload": payload,
            "connectTimeoutInSeconds": 60,
            "responseTimeoutInSeconds": 60
        }

    #
    # Check method invocation response.
    #
    def _check_response(self, response, value_to_return = None):

        try:
            #self._sdk_logger.info("Method response: {}".format(response))
            if not response:
                return None
            if response["status"] != 200 and not value_to_return:
                raise Exception(response["payload"]["error"])
            if value_to_return:
                if response["payload"]:
                    if value_to_return in response["payload"]:
                        return response["payload"][value_to_return]
                return None
        
        except Exception as e:
            raise e

    #
    # Create message.
    #
    def _create_message(self, device_physical_id, message):

        # Creating PnP message.
        new_message = Message(message)
        new_message.id = uuid.uuid4()
        new_message.content_encoding = "utf-8"
        new_message.content_type = "application/json"
        
        # Adding device identifier (this is required by the Identity Translation Module to translate identity).
        new_message.custom_properties["device_physical_id"] = device_physical_id

        return new_message

    #
    # Set inference mode for a specific proteus.
    #
    # @param node (wih all parameter).
    #        [{"id_scope":,"device_id":, "primary_key":, "device_physical_id", "device_template_id":}]
    #
    async def node_provisioning(self, node):
        try:
            activity = "Provisioning node device ... " + node["device_id"]
            module_id = "edgeIdentityTranslation"
            method_name = "provision_leaf_device"
            logging.getLogger(__name__).info(activity, module_id, method_name)

            # Keeping the first device by default.
            payload = dict()
            payload["id_scope"] = node["id_scope"]
            payload["device_id"] = node["device_id"]
            payload["primary_key"] = node["primary_key"]
            payload["device_template_id"] = node["device_template_id"]
            payload["device_physical_id"] = node["device_physical_id"]
            payload["protocol"] = 0

            device_id = os.environ["IOTEDGE_DEVICEID"]

            response = await self._module_client.invoke_method(
                method_params = self._set_method_parameters(method_name, payload),
                device_id = os.environ["IOTEDGE_DEVICEID"],
                module_id = module_id
            )

            self._check_response(response)
        except Exception as e:
            raise e
        
    async def set_nodes(self, nodes):
        ex = None
        for node in nodes:
            try:
                self.node_provisioning(node)
            except Exception as ex_local:
                if ex is None:
                    ex = ex_local

        #notify only the first exception
        if not ex is None:
            raise ex

    async def node_send_message(self, node_uuid, message, output_channel):
        try:
            _msg = self._create_message(node_uuid, message)
            # logging.getLogger(__name__).info("\n\n", _msg, "\n\n")
            await self._module_client.send_message_to_output(_msg, output_channel)
            return _msg

        except Exception as e:
            raise e
 