#!/usr/bin/python3
#
# File:    gw.py
# Author:  STMicroelectronics.
# Version: 1.0.0
# Date:    16-December-2024
# Brief:   Main GW application
#
# Copyright (c) 2024 STMicroelectronics. All rights reserved.
#
# This software component is licensed by ST under ODE SOFTWARE LICENSE AGREEMENT
# SLA0094, the "License"; You may not use this file except in compliance with
# the License. You may obtain a copy of the License at:
# http://www.st.com/SLA0094
#

# common modules
import json
import logging
import os
import time
import uuid
import shutil
from os.path import exists

# application modules
import inference
import data_logger

# azure modules
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import MethodResponse, Message
from azure.iot.device.aio import ProvisioningDeviceClient

#local default configuration
APP_MODULE_NAME = "iiotedgegw"
APP_MODULE_VER  = "1.0.0"

CHANNEL_IOTHUB  = "iothub_output"               # out channel to the cloud
CHANNEL_IDNTRX  = "identitytranslation_output"  # out channel through the identity translation module
MAX_RETRY       = 3                             # number of retry for
SERIAL_GENERIC  = "generic"                     # key dictionary for not specified input serial stream

CONFIG_APP_FILE = "config_app.json"
CONFIG_NET_FILE = "config_net.json"

CONFIG_FOLDER = "/app/config/"
CONFIG_TEMPLATE_FOLDER = "/app/template_config/"

