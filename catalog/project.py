#! /usr/bin/env python3

from flask import Flask, render_template
from flask import request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Company, Watches, User

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "company watch Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///companywithusers.db',
                       connect_args={'check_same_thread': False}, echo=True)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token

@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    comp = session.query(Company).all()
    # return "The current session state is %s" % login_session['state']
    return render_template('log.html', STATE=state, comp=comp)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already'
                                            'connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # See if a user exists, if it doesn't make a new one
    user_id = getUserId(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    output = '<div style="text-align: center;">'
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += data['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    output += '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    output += '</div>'
    flash("you are now logged in as %s" % login_session['username'])
    return output


# User Helper Functions


def createUser(login_session):
    print("in createUser")
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserId(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        print("in getUserId try")
        return user.id
    except BaseException:
        print("in getUserId except")
        return None


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('showcompanys'))
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Show all companys
@app.route('/')
@app.route('/company')
def showcompanys():
    company = session.query(Company).all()
    return render_template('showcompanys.html', company=company)

# Create a new company


@app.route('/company/new/', methods=['GET', 'POST'])
def newcompany():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newcompany = Company(
            name=request.form['name'], user_id=login_session['user_id'],
            description=request.form['Description'], pic=request.form['pic'])
        session.add(newcompany)
        flash('New company %s Successfully Created' % newcompany.name)
        session.commit()
        return redirect(url_for('showcompanys'))
    else:
        return render_template('newcompany.html')

# Edit a company


@app.route('/company/<int:company_id>/edit/', methods=['GET', 'POST'])
def editCompany(company_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedcompany = session.query(Company).filter_by(id=company_id).one()
    creator = getUserInfo(editedcompany.user_id)
    user = getUserInfo(login_session['user_id'])
    if creator.id != login_session['user_id']:
        flash("you can't edit this company ."
              "This belongs to  %s" % creator.name)
        return redirect(url_for('showcompanys'))
    if request.method == 'POST':
        editedcompany.name = request.form['name']
        editedcompany.description = request.form['Description']
        if request.form['pic']:
            print("in pic edit")
            editedcompany.pic = request.form['pic']
        session.add(editedcompany)
        session.commit()
        flash('company Successfully Edited %s' % editedcompany.name)
        return redirect(url_for('showcompanys'))
    else:
        return render_template('editcompany.html', company=editedcompany)


# Delete a company
@app.route('/company/<int:company_id>/delete/', methods=['GET', 'POST'])
def deleteCompany(company_id):
    if 'username' not in login_session:
        return redirect('/login')
    companyToDelete = session.query(
        Company).filter_by(id=company_id).one()
    creator = getUserInfo(companyToDelete.user_id)
    user = getUserInfo(login_session['user_id'])
    if creator.id != login_session['user_id']:
        flash("you can't delete this company name."
              "This belongs to  %s" % creator.name)
        return redirect(url_for('showcompanys'))
    if request.method == 'POST':
        session.delete(companyToDelete)
        flash('%s Successfully Deleted' % companyToDelete.name)
        session.commit()
        return redirect(url_for('showcompanys', company_id=company_id))
    else:
        return render_template('deletecompany.html', company=companyToDelete)

# Show a company watch


@app.route('/company/<int:company_id>/')
@app.route('/company/<int:company_id>/watch/')
def showwatch(company_id):
    company = session.query(Company).filter_by(id=company_id).one()
    items = session.query(Watches).filter_by(company_id=company_id).all()
    return render_template('watch.html', items=items, company=company)


# Create a new watch item
@app.route('/company/<int:company_id>/watch/new/', methods=['GET', 'POST'])
def newwatchItem(company_id):
    if 'username' not in login_session:
        return redirect('/login')
    company = session.query(Company).filter_by(id=company_id).one()
    creator = getUserInfo(company.user_id)
    print (company.user_id, creator)
    user = getUserId(login_session['email'])
    if user != company.user_id:
        flash("you can't add new watch menu."
              "This belongs to  %s" % creator.name)
        return redirect(url_for('showwatch', company_id=company_id))
    if request.method == 'POST':
        newItem = Watches(name=request.form['name'],
                          description=request.form['description'],
                          price=request.form['price'],
                          pic1=request.form['pic1'],
                          company_id=company_id, user_id=company.user_id)
        session.add(newItem)
        session.commit()
        flash('New watch %s Item Successfully Created' % (newItem.name))
        return redirect(url_for('showwatch', company_id=company_id))
    else:
        return render_template('newwatchitem.html', company_id=company_id)

# Edit a watch item


@app.route('/company/<int:company_id>/watch/<int:watch_id>/edit',
           methods=['GET', 'POST'])
def editwatchItem(company_id, watch_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Watches).filter_by(id=watch_id).one()
    company = session.query(Company).filter_by(id=company_id).one()
    creator = getUserInfo(company.user_id)
    user = getUserInfo(login_session['user_id'])
    if creator.id != login_session['user_id']:
        flash("you can't edit this watch menu."
              "This belongs to  %s" % creator.name)
        return redirect(url_for('showwatch', company_id=company_id))
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['pic1']:
            editedItem.pic1 = request.form['pic1']
        session.add(editedItem)
        session.commit()
        flash('watch Item Successfully Edited')
        return redirect(url_for('showwatch', company_id=company_id))
    else:
        return render_template('editwatchitem.html',
                               company_id=company_id,
                               watch_id=watch_id, item=editedItem)


# Delete a watch item
@app.route('/company/<int:company_id>/watch/<int:watch_id>/delete',
           methods=['GET', 'POST'])
def deletewatchItem(company_id, watch_id):
    if 'username' not in login_session:
        return redirect('/login')
    company = session.query(Company).filter_by(id=company_id).one()
    itemToDelete = session.query(Watches).filter_by(id=watch_id).one()
    creator = getUserInfo(company.user_id)
    user = getUserInfo(login_session['user_id'])
    if creator.id != login_session['user_id']:
        flash("you can't delete this watch menu."
              "This belongs to  %s" % creator.name)
        return redirect(url_for('showwatch', company_id=company_id))
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('watch Item Successfully Deleted')
        return redirect(url_for('showwatch', company_id=company_id))
    else:
        return render_template('deletewatchItem.html',
                               company_id=company_id, item=itemToDelete)


# JSON APIs to view company Information
@app.route('/company/<int:company_id>/watch/JSON')
def watchMenuJSON(company_id):
    company = session.query(Company).filter_by(id=company_id).one()
    items = session.query(Watches).filter_by(
        company_id=company_id).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/company/<int:company_id>/watch/<int:watch_id>/JSON')
def WatchesJSON(company_id, watch_id):
    Menu_Item = session.query(Watches).filter_by(id=watch_id).one()
    return jsonify(Menu_Item=Menu_Item.serialize)


@app.route('/company/JSON')
def companysJSON():
    companys = session.query(Company).all()
    return jsonify(companys=[r.serialize for r in companys])


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
