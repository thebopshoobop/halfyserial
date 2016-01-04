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
    p.join(.0625) # Wait (1/16th of a second) for the response to accumulate in the queue
    
    # Translate the queue into a list
    while not q.empty():
        output.append(q.get())

    return ''.join(output) # Concatenate ('' delimited) the character list and return

def get_status(): # Read and print output statuses
    status = {} # Dictionary of statuses
    for output_port in sorted(config['outputs']): # Iterate over the outputs
        try:
            status.update(get_single_status(output_port)) # Attempt to add a status entry to the dictionary
        except:
            raise
    return status

def get_single_status(port): # Get the input connected to a given output port
    if port in config['outputs']: # Make sure port is an active output
        command_list = 'SL', str(config['level']), 'O', str(port), 'T' # Make a list of strings
        halfy_response = build_command(command_list) # Signal the halfy
        response_list = re.split(r'[\(|\ \)]', halfy_response) # Break the response string into a list
        if check_command(response_list.pop(0)): # Remove the command response and check that it succeeded
            response = [ int(x) for x in response_list if x != '' ] # Drop null entries, convert to int
            if not response:
                return { port : '' } # Return null string on unset output
            else:
                return { port : response[0] } # Compose dictionary
            return status
        else:
            raise ConfigError("command was not successfully implemented:", halfy_response)
    else:
        raise ConfigError("output port is not within active range:", port)

def set_single_status(out_port, in_port):
    if out_port in config['outputs'] and in_port in config['inputs']: # Make sure that our ports are active
        command_list = 'CL', str(config['level']), 'I', str(in_port), 'O', str(out_port), 'T' # Make a list of strings
        halfy_response = build_command(command_list) # Signal the halfy
        if check_command(halfy_response): # Make sure our command was successful
            return True
        else:
            raise ConfigError("command was not successfully implemented:", halfy_response)
    else:
        raise ConfigError("output and/or input port is not within active range:", { out_port : in_port})

def check_command(response): # Make sure that the command was successfully excecuted by the halfy
    response_chars = list(response) # Turn the command into a list of chars
    response_letter = response_chars.pop() # Grab the last char
    if response_letter == 'T':
        return True
    else:
        return False

def build_command(command_list): # Generate a command for the halfy, excecute it, and return the result
    command_string = "".join(command_list) # Concatenate into a single string
    command_bytes = command_string.encode('ascii') # Turn that string into ascii bytes
    return signaler(command_bytes) # Signal the halfy and return

def parse_config():
    # Load values from config file
    with open('config.json') as json_data_file:
        config = json.load(json_data_file) # Make a dictionary from the config file data

    # Make our string dictionary entries into integers
    config['level'] = int(config['level'])
    for port in 'inputs', 'outputs': 
        for key in config[port]: # Iterate over the keys in the input/output dictionaries
            config[port][int(key)] = config[port].pop(key) # Create a new dictionary item whose key is an integer

    # Sanitize config file variables
    if not os.path.exists(config['device_name']): # Serial port in use: string ['/dev/tty*']
        raise ConfigError("device_name does not exist [/dev/tty*]:", config['device_name'])
    for input_number in config['inputs']:
        if not 1 <= input_number <= 8: # Number of inputs in use: int [1-8]
            raise ConfigError("inputs is out of the allowed range [1-8]:", config['inputs'])
    for output_number in config['outputs']:
        if not 1 <= output_number <= 4: # Number of outputs in use: int [1-4]
            raise ConfigError("outputs is out of the allowed range [1-4]:", config['outputs'])
    if not 1 <= config['level'] <= 2: # Matrix switcher level in use: int [1-2]
        raise ConfigError("level is out of the allowed range [1-2]:", config['level'])

    return config

if __name__ == '__main__':
    try:
        config = parse_config() # Parse and sanitize variables from config file
        halfy = serial.Serial(config['device_name']) # Attempt to initialize serial port
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
        q = mp.Queue() # Initialize queue to talk to listener process

        # Initialize and start listener as a separate process
        p = mp.Process(target=listener)
        p.start()
        try:
            set_single_status(1, 7)
            out_dict = get_status()
            for output_port in sorted(config['outputs']):
                if not out_dict[output_port]:
                    print(config['outputs'][output_port], "is not connected")
                else:
                    print(config['outputs'][output_port], "is connected to", config['inputs'][out_dict[output_port]])
        except ConfigError as err:
            print("Command error:", err.error_message, err.incorrect_value)

        # If process is still active"Output"
        if p.is_alive():
            # Terminate
            p.terminate()
            p.join()