class GWApp():
    _Nodes = {}                                 # list of nodes connected to the gateway

    _CoordinatorInfo = {
        "Firmware": {
            "Name": "-",
            "Version": "-",
            "Date": "-",
        },
        "Clock": { 
            "Date":"-",
            "Time":"-"
            }
    }

    _DataSerialStreams = {SERIAL_GENERIC: ""}   # dictionary for serial stream, the first one is the default stream accumulator
    _Inference = None                           # inference object to manage the identity translation
    _DataLogger = None                          # data logger

    _Client = None                              # azure client, in case of None we are in local mode (no cloud connection)

    _Config = {
        "SerialPort": {},                       # serial port configuration (i.e. device, baudrate, ...)
        "DataLogger": {},                       # data logger configuration
        "Net": {
            "DefaultProvisioning": {},          # default provisioning information
            "EdgeGateway": {},                  # edge gateway
            "Nodes": {},                        # node mappint
            "Map": {},                          # quickly map to retrive the uid in a short string
        }
    }

    _Logger = logging.getLogger(__name__)

    #
    # Constructor.
    # @param client  
    #
    def __init__(self, client):
        self._Logger.setLevel(logging.DEBUG)
        self._Logger.info("GW started")
        self.check_conf()
        self.load_conf()

        self._Client = client
        self._serial_devices = []
        if not client is None:
            self._Inference = inference.Inference(client)
        self._DataLogger = data_logger.DataLogger(self._Config["DataLogger"]["Config"], self._Config["DataLogger"]["Enable"])
        self._DataLogger.generate_all(self._Nodes, self.app)

    @property
    def client(self):
        return self._Client
    
    @property
    def isLocalMode(self):
        return self._Client is None

    @property
    def app(self):
        _app = {
            "CoordinatorInfo": self._CoordinatorInfo,
            "DeviceNumber": len(self._Nodes)
        }
        return _app

    #
    # get the node configuration with the uid.
    # @param uid  
    #
    def get_node_config(self, uid):
        config = None
        if uid == "":
            return None
        
        try:
            #search the current uid into the config nodes
            if config is None and uid in self._Config["Net"]["Nodes"]:
                config = self._Config["Net"]["Nodes"][uid]
                    
            #find the first free config node
            #AR 13/12
            if config is None:
                for uid_temp in self._Config["Net"]["Nodes"]:
                    if config == None and uid_temp.find("NODE") != -1:
                        #associate the configuration to the uid and remove the old
                        self._Logger.info("Config update uid:" + uid + " temp_uid:" + uid_temp)
                        self._Config["Net"]["Nodes"][uid] = self._Config["Net"]["Nodes"][uid_temp]
                        self._Config["Net"]["Nodes"].pop(uid_temp)
                        config = self._Config["Net"]["Nodes"][uid]

        except:
            pass
        return config
    #
    # Update and/or generate the name in a node trying to retrieve information in the configuration.
    # @param node  
    #
    def _update_field_name(self, node):
        if node is None or not "UID" in node:
            return
        
        uid = node["UID"] 
        try:
            #retrieve the name from the configuration
            config = self.get_node_config(uid)
            node["Name"] = config["Name"]
        except:
            #if the node is not present in the configuration generate a standard name
            node["Name"] = "Node" + node["UID"][-2:]

    #
    # Check if the template files exists and in case copy on the binded folder app_config->iiotedgegw_config
    #
    def check_conf(self):
        try:
            f_cnf = CONFIG_FOLDER + CONFIG_APP_FILE
            f_tmp = CONFIG_TEMPLATE_FOLDER + CONFIG_APP_FILE
            print("App configuration file ... " + f_cnf + " " + f_tmp)
            self._Logger.info("App configuration file ... " + f_cnf + " " + f_tmp)
            file_exists = exists(f_cnf)

            #if not exist copy the config file
            if not file_exists:
                shutil.copy(f_tmp, f_cnf)

        except Exception as ex:
            self._Logger.error("Configuration App check failed: " + str(ex))
            pass

        try:
            f_cnf = CONFIG_FOLDER + CONFIG_NET_FILE
            f_tmp = CONFIG_TEMPLATE_FOLDER + CONFIG_NET_FILE
            print("Net configuration file ... " + f_cnf + " " + f_tmp)
            self._Logger.info("Net configuration file ... " + f_cnf + " " + f_tmp)
            file_exists = exists(f_cnf)

            #if not exist copy the config file
            if not file_exists:
                shutil.copy(f_tmp, f_cnf)

        except Exception as ex:
            self._Logger.error("Configuration Net check failed: " + str(ex))
            pass    

    #
    # Load the configuration from config json files
    #
    def load_conf(self):
        try:
            self._Logger.info("Loading App configuration ... ")
            with open(CONFIG_FOLDER + CONFIG_APP_FILE) as json_conf_app_file:
                json_conf_app_datafile = json.load(json_conf_app_file)
                if "DataLogger" in json_conf_app_datafile: self._Config["DataLogger"] = json_conf_app_datafile["DataLogger"]
                if "SerialPort" in json_conf_app_datafile: self._Config["SerialPort"] = json_conf_app_datafile["SerialPort"]

            self._Logger.info("Configuration App loaded")
        except Exception as ex:
            self._Logger.error("Configuration App load failed: " + str(ex))
            pass

        try:
            self._Logger.info("Loading Network configuration ... ")
            with open(CONFIG_FOLDER + CONFIG_NET_FILE) as json_conf_net_file:
                json_conf_net_datafile = json.load(json_conf_net_file)
                self._Config["Net"] = json_conf_net_datafile

            self._Logger.info("Configuration Network loaded")
        except Exception as ex:
            self._Logger.error("Configuration Network load failed: " + str(ex))
            pass
    #
    # start the Gateway operation
    #
    def start(self):
        self._Logger.info("start")

    #
    # run the Gateway task
    #
    def run(self):
        self._Logger.info("live " + str(len(self._Nodes)))
        #self._DataLogger.app(self._Config["Net"]["Nodes"])
        self._DataLogger.app(self.app)
        self._DataLogger.raw(self._Nodes)

    #
    # stop the Gateway operation
    #
    def stop(self):
        self._Logger.info("stop")

    #
    # Retrieve a node in the list with the uid.
    # @param uid  
    #
    def find_node_by_uid(self, uid):
        if uid in self._Nodes:
            return self._Nodes[uid]
        return None

    #
    # Retrieve a node in the list with the address.
    # @param address  
    #
    def find_node_by_address(self, address):
        for uid in self._Nodes:
            if self._Nodes[uid]["Address"] == address:
                return self._Nodes[uid]
        return None

    #
    # Create a node starting to a data packet (missing type, parent and network information).
    # @param uid  
    #
    def create_empty_node(self, uid):
        try:
            node = {
                "Name": "",
                "Id": -1, 
                "Type": -1,
                "UID": uid, 
                "Epoch": -1, 
                "State": -1, 
                "Address": "-", 
                "Parent":"-", 
                "RSSI": 0, 
                "Temperature": 0, 
                "CbM": -1, 
                "Battery" : {"Voltage":0, "Level": 0, "State": -1},
                "Provisioned": 0
            }

            return node
        except Exception as ex:
            self._Logger.error("Create empty node: " + str(ex))
            return None
    #
    # Create a node starting to a data packet and return the node.
    # @param uid  
    # @param data  
    # @param id_num  
    # @param epoch (optional)  
    #
    def create_node_with_data_packet(self, uid, data, id_num, epoch = -1):
        try:
            #generate a node with a received data packet
            node = self.create_empty_node(uid)

            # copy the known data 
            node["Id"] = id_num
            node["Epoch"] = epoch
            node["Address"] = data["ZbAddr"]

            if "ZbPrntAddr" in data:
                node["Parent"] = data["ZbPrntAddr"]

            # data part
            if "Temperature" in data:
                node["Temperature"] = float(data["Temperature"]) / 10

            if "CbM" in data:
                node["CbM"] = int(data["CbM"])

            if "Battery" in data:
                node["Battery"] = data["Battery"]

            self._update_field_name(node)
            return node

        except Exception as ex:
            self._Logger.error("Create node with data packet: " + str(ex))
            return None
        
    #
    # Create a node starting to a network packet and return the node.
    # @param uid  
    # @param data  
    # @param id_num  
    # @param epoch (optional)  
    #
    def create_node_with_network_packet(self, uid, data, id_num, epoch = -1):
        try:
            #generate a standard node with a received network packet
            node = self.create_empty_node(uid)

            # copy the known data 
            node["Id"] = id_num
            node["Epoch"] = epoch
            node["Address"] = data["ZbAddr"]
            
            if "ZbPrntAddr" in data:
                node["Parent"] = data["ZbPrntAddr"]

            if "ZbTyp" in data:
                node["Type"] = data["ZbTyp"]

            if "ZbSts" in data:
                node["State"] = data["ZbSts"]

            if "RSSI" in data:
                node["RSSI"] = data["RSSI"]

            self._update_field_name(node)

            return node
        
        except Exception as ex:
            self._Logger.error("Create node with network packet: " + str(ex))
            return None
        
    #
    # Update a node with a data packet and return the updated node
    # @param node  
    # @param data  
    # @param epoch (optional)  
    #
    def update_node_with_data_packet(self, node, data, epoch = -1):
        modify_fields = []
        try:
            if "UID" in data and node["UID"] != data["UID"]:
                raise Exception("UID not match")

            # adding default fields (always available)
            modify_fields.append("UID")
            modify_fields.append("Epoch")
            modify_fields.append("Address")
            modify_fields.append("Parent")

            # copy the known data 
            node["Epoch"] = epoch

            # check the current and saved address
            if "ZbAddr" in data:
                new_addr = data["ZbAddr"].upper()
                if node["Address"] != new_addr:
                    # in case of a change of address, reset the parent too
                    node["Address"] = new_addr
                    node["Parent"] = "-"

            if "ZbPrntAddr" in data:
                node["Parent"] = data["ZbPrntAddr"]

            # data part
            if "Temperature" in data:
                modify_fields.append("Temperature")
                node["Temperature"] = float(data["Temperature"]) / 10

            if "CbM" in data:
                modify_fields.append("CbM")
                node["CbM"] = int(data["CbM"])

            if "Battery" in data:
                modify_fields.append("Battery")
                node["Battery"] = data["Battery"]

            # create the object with the updated data
            node_update = {}
            for k in modify_fields: 
                node_update[k] = node[k]

            return node_update
        except Exception as ex:
            self._Logger.error("update node with data packet: " + str(ex))
            return None

    #
    # Update a node with a network packet and return the updated node
    # @param node  
    # @param data  
    # @param epoch (optional)  
    #
    def update_node_with_network_packet(self, node, data, epoch = -1):
        modify_fields = []

        try:
            if "UID" in data and node["UID"] != data["UID"]:
                raise Exception("UID not match")

            # include the following  fields as default
            modify_fields.append("UID")
            modify_fields.append("Epoch")
            modify_fields.append("Address")
            modify_fields.append("Parent")

            # copy the known data 
            node["Epoch"] = epoch

            # check the current and saved address
            if "ZbAddr" in data:
                new_addr = data["ZbAddr"].upper()
                if node["Address"] != new_addr:
                    # in case of a change of address, reset the parent
                    node["Address"] = new_addr
                    node["Parent"] = "-"

            if "ZbPrntAddr" in data:
                node["Parent"] = data["ZbPrntAddr"]

            if "ZbTyp" in data:
                modify_fields.append("Type")
                node["Type"] = data["ZbTyp"]

            if "ZbSts" in data:
                modify_fields.append("State")
                node["State"] = data["ZbSts"]

            if "RSSI" in data:
                modify_fields.append("RSSI")
                node["RSSI"] = data["RSSI"]

            # create an object only with the updated data
            node_update = {}
            for k in modify_fields: 
                node_update[k] = node[k]

            return node_update

        except Exception as ex:
            self._Logger.error("update node with network packet: " + str(ex))
            return None

#region Decode Packets
    #WRN da sistemaree
    #
    # Generate a str info app.
    #    
    def app_info_str(self):
        mystr = ""
        try:
            app_info = {
                # "Firmware" : {
                #     "Name": str(app["Firmware"]["Name"]),
                #     "Version": str(app["Firmware"]["Version"]),
                #     "Date": str(app["Firmware"]["Date"])[:10]
                # },
                # "DateTime" : {
                #     "Date": str(app["DateTime"]["Date"])[:10],
                #     "Time": str(app["DateTime"]["Time"])[:8],
                # }
            }
            mystr = str(app_info).replace("'","\"")
        except:
            pass
        return mystr

    #
    # Retrieve the node with uid and in case the address
    # @param uid  
    # @param addr  
    #
    def get_node(self, uid, addr):
        node = None

        #search the node by uid
        if uid != "":
            node = self.find_node_by_uid(uid)

        #if not found search the node by address
        if node is None:
            node = self.find_node_by_address(addr)

        return node

    #
    # Perform a provisioning
    # @param node  
    #        
    async def do_provisioning(self, node):
        if node is None:
            raise Exception("Invalid node parameter")
        
        try:
            if node["Provisioned"] <= 0:
                # get the configuration node (refere to json config file)
                node_config = self.get_node_config(node["UID"])

                # performing provisioning
                await self._Inference.node_provisioning(node_config["Provisioning"])
                node["Provisioned"] = 1

        except Exception as ex:
            self._Logger.error("provisioning error: " + str(ex))
            node["Provisioned"] = -1

    #
    # Send a message node to the cloud
    # @param node  
    # @param message  
    #
    async def send_msg_to_node(self, node, message):
        if node is None:
            raise Exception("Invalid node parameter")

        if message == "":
            return 

        try:
            # get the configuration node (refere to json config file)
            node_config = self.get_node_config(node["UID"])
            if node_config is None:
                return

            #prepare payload
            device_message = message
            device_physical_id = node_config["Provisioning"]["device_physical_id"]
            out_ch = CHANNEL_IDNTRX

            self._Logger.info("Sending data... message: '" + str(device_message) + "' output: " + out_ch)
            await self._Inference.node_send_message(device_physical_id, device_message, out_ch)
        except Exception as ex:
            self._Logger.error("send_msg_to_node error: " + str(ex))
            pass

    # check the validity of a UID
    def check_uid(self, uid):
        if uid == "": return False
        if len(uid) != 8: return False
        return True
        
