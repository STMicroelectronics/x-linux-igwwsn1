#!/usr/bin/python3
#
# File:    data_logger.py
# Author:  STMicroelectronics.
# Version: 1.0.0
# Date:    16-December-2024
# Brief:   Manage and enable logging feature
#
# Copyright (c) 2024 STMicroelectronics. All rights reserved.
#
# This software component is licensed by ST under ODE SOFTWARE LICENSE AGREEMENT
# SLA0094, the "License"; You may not use this file except in compliance with
# the License. You may obtain a copy of the License at:
# http://www.st.com/SLA0094

import json
import logging
import os

class DataLogger():

    TAG = "<tag>"
    OUTPUT_PATH_DEF  = "/app/log/"

    OUPUT_PREFIX_DEF         = "iiotgw_"
    OUPUT_LOG_NODE_DEF       = "node_" + TAG + ".log"
    OUPUT_LOG_NETWORK_DEF    = "network.log"
    OUPUT_LOG_APP_DEF        = "app.log"
    OUPUT_LOG_RAW_DEF        = "complete.log"
    OUPUT_LOG_SERIAL_DEF     = "serial_" + TAG + ".log"

    OUPUT_NET_DEL_FIELDS_DEF = ["Name", "Id", "Type", "UID", "Status", "Addr", "Parent", "RSSI"]

    _Config = {
        "Path"       : OUTPUT_PATH_DEF,
        "Prefix"     : OUPUT_PREFIX_DEF,
        "Filenames"  : {
            "LogNode"    : OUPUT_LOG_NODE_DEF,
            "LogNetwork" : OUPUT_LOG_NETWORK_DEF,
            "LogApp"     : OUPUT_LOG_APP_DEF,
            "LogRaw"     : OUPUT_LOG_RAW_DEF,
            "LogSerial"  : OUPUT_LOG_SERIAL_DEF
        },
        "NetDeliveryFields" : OUPUT_NET_DEL_FIELDS_DEF
        }
    
    _Enable = True

    #
    # Constructor.
    # @param config  
    # @param enable (optional)  
    #
    def __init__(self, config, enable = True):
        self._Enable = enable

        if config is None:
            # using default configuration
            return
        
        # copy available config
        for key in self._Config:
            if key != "Filenames" and key in config: self._Config[key] = config[key]

        if "Filenames" in config:
            for key in self._Config["Filenames"]:
                if key in config["Filenames"]: self._Config["Filenames"][key] = config["Filenames"][key]

    @property
    def Path(self):
        return self._Config["Path"]   

    @property
    def Prefix(self):
        return self._Config["Prefix"]   

    @property
    def NetDeliveryFields(self):
        return self._Config["NetDeliveryFields"]   
    #
    # get tge filename list according to the key.
    # @param key
    #
    def _get_filename(self, key):
        if not key in self._Config["Filenames"]:
            raise Exception("Invalid key " + key)

        return self.Prefix + self._Config["Filenames"][key]

    #
    # data output 
    # @param filename
    # @param obj  
    #
    def _data_output(self, filename, obj):
        if not self._Enable:
            return False
        
        f = None
        ret = False
        try:
            f = open(self.Path + filename, "w")
            logging.getLogger(__name__).info("File: '" + os.path.abspath(f.name) + "'")

            f.write(json.dumps(obj, indent=2))
            
            # adding empty lines
            f.write("\n\n\n")
            
            f.close()
            
            ret = True
        except Exception as ex:
            logging.getLogger(__name__).error("data output:" + str(ex))

        # try to close the file if open
        try:
            if not f is None: f.close()
        except:
            pass

        return ret

    #
    # generate all logs 
    # @param nodes
    # @param app  
    #
    def generate_all(self, nodes, app):
        if not self._Enable:
            return False
        
        self.raw(nodes)
        self.all_nodes(nodes)
        self.network(nodes)
        self.app(app)

    #
    # delete all logs 
    #
    def delete_all(self):
        for filename in os.listdir(self.Path):
            if ".log" in str(filename):
                file_path = os.path.join(self.Path, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    logging.getLogger(__name__).error("Failed to delete %s. Reason: %s" % (file_path, e))
    
    #
    # generate raw log
    # @param nodes
    #
    def raw(self, nodes):
        if not self._Enable:
            return False
        
        logging.getLogger(__name__).info("raw")
        return self._data_output(self._get_filename("LogRaw"), nodes)
    
    #
    # generate node log
    # @param node
    #
    def node(self, node):
        if not self._Enable:
            return False
        
        if node is None:
            logging.getLogger(__name__).error("output node: null")
            return False
        
        filename = ""
        try:
            #create the file name replacing the id for the placeholder TAG
            filename = self._get_filename("LogNode")
            filename = filename.replace(self.TAG, str(node["Id"]))
        except Exception as ex:
            logging.getLogger(__name__).error("output node: " + str(ex))
            return False
        
        logging.getLogger(__name__).info("output node", node["Name"], node["Id"])
        return self._data_output(filename, node)

    #
    # generate all nodes log
    # @param nodes
    #
    def all_nodes(self, nodes):
        if not self._Enable:
            return False
        
        logging.getLogger(__name__).info("output all nodes")
        for uid in nodes:
            self.node(nodes[uid])

    #
    # generate network log
    # @param nodes
    #
    def network(self, nodes):
        if not self._Enable:
            return False
        
        network = []
        try:
            #create a filtered network object starting from the configuration
            for uid in nodes:
                node = nodes[uid]
                p = dict()
                for field in self.NetDeliveryFields:
                    #check if a field is available in a node
                    if field in node:
                        p[field] = node[field]
                network.append(p)
        except Exception as ex:
            logging.getLogger(__name__).error("output network: " + str(ex))
            return False

        logging.getLogger(__name__).info("network")
        return self._data_output(self._get_filename("LogNetwork"), network)

    #
    # generate app log
    # @param app
    #
    def app(self, app):
        if not self._Enable:
            return False
        
        logging.getLogger(__name__).info("app")
        return self._data_output(self._get_filename("LogApp"), app)

    #
    # append the serial stream to the corresponding file
    # @param device_port
    # @param text
    #
    def serial_stream_log(self, device_port, text):
        if not self._Enable:
            return False
        
        #in different way, this function append data from the serial for each port in a different file
        f = None
        try:
            print("log serial")
            filename = self._get_filename("LogSerial")
            filename = filename.replace(self.TAG, device_port)
            f = open(self.Path + filename,"a")
            f.write(text)
            f.close()
            return True
        except Exception as ex:
            print("log_serial EX:", str(ex))
            if not f is None: f.close()
            return False
