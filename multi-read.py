import multiprocessing as mp
import serial
import json
import os.path
import re

class ConfigError(Exception):
    def __init__(self, error_message, incorrect_value):
        self.error_message = error_message
        self.incorrect_value = incorrect_value

def listener(): # Run as a separate process to read from the serial port
    i = ''
    while True: # Loop forever
        i = halfy.read(1) # Attempt to read one byte from the serial port
        q.put(i.decode()) # Decode from byte to character and add to queue

def signaler(message): # Send a command to the halfy and return the response
    output = []
    halfy.write(message) # Write the status command to the serial port
    p.join(.125) # Wait (1/8th of a second) for the response to accumulate in the queue
    
    # Translate the queue into a list
    while not q.empty():
        output.append(q.get())

    return ''.join(output) # Concatenate ('' delimited) the character list and return

def get_status(): # Read and print output statuses
    # Generate and excecute status comands
    status = {}
    for i in range(outputs):
        port = i + 1 # Switch to 1-indexed range
        try:
            status.update(get_single_status(port))
        except:
            raise
    return status

def get_single_status(port):
    if 1 <= port <= outputs:
        command_list = 'SL', str(level), 'O', str(port), 'T' # Make a list of strings
        command_string = "".join(command_list) # Concatenate into a single string
        command_bytes = command_string.encode('ascii') # Turn that string into ascii bytes
        halfy_response = signaler(command_bytes) # Signal the halfy
        response_list = re.split(r'[\(|\ \)]', halfy_response) # Break the response string into a list
        response_list.pop(0) # Remove the first entry (the command)
        response = [ int(x) for x in response_list if x != '' ][0] # Drop null entries, convert to int
        status = { port : response } # Compose dictionary
        return status
    else:
        raise ConfigError("port is not within active range:", port)

def parse_config():
    # Load values from config file
    with open('config.json') as json_data_file:
        data = json.load(json_data_file) # Make a dictionary from the config file data
    # Sanitize config file variables
    device_name = data['device_name'] # Serial port in use: string ['/dev/tty*']
    if not os.path.exists(device_name):
        raise ConfigError("device_name does not exist [/dev/tty*]:", device_name)
    inputs = int(data['inputs']) # Number of inputs in use: int [1-8]
    if not 1 <= inputs <= 8:
        raise ConfigError("inputs is out of the allowed range [1-8]:", inputs)
    outputs = int(data['outputs']) # Number of outputs in use: int [1-4]
    if not 1 <= outputs <= 4:
        raise ConfigError("outputs is out of the allowed range [1-4]:", outputs)
    level = int(data['level']) # Matrix level in use: int [1-2]
    if not 1 <= level <= 2:
        raise ConfigError("level is out of the allowed range [1-2]:", level)

    return device_name, inputs, outputs, level

if __name__ == '__main__':
    try:
        device_name, inputs, outputs, level = parse_config() # Parse and sanitize variables from config file
        halfy = serial.Serial(device_name) # Attempt to initialize serial port
    # Ensure that the config file is parsed properly and the serial port was initialized
    except serial.serialutil.SerialException as err:
        print("Serial Port Error:", err)
    except KeyError as err:
        print("Missing or mislabeled config file key:", err)
    except json.decoder.JSONDecodeError as err:
        print("Misformatted config file:", err)
    except FileNotFoundError as err:
        print("Missing or misnamed config file:", err)
    except ConfigError as err:
        print("Config file value error:", err.error_message, err.incorrect_value)
    else:
        q = mp.Queue() #Initialize queue to talk to listener process

        # Initialize and start listener as a separate process
        p = mp.Process(target=listener)
        p.start()
        try:
            out_dict = get_status()
            for key in range(outputs):
                print("Output", key + 1, "is connected to Input", out_dict[key + 1])
            print(get_single_status(2))
            print(get_single_status(12))
        except ConfigError as err:
            print("Status query error:", err.error_message, err.incorrect_value)

        # If process is still active
        if p.is_alive():
            print("Done.")

            # Terminate
            p.terminate()
            p.join()