#endregion

    #
    # Decode a line containing a completed json
    # @param json_line  
    #
    async def data_decode(self, json_line):
        self._Logger.info("Decode line '" + (json_line) + "'")

        try:
            # decode the json
            json_obj = json.loads(json_line)

            # retrieve the 
            epoch = 0
            try:
                if "Epoch" in json_obj:
                    epoch = int(json_obj["Epoch"])
            except:
                epoch = -1

            if "DevSts" in json_obj:
                payload = json_obj["DevSts"]
                await self.manage_node_packet(payload, epoch)

            if "ZbNet" in json_obj:
                payload = json_obj["ZbNet"]
                await self.manage_network_packet(payload, epoch)

            if "DevFw" in json_obj:
                payload = json_obj["DevFw"]
                await self.manage_sys_fw_packet(payload, epoch)

            if "DevRtc" in json_obj:
                payload = json_obj["DevRtc"]
                await self.manage_sys_rtc_packet(payload, epoch)

        except json.JSONDecodeError as json_ex:
            self._Logger.error("Data decode json error: " + str(json_ex))
            
    #
    # decode and manage node packet
    # @param data  
    # @param epoch (optional) 
    #
    async def manage_node_packet(self, data, epoch = -1):
        self._Logger.info("Node data decoding")
        try:
            node_to_cloud = None
            node = None
            uid = ""
            addr = ""

            # collect node identification, priority: UID, ZbAddr
            if "UID" in data:
                uid = data["UID"]

            if "ZbAddr" in data:
                addr = data["ZbAddr"]

            node = self.get_node(uid, addr)
            if not node is None: uid = node["UID"]

            # check uid validity
            if not self.check_uid(uid):
                raise Exception("Invalid uid found for the node data package", uid)

            if node is None: 
                #we have a new node to add to the list
                node = self.create_node_with_data_packet(uid, data, len(self._Nodes), epoch)
                if not node is None:
                    self._Nodes.update({uid: node})
                    self._DataLogger.log_network(self._Nodes)
                    node_to_cloud = node
            else:
                #known node, update data
                node_to_cloud = self.update_node_with_data_packet(node, data, epoch)

            if not node is None: 
                self._DataLogger.node(node)

                self._Logger.info("Node info uid:'" + uid + "' address:'" + node["Address"] + "' name:'" + node["Name"] + "' out:'" + str(node_to_cloud)+"'")
                await self.do_provisioning(node)

                #send only the update
                if not node_to_cloud is None and node["Provisioned"] == 1:
                    await self.send_msg_to_node(node, str(node_to_cloud))
                    
        except Exception as ex:
            self._Logger.error("manage data packet: " + str(ex))

    #
    # decode and manage network packet
    # @param data  
    # @param epoch (optional) 
    #
    async def manage_network_packet(self, data, epoch = -1):
        self._Logger.info("Network data decoding")
        try:
            #get list devices
            data_nodes = data["Devices"]
            for data_node in data_nodes:
                node_to_cloud = None
                node = None
                uid = ""
                addr = ""

                # collect node identification, priority: UID, ZbAddr
                if "UID" in data_node:
                    uid = data_node["UID"]

                if "ZbAddr" in data_node:
                    addr = data_node["ZbAddr"]

                node = self.get_node(uid, addr)
                if not node is None: uid = node["UID"]

                # check uid validity
                if not self.check_uid(uid):
                    raise Exception("Invalid uid found for the node data package", uid)

                if node is None: 
                    # new node
                    node = self.create_node_with_network_packet(uid, data_node, len(self._Nodes), epoch)
                    if not node is None:
                        self._Nodes.update({uid: node})
                        node_to_cloud = node
                else:
                    # known node, update data
                    node_to_cloud = self.update_node_with_network_packet(node, data_node, epoch)

                if not node is None: 
                    self._DataLogger.node(node)

                    self._Logger.info("Node info uid:'" + uid + "' address:'" + node["Address"] + "' name:'" + node["Name"] + "' out:'" + str(node_to_cloud)+"'")
                    await self.do_provisioning(node)

                    #send only the update
                    if not node_to_cloud is None and node["Provisioned"] == 1:
                        await self.send_msg_to_node(node, str(node_to_cloud))

            self._DataLogger.network(self._Nodes)
            self._DataLogger.all_nodes(self._Nodes)

        except Exception as ex:
            self._Logger.error("manage network packet: " + str(ex))            
            pass

    #
    # decode and manage system firmware packet
    # @param data  
    # @param epoch (optional) 
    #
    async def manage_sys_fw_packet(self, data, epoch = -1):
        self._Logger.info("Firmware")
        self._Logger.warning("no implementation")

    #
    # decode and manage system RTC packet
    # @param data  
    # @param epoch (optional) 
    #
    async def manage_sys_rtc_packet(self, data, epoch = -1):
        self._Logger.info("RTC")
        self._Logger.warning("no implementation")

#region Handlers
    #
    # termination handler called by the system
    #
    def termination_handler(self):
        self._Logger.info(APP_MODULE_NAME + " v" + APP_MODULE_VER + " terminated")

    #
    # handler of a received message
    # @param message incoming message from the serial port
    #
    async def receive_message_handler(self, message):
        try:
            # retrieve the stream serial port
            serial_port_id = SERIAL_GENERIC
            if "serial_port" in message.custom_properties:
                serial_port_id = message.custom_properties["serial_port"]
            else:
                if "device_physical_id" in message.custom_properties:
                    serial_port_id = message.custom_properties["device_physical_id"]


            # check if the stream exist
            if not serial_port_id in self._DataSerialStreams:
                #create the stream data for the serial port id
                self._DataSerialStreams[serial_port_id] = ""

            # select the default output
            out_ch = CHANNEL_IOTHUB

            partial_str = message.data.decode('utf-8')
            completed = partial_str[-1:] == "\n"
            self._DataLogger.serial_stream_log(serial_port_id, ">>" + partial_str + "<< ")
            self._Logger.info("incoming message on port '" + serial_port_id + "' -  completed " + str(completed) + " '" +  partial_str[-1:] + "'")

            # accumulate the received data
            self._DataSerialStreams[serial_port_id] += partial_str

            # convert the stream in a array respect the \n key
            stream_lines = self._DataSerialStreams[serial_port_id].splitlines()
            
            # remove the accumulated stream data
            self._DataSerialStreams[serial_port_id] = ""

            # decode each line
            for stream_line in stream_lines:
                self._Logger.info("stream: '" + stream_line + "'")
                if completed:
                    # try to decode in case of error discard the line
                    try:
                        await self.data_decode(str(stream_line))
                    except:
                        pass
                else:
                    self._DataSerialStreams[serial_port_id] = stream_line
                    break

        except Exception as ex:
            self._Logger.error("received serial stream: " + str(ex))
            pass
    #
    # handler of a received message
    # @param method_request incoming method_request from the iot hub
    #
    async def method_request_received_handler(self, method_request):
            self._Logger.error("method_request_received_handler not implemented: Name:" + method_request.name + " Payload:" + method_request.payload + " method_request:" + method_request)

#endregion
