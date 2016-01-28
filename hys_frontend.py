import hys_backend as halfy
from flask import Flask, render_template, request, redirect, flash, session, url_for

app = Flask(__name__)
app.secret_key = '7JmEPqJ82SiS9GciBNHB8k82Zg7AvOqg' # A little entropy for the session handling

# If we have a session, load the console, otherwise redirect to the login
@app.route('/')
def index():
    if 'username' in session:
        try:
            status_dict = halfy.get_status()
        except halfy.CustomError as err:
            halfy.logging.warning(err.error_message)
            flash("Warning: Failed status check, please refresh.")
            status_dict = {}
        return render_template('console.html', outputs=halfy.config['outputs'], inputs=halfy.config['inputs'], connections=status_dict)
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
        halfy.set_single_status(output_port, input_port)
    except halfy.CustomError as err:
        halfy.logging.warning(err.error_message)
        flash("Warning: Possible failed switch. Please check the logs.")
    except ValueError as err:
        halfy.logging.warning("Invalid input or output value: {}".format(err))
        flash("Warning: something didn't work. Check the logs, yo!")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)