import logging
import time
import serial
import json
import os.path
import re
from threading import Lock
import subprocess

class CustomError(Exception):
    def __init__(self, error_message):
        self.error_message = error_message

class PowerRelay:
    def pr_signal(self, message):
        try:
            response = subprocess.check_output(message, shell=True)
        except subprocess.CalledProcessError as err:
            raise CustomError("Unable to communicate with power relay: {}".format(err))
        return response

    def get_power_status(self):
        response = self.pr_signal("cat /sys/class/gpio/gpio87/value")
        response_value = int(response.decode()[0])
        if response_value is 1:
            return True
        else:
            return False

    def power_on(self):
        if not self.get_power_status():
            self.pr_signal("echo 1 > /sys/class/gpio/gpio87/value")

    def power_off(self):
        if self.get_power_status():
            self.pr_signal("echo 0 > /sys/class/gpio/gpio87/value")

class MatrixSwitch:
    def __init__(self):
        # Parse the config file. Initialize the serial port.
        self.config = {} # A dictionary for variables gleaned from the config file
        self.init_status = {} # A dictionary containing our init status and error messages if appropriate
        self.lock = Lock() # A thread lock used to prevent multiple web server threads from using the serial port at once

        self.parse_config() # Parse our config file.
        if self.init_status['success']: # If that worked, initialize our serial device
            try:
                self.halfy = serial.Serial(self.config['device_name'], timeout=0)
            except serial.serialutl.SerialException as err:
                self.init_error( "Serial port initialization error: {}".format(err) )

    def signaler(self, command_list): # Send a command to the halfy and return the response
        with self.lock: # Only allow one thread to use the signaler at a time
            command_string = "".join(command_list) # Concatenate into a single string
            message = command_string.encode('ascii') # Turn that string into ascii bytes
            self.halfy.reset_input_buffer() # Clear the input buffer of leftovers
            self.halfy.write(message) # Write the command to the serial port
            logging.debug("Message sent to halfy: {}".format(message.decode()))

            # Ascertain what kind of command we're sending for control porpoises
            if message.decode()[0] in [ 'C', 'D' ]:
                end_char = 'T' # Change and Disconnect command responses should end with a 'T'
            elif message.decode()[0] is 'S':
                end_char = ')' # Status command responses should end with a ')'
            else:
                raise CustomError("Invalid command: {}".format(message.decode()))

            timeout = time.time() + 5 # 5 second timeout
            response_list = [] # List to put our response characters in
            while True:
                if time.time() > timeout: # Loop for 5 seconds, then errors away!
                    logging.warning("Response timeout. Chars recieved so far: {}".format(''.join(response_list)))
                    raise CustomError("Valid response was not recived from halfy in 5 seconds!")
                else: # Read our bytes
                    response_char = self.halfy.read(1) # Attempt to read one byte
                    if response_char: # If we got one, decode that byte into a char and add it to the list
                        response_list.append(response_char.decode())
                if response_char.decode() is end_char: # Check if we've reached the end of the response
                    break

            response = ''.join(response_list) # Concatenate our list into a string
            logging.debug("Message recieved from the halfy: {}".format(response))
            return response

    def get_status(self): # Read and print output statuses
        status = {} # Dictionary of statuses
        for output_port in sorted(self.config['outputs']): # Iterate over the outputs
            status.update(self.get_single_status(output_port)) # Attempt to add a status entry to the dictionary
        logging.debug("Status dictionary contains: {}".format(status))
        return status

    def get_single_status(self, port): # Get the input connected to a given output port
        if port in self.config['outputs']: # Make sure port is an active output
            command_list = 'SL', str(self.config['level']), 'O', str(port), 'T' # Make a list of strings
            halfy_response = self.signaler(command_list) # Signal the halfy
            response_list = re.split(r'[\(|\ \)]', halfy_response) # Break the response string into a list
            response_list.pop(0) # Remove the command response from the list
            response = [ int(x) for x in response_list if x != '' ] # Drop null entries, convert to int
            if not response:
                return { port : '' } # Return null string on unset output
            else:
                return { port : response[0] } # Compose dictionary
        else:
            raise CustomError("Output port is not active: {}".format(port))

    def set_single_status(self, out_port, in_port): # Connect one output to one input
        if out_port in self.config['outputs'] and in_port in self.config['inputs']: # Make sure that our ports are active
            command_list = 'CL', str(self.config['level']), 'I', str(in_port), 'O', str(out_port), 'T' # Make a list of strings
            self.signaler(command_list) # Signal the halfy
        else:
            raise CustomError("Invalid switch attempted. Output and/or input port not active: {}".format({ out_port : in_port}))

    def connect_all(self, in_port): # Connect all outputs to one input
        if in_port in self.config['inputs']: # Make sure that our port is active
            command_list = 'CL', str(self.config['level']), 'I', str(in_port), 'O', self.get_out_string(), 'T' # Make a list of strings
            self.signaler(command_list) # Signal the halfy
        else:
            raise CustomError("Invalid switch attempted. Input port is not active: {}".format(in_port))

    def disconnect_output(self, out_port): # Disconnect one output
        if out_port in self.config['outputs']: # Make sure that our port is active
            command_list = 'DL', str(self.config['level']), 'O', str(out_port), 'T' # Make a list of strings
            self.signaler(command_list) # Signal the halfy
        else:
            raise CustomError("Invalid disconnect attempted. Output port is not active: {}".format(out_port))

    def disconnect_all(self): # Disconnect all outputs
        command_list = 'DL', str(self.config['level']), 'O', self.get_out_string(), 'T' # Make a list of strings
        self.signaler(command_list) # Signal the halfy

    def get_out_string(self): # Return a comma-delimited string composed of the active output numbers
        out_list = []
        for out_port in self.config['outputs']:
            out_list.append(str(out_port))
        return ','.join(out_list)

    def init_error(self, err_msg):
        logging.critical(err_msg)
        self.init_status.update( { 'success' : False, 'message' : err_msg } )

    def parse_config(self):
        try:
            # Load values from config file
            with open('config.json') as json_data_file:
                self.config = json.load(json_data_file) # Make a dictionary from the config file data

            # Make our string dictionary values into integers
            self.config['level'] = int(self.config['level'])
            for port in 'inputs', 'outputs':
                self.config[port] = {int(key):value for key, value in self.config[port].items()}

            # Sanitize config file variables
            if not os.path.exists(self.config['device_name']): # Serial port in use: string ['/dev/tty*']
                raise CustomError("device_name does not exist [/dev/tty*]: {}".format(self.config['device_name']))
            for input_number, input_label in self.config['inputs'].items():
                if not 1 <= input_number <= 8: # Number of inputs in use: int [1-8]
                    raise CustomError("Input {} is out of the allowed range [1-8]: {}".format(input_number, self.config['inputs']))
            for output_number, output_label in self.config['outputs'].items():
                if not 1 <= output_number <= 4: # Number of outputs in use: int [1-4]
                    raise CustomError("Output {} is out of the allowed range [1-4]: {}".format(output_number, self.config['outputs']))
            if not 1 <= self.config['level'] <= 2: # Matrix switcher level in use: int [1-2]
                raise CustomError("Level is out of the allowed range [1-2]: {}".format(self.config['level']))
            if self.config['log_level'] is '': # Default to log level WARNING
                self.config['log_level'] = 'WARNING'
            log_level = logging.getLevelName(self.config['log_level']) # Convert log level for setting below
            if self.config['log_file'] is '': # Log to log_file if set
                logging.basicConfig(level=log_level, format='%(asctime)s %(levelname)s:%(message)s')
            else: # Or just log to console
                logging.basicConfig(level=log_level, filename=self.config['log_file'], format='%(asctime)s %(levelname)s:%(message)s')

        # Ensure that the config file is parsed properly
        except KeyError as err:
            self.init_error( "Missing or mislabeled config file key: {}".format(err) )
        except FileNotFoundError as err:
            self.init_error( "Missing or misnamed config file: {}".format(err) )
        except PermissionError as err:
            self.init_error( "Unable to access log file: {}".format(err) )
        except TypeError as err:
            self.init_error( "Type error: {}".format(err) )
        except ValueError as err:
            self.init_error( "Config file value error: {}".format(err) )
        except CustomError as err:
            self.init_error( "Config file value error: {}".format(err.error_message) )
        else:
            logging.debug("Config dictionary contains: \n{}".format(self.config))
            self.init_status.update( { 'success' : True } )
