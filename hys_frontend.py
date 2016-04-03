import hys_backend
from flask import Flask, render_template, request, redirect, flash, session, url_for

app = Flask(__name__)
app.secret_key = '7JmEPqJ82SiS9GciBNHB8k82Zg7AvOqg' # A little entropy for the session handling

halfy = hys_backend.MatrixSwitch()
pr = hys_backend.PowerRelay()

# If we have a session, load the console, otherwise redirect to the login
@app.route('/')
def index():
    if 'username' in session:
        if halfy.init_status['success']:
            try:
                status_dict = halfy.get_status()
                amp_power = pr.get_power_status()
            except hys_backend.CustomError as err:
                hys_backend.logging.warning(err.error_message)
                flash("Warning: Failed status check, please refresh.")
                return redirect(url_for('error_page'))
            else:
                return render_template('console.html', outputs=halfy.config['outputs'], inputs=halfy.config['inputs'], connections=status_dict, amp_power=amp_power)
        else:
            flash(halfy.init_status['message'])
            return redirect(url_for('error_page'))
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

# Remove the username and redirect to login
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Affect a port switch and redirect to index
@app.route('/switch')
def middle():
    try:
        output_port = int(request.args.get('output_port', ''))
        input_port = int(request.args.get('input_port', ''))
        halfy.set_single_status(output_port, input_port)
    except hys_backend.CustomError as err:
        hys_backend.logging.warning(err.error_message)
        flash("Warning: Possible failed switch. Please check the logs.")
    except ValueError as err:
        hys_backend.logging.warning("Invalid input or output value: {}".format(err))
        flash("Warning: something didn't work. Check the logs, yo!")
    return redirect(url_for('index'))

# Connect all outputs to a single input and redirect to index
@app.route('/connect_all')
def connect_all():
    try:
        input_port = int(request.args.get('input_port', ''))
        halfy.connect_all(input_port)
    except hys_backend.CustomError as err:
        hys_backend.logging.warning(err.error_message)
        flash("Warning: Possible failed switch. Please check the logs.")
    except ValueError as err:
        hys_backend.logging.warning("Invalid input value: {}".format(err))
        flash("Warning: something didn't work. Check the logs, yo!")
    return redirect(url_for('index'))

# Disconnect an/all output(s) and redirect to index
@app.route('/disconnect', defaults={'output_port': 'all'})
@app.route('/disconnect/<int:output_port>')
def disconnect(output_port):
    try:
        if output_port is 'all':
            halfy.disconnect_all()
        else:
            halfy.disconnect_output(output_port)
    except hys_backend.CustomError as err:
        hys_backend.logging.warning(err.error_message)
        flash("Warning: Possible failed switch. Please check the logs.")
    except ValueError as err:
        hys_backend.logging.warning("Invalid output value: {}".format(err))
        flash("Warning: something didn't work. Check the logs, yo!")
    return redirect(url_for('index'))

# Power Switch
@app.route('/power/<int:switch_direction>')
def power_switch(switch_direction):
    try:
        if switch_direction is 1:
            pr.power_on()
        elif switch_direction is 0:
            pr.power_off()
    except hys_backend.CustomError as err:
        hys_backend.logging.warning(err.error_message)
        flash("Warning: Possible failed switch. Please check the logs.")
    return redirect(url_for('index'))

# Something went wrong...
@app.route('/error')
def error_page():
    return render_template('error.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8888)
