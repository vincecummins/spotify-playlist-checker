from flask import Flask, render_template, url_for, request, redirect, session, g
import main

app = Flask(__name__)
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'

@app.route('/')
def index():
    if 'auth_header' in session:
        auth_header = session['auth_header']
        return render_template('index.html')
    return render_template('auth.html')


@app.route('/authorize', methods=['POST', 'GET'])
def auth():
    return redirect(main.spotify.AUTH_URL)

@app.route('/search', methods=['POST', 'GET'])
def search():
    auth_token = request.args['code']
    print(auth_token)
    auth_header = main.spotify.authorize(auth_token)
    session['auth_header'] = auth_header
    return render_template('index.html')

@app.route('/output', methods=['POST', 'GET'])
def output():
    if 'auth_header' in session:
        auth_header = session['auth_header']
        x = main.spotify.search(auth_header, request.args['playlist'])
        if x == False:
            return redirect(main.spotify.AUTH_URL)
        else:
            return render_template('output.html', p=x['p'], art=x['art'], art_p=x['art_p'], alb=x['alb'], alb_p=x['alb_p'], t=x['t'], t_p=x['t_p'], art_n=x['art_n'], art_np=x['art_np'])
    else:
        return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)