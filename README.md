# halfyserial
##### a web app that controls a half-y matrix switcher for my home stereo

I'm using an AutoPatch half-y matrix switcher that has 8 inputs and 4 outputs.
The half-y is controlled over a USB serial adapter with pySerial.
The control interface is a simple responsive web app built with [Python 3](https://www.python.org/), [Flask](flask.pocoo.org), [Jinja2 templates](http://jinja.pocoo.org/), and [Skeleton Framework](https://github.com/skeletonframework/skeletonframework) with [normalize.css](https://github.com/necolas/normalize.css/).

### Installation:

This is deployed on [Ubuntu 14.04](http://releases.ubuntu.com/14.04/), [Gunicorn](http://gunicorn.org/), and [Nginx](http://nginx.org/). In order to use up-to-date software, I've added the [nginx/stable ppa](https://launchpad.net/~nginx/+archive/ubuntu/stable) and installed all my python dependencies via pip in a virtualenv.

The hys_nginx file goes in /etc/nginx/sites-enabled/. The hys_server.conf goes in /etc/init/.

You will need to create a config file.

### Config file format:

The config file is called config.json and is located in your application directory (i.e. /var/www/whatever/).
It follows the following format outline:

```json
{
    "device_name":"/dev/ttyUSB0",
    "inputs":{
        "1":"Line In",
        "3":"Laptop"
    },
    "outputs":{
        "1":"Living Room",
        "4":"Kitchen"
    },
    "level":"1",
    "log_level":"Debug",
    "log_file":""
}
```

* device_name: The name of the serial port device
* inputs: A dictionary of the format { input_number : input_label }
  * Valid values for input_number are 1-8
* outputs: A dictionary of the format { output_number : output_label }
  * Valid values for output_number are 1-4
* level: The level of the halfy switcher in use
  * Valid values for level are 1-2
* log_level: Log level, level WARNING on null [default]
  * Valid values: "", DEBUG, INFO, WARNING, ERROR, CRITICAL
* log_file: Log file name, log to console on null [default]
  * Valid values: "", some_file_name