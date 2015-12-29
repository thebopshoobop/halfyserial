import multiprocessing as mp
#import time
import serial

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

def get_status(): # Read and print status
    for i in [ b'SL1O1T', b'SL1O2T', b'SL1O3T', b'SL1O4T' ]: # Iterate over the output status commands
        status = signaler(i)
        print(status)

if __name__ == '__main__':
    halfy = serial.Serial('/dev/ttyUSB0') # Initialize serial port
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