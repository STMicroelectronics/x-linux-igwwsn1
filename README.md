# X-LINUX-IGWWSN1 V1.0.0

![latest tag](https://img.shields.io/github/v/tag/STMicroelectronics/x-linux-igwwsn1.svg?color=brightgreen)

## Introduction
**X-LINUX-IGWWSN1** is an industrial edge gateway software package for wireless sensor networks (WSN). It allows you to connect sensor nodes, such as the **STEVAL-PROTEUS1** kit, to **Microsoft Azure® IoT Central** cloud, transmit
preprocessed sensor data, and receive commands.
Detailed User Guide _"Industrial WSN edge gateway software expansion package"_ can be foudn here  : https://www.st.com/resource/en/user_manual/


## Description
[X-LINUX-IGWWSN1](https://www.st.com/en/embedded-software/x-linux-igwwsn1.html) is an industrial edge gateway software package for wireless
sensor networks (WSN). It allows you to connect sensor nodes, such as the [STEVAL-PROTEUS1](https://www.st.com/en/evaluation-tools/steval-proteus1.html) kit, transmit preprocessed data to Microsoft Azure® IoT Central cloud and receive commands.

It fully supports **Microsoft Azure®** device management primitives and includes a complete Industrial IoT Edge Gateway to route data from a ZigBee Mesh Network to the Cloud preprocessing real-time data and taking decision on-premise.
This software can be used to accelerate the development of sensor-to-cloud applications for a broad range of industrial use cases.
[X-LINUX-IGWWSN1](https://www.st.com/en/embedded-software/x-linux-igwwsn1.html) includes dashboards to retrieve meaningful sensor data on **Microsoft Azure®**.

## Package Structure:

```
$Root
+---asset
¦    ¦   IIoTEdgeGW_edgeIIoTGW_module.json
¦    ¦   IIoTEdgeGW_edgeSerial_module.json
¦    ¦   NodeDevice_module.json
¦      
+---code
¦    +---template_config
¦    ¦        |   config_app.json
¦    ¦        |   config_net.json
¦    +---modules
¦    ¦   +---edgeIIoTGW
¦    ¦        |   data_logger.py
¦    ¦        |   Dockerfile.arm32v7
¦    ¦        |   gw.py
¦    ¦        |   inference.py
¦    ¦        |   main.py
¦    ¦        |   module.json
¦    ¦        |   requirements.txt
¦    ¦   .env
¦    ¦   deployment.template.json
¦   CODE_OF_CONDUCT.md
¦   CONTRIBUTING.md
¦   Package_License.md
¦   README.md
¦   RELEASE_NOTE.md
¦   SECURITY.md

```   

## Getting Started
For more information refer to the **[Quick Start Guide](https://www.st.com/en/embedded-software/x-linux-igwwsn1.html)**

### Requirements
#### Hardware
- [STM32MP257F-EV1](https://www.st.com/en/evaluation-tools/stm32mp257f-ev1.html)
- Micro SD 32GB 
- 5 x [STEVAL-PROTEUS1](https://www.st.com/en/evaluation-tools/steval-proteus1.html) (at least 2 boards)
- [STLINK-V3MINIE](https://www.st.com/en/development-tools/stlink-v3minie.html) or [STLINK-V3SET](https://www.st.com/en/development-tools/stlink-v3set.html)
- Power supply classic or USB type-C 5V@3A

#### Software Setup:
- [STM32CubeProgrammer v.2.18 or higher](https://www.st.com/en/development-tools/stm32cubeprog.html)
- [OSTL v 5.1](https://www.st.com/en/embedded-software/stm32-mpu-openstlinux-distribution.html)
- [X-LINUX-AZURE v5.1.0](https://www.st.com/en/embedded-software/x-linux-azure.html)
- [STSW-PROTEUS v1.1.1](https://www.st.com/en/embedded-software/stsw-proteus.html) 

#### Misc
- A Linux® PC running _Ubuntu® 20.04_ or _22.04_ is recommended. Developers can follow the link for details: [PC prerequisites](https://wiki.st.com/stm32mpu/wiki/PC_prerequisites)
- Internet connection by ethernet cable
- **Microsoft Azure IoT Central account**

#### Board setup
Legend:
- STM32MPU Board : STM32MPU based board (i.e. STM32MP257F-EV1)
- Host PC : Linux PC
- Node : STEVAL-PROTEUS1 with STSW-PROTEUS v1.1.1 with Zigbee stack

**See official documentation for more information**
1) Put the Micro SD in the dedicated slot of the STM32MPU (Board)
2) Power on the board with a standard power supply 5V@3A with the jack (5V_3A connector) or Type-C (USB_PWR STLINK connector)
3) OSTL v5.1 Installation on MicroSD Guide: [STM32MP257x-EV1 - stm32mpu
](https://wiki.st.com/stm32mpu/wiki/Getting_started/STM32MP2_boards/STM32MP257x-EV1)
4) [X-LINUX-AZURE](https://www.st.com/en/embedded-software/x-linux-azure.html) Installation Guide: [X-LINUX-AZURE expansion package - stm32mpu](https://wiki.st.com/stm32mpu/wiki/X-LINUX-AZURE_expansion_package)

#### Nodes setup (Coordinator, Router and End device)
1) Install the STM32CubeProgrammer on Host PC
2) Download the [STSW-PROTEUS v1.1.1](https://www.st.com/en/embedded-software/stsw-proteus.html) package
3) Unzip the downloaded file in a temporary folder
4) Connect the STLINK-V3MINIE to the Host PC
5) Open the STM32CubeProgrammer 

#### For each Node (STEVAL-PROTEUS1)

Refer to official documentation for more details [UM3045 Getting started with STSW-PROTEUS1](https://www.st.com/resource/en/user_manual/um3045-getting-started-with-the-stswproteus-software-package-for-the-stevalproteus1-industrial-sensor-node-kit-stmicroelectronics.pdf) 3.2 Zigbee-based application section
1) Plug the STLINK-V3MINIE to the Node (refer to the official documentation)
2) Upload the Full-features Zigbee for Coordinator and router and the Reduced features stack v1.19.0 (if not already loaded)
3) Upload the target firmware: 1 Coordinator, 1 Router, 3 End-devices

### Configuration
#### Microsoft IoT Central
- Load the Manifest and the Device Templates available in the asset 
folder:
    1) _IoTC Connect->Edge manifests_ menu create a new manifest called _STIIoTEdgeGW_Manifest_ and then select the file _asset/STIIoTEdgeGW_Manifest_deployment.arm32v7.json_
    2) _IoTC Connect->Device templates_ create a new template called _STIIoTEdgeGW_ and import the modules: _STIIoTEdgeGW_DeviceTemplate_edgeIIoTGW_module.json_ and _STIIoTEdgeGW_DeviceTemplate_edgeSerial_module.json_
    **Note**: select _Azure IoT Edge_ template and then **check** _This is a gateway device_ 
    3) _IoTC Connect->Device templates_ create a new template called _STIIoTNodeDevice_ and import the module: STIIoTEndNode_DeviceTemplate_module.json
    **Note**: select _IoT device_ template and then **uncheck** _This is a gateway device_
- Open _IoTC Connect->Devices_ 
- Create one edge device (for the STM32MPU Board) and select the _STIIoTEdgeGW_Manifest_ manifest and _STIIoTEdgeGW_ device template **Note**: copy the data available in the connect button data (ID scope, Device ID, and Primary key)
- Create 4 devices (no device for the coordinator) selecting _STIIoTNodeDevice_ as device template and copy the connect button data (ID scope, Device ID, and Primary key) to update the config_net.json file
(follow the official dcoumentation for more details)

#### Configure STM32MPU Board
- Configure _/etc/aziot/config.toml_ file and re-apply the configuration with the command: _iotedge config apply_
- Configure the _config_net.json_ json file available in the _/var/lib/iiotedgegw/config/_ folder  config_app.json and 

#### Apply the configuration in the STM32MPU Board
- exec: iotedge config apply

Note: 
- The Node UID is the last 4 bytes of the MCU id.


