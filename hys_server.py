import logging
import time
import serial
import json
import os.path
import re
from flask import Flask, render_template, request, redirect, flash, session, url_for

app = Flask(__name__)
app.secret_key = '7JmEPqJ82SiS9GciBNHB8k82Zg7AvOqg' # A little entropy for the session handling

# If we have a session, load the console, otherwise redirect to the login
@app.route('/')
def index():
    if 'username' in session:
        status_dict = get_status()
        return render_template('console.html', outputs=config['outputs'], inputs=config['inputs'], connections=status_dict)
    else:
        return redirect(url_for('login'))

# Simple session, just a username
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    else:
        return render_template('login.html')

# Remove the username and redirect to index (and from there to login)
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

# Affect a port switch and redirect to index
@app.route('/switch')
def middle():
    try:
        output_port = int(request.args.get('output_port', ''))
        input_port = int(request.args.get('input_port', ''))
        set_single_status(output_port, input_port)
    except CustomError as err:
        logging.warning(err.error_message)
        flash("Warning: something didn't work. Check the logs, yo!")
    except ValueError as err:
        logging.warning("Invalid input or output value: {}".format(err))
        flash("Warning: something didn't work. Check the logs, yo!")
    return redirect(url_for('index'))

class CustomError(Exception):
    def __init__(self, error_message):
        self.error_message = error_message

def signaler(message, command_type): # Send a command to the halfy and return the response
    halfy.reset_input_buffer() # Clear the input buffer of leftovers
    halfy.write(message) # Write the command to the serial port
    # Ascertain what kind of command we're sending for timing porpoises
    if command_type == 'CL':
        response_length = len(message)
    elif command_type == 'SL':
        response_length = len(message) + 2
    # Wait for the response bytes to appear, max one second
    timeout = time.time() + 1
    while halfy.in_waiting < response_length:
        if time.time() > timeout:
            break
    time.sleep(.005) # Wait just a bit longer, because reasons
    response = halfy.read(halfy.in_waiting) # Read the number of bytes contained in the input buffer
    return response.decode() # Decode from ascii bytes to string and return

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
            raise CustomError("Get status command was not successfully implemented: {}".format(halfy_response))
    else:
        raise CustomError("Output port is not active: {}".format(port))

def set_single_status(out_port, in_port):
    if out_port in config['outputs'] and in_port in config['inputs']: # Make sure that our ports are active
        command_list = 'CL', str(config['level']), 'I', str(in_port), 'O', str(out_port), 'T' # Make a list of strings
        halfy_response = build_command(command_list) # Signal the halfy
        if check_command(halfy_response): # Make sure our command was successful
            return True
        else:
            raise CustomError("Set command was not successfully implemented: {}".format(halfy_response))
    else:
        raise CustomError("Invalid switch attempted. Output and/or input port is not active: {}".format({ out_port : in_port}))

def check_command(response): # Make sure that the command was successfully excecuted by the halfy
    response_chars = list(response) # Turn the command into a list of chars
    if response_chars != []: # Make sure that there's something to check
        response_letter = response_chars.pop() # Grab the last char
        if response_letter == 'T': # Make sure it's a 'T'
            return True
        else:
            return False
    else:
        return False

def build_command(command_list): # Generate a command for the halfy, excecute it, and return the result
    command_type = command_list[0] # Grab the command type to send to signaler
    command_string = "".join(command_list) # Concatenate into a single string
    command_bytes = command_string.encode('ascii') # Turn that string into ascii bytes
    return signaler(command_bytes, commmand_type) # Signal the halfy and return

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
        raise CustomError("device_name does not exist [/dev/tty*]: {}".format(config['device_name']))
    for input_number in config['inputs']:
        if not 1 <= input_number <= 8: # Number of inputs in use: int [1-8]
            raise CustomError("Input {} is out of the allowed range [1-8]: {}".format(input_number, config['inputs']))
    for output_number in config['outputs']:
        if not 1 <= output_number <= 4: # Number of outputs in use: int [1-4]
            raise CustomError("Output {} is out of the allowed range [1-4]: {}".format(output_number, config['outputs']))
    if not 1 <= config['level'] <= 2: # Matrix switcher level in use: int [1-2]
        raise CustomError("Level is out of the allowed range [1-2]: {}".format(config['level']))
    if config['log_level'] is '': # Default to log level WARNING
        config['log_level'] = 'WARNING'
    log_level = logging.getLevelName(config['log_level']) # Convert log level for setting below
    if config['log_file'] is '': # Log to log_file if set
        logging.basicConfig(level=log_level, format='%(asctime)s %(levelname)s:%(message)s')
    else: # Or just log to console
        logging.basicConfig(level=log_level, filename=config['log_file'], format='%(asctime)s %(levelname)s:%(message)s')

    return config

if __name__ == '__main__':
    try:
        config = parse_config() # Parse and sanitize variables from config file
        halfy = serial.Serial(config['device_name']) # Attempt to initialize serial port
    # Ensure that the config file is parsed properly and the serial port was initialized
    except serial.serialutil.SerialException as err:
        logging.critical("Serial Port Error: {}".format(err))
    except KeyError as err:
        logging.critical("Missing or mislabeled config file key: {}".format(err))
    except json.decoder.JSONDecodeError as err:
        logging.critical("Misformatted config file: {}".format(err))
    except FileNotFoundError as err:
        logging.critical("Missing or misnamed config file: {}".format(err))
    except PermissionError as err:
        logging.critical("Unable to access log file: {}".format (err))
    except ValueError as err:
        logging.critical("Invalid error level passed: {}".format(err))
    except CustomError as err:
        logging.critical("Config file value error: {}".format(err.error_message))
    else:
        try:
            app.run(debug=True)
        except KeyboardInterrupt:
            print("Forced Shutdown")
            halfy.close()
