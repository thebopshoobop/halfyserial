import multiprocessing as mp
import serial
import json

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

def get_status(segment = outputs): # Read and print input or output statuses
    # Generate and excecute status comands
    for i in range(segment):
        port = i + 1 # Switch to 1-indexed range
        get_single_status(port, segment)

def get_single_status(port, segment = outputs):
    segment_char = 'O' # Default to checking output
    if segment is inputs: # Override default and check input
        segment_char = 'I'

    command_list = 'SL', str(level), segment_char, str(port), 'T' # Make a list of strings
    command_string = "".join(command_list) # Concatenate into a single string
    command_bytes = command_string.encode('ascii') # Turn that string into ascii bytes
    status = signaler(command_bytes) # Signal the halfy
    print(status)

if __name__ == '__main__':
    # Load values from settings file
    with open('config.json') as json_data_file:
        data = json.load(json_data_file) # Make a dictionary from the config file data
        device_name = data['device_name'] # Serial port in use: string ['/dev/tty*']
        inputs = int(data['inputs']) # Number of inputs in use: int [1-8]
        outputs = int(data['outputs']) # Number of outputs in use: int [1-4]
        level = int(data['level') # Matrix level in use: int [1-2]

    try:
        halfy = serial.Serial(device_name) # Attempt to initialize serial port
    except serial.serialutil.SerialException as err: # Catch exceptions from pyserial
        print("Serial Port Error:", err)
    else:
        q = mp.Queue() #Initialize queue to talk to listener process

        # Initialize and start listener as a separate process
        p = mp.Process(target=listener)
        p.start()
        get_status()

        # If process is still active
        if p.is_alive():
            print("Done.")

            # Terminate
            p.terminate()
            p.join()
