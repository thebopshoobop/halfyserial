import serial

halfy = serial.Serial('/dev/ttyUSB0') # Initialize serial port
i = ''
chars = []

while i != b')': # Loop until you read a close paren from the serial port
    i = halfy.read(1) # Attempt to read one byte from the serial port
    chars.append(i.decode()) # Turn that byte into a char

print(''.join(chars)) # Print the response from the serial port
