# FLEET Client
The core FLEET client program is [app.py](optee/out-br/target/root/app.py).
## Setup
### Step 1
Follow the [DarkneTZ tutorial](https://github.com/HenryHu2000/PPFL/blob/main/client_side_trustzone/README.md) to set up OP-TEE and DarkneTZ. 

You can reference [build-hikey.sh](build-hikey.sh) and [build-rpi.sh](build-rpi.sh) for building OP-TEE.

You can reference [flash-hikey.sh](flash-hikey.sh) and [flash-hikey.sh](flash-hikey.sh) for flashing the devices.

### Step 2
To set up the FLEET client, copy the content in the [optee](optee) folder to the corresponding location in the directory you built in Step 1. Rebuild OP-TEE.

### Step 3
Connect the device to your computer using a serial port. Boot up the device. Use `root` as the password to log in. Run the corresponding setup script.

### Step 4
Execute `python app.py`. Once the diagnosis finishes, log in using `user` as the default username and password. Edit `config.ini` to configure the Kafka server. Rerun `python app.py`.
