# login.py contains the functions used to process logging in and logging out of the CA repository
# they are accessed by CA-Repository-Server.py

# Creator: Mark S. Fox, msf@eil.utoronto.ca
# Date: 23 January 2021
# Copyright 2021 Mark S. Fox
# Available under: http://creativecommons.org/licenses/by/3.0/

import datetime
from werkzeug.utils import secure_filename
import os
from owlready2 import *
from flask import Flask, render_template, request, session, redirect, url_for, g, flash

# Import required CA-Repository modules
import sys
sys.path.insert(0, './lib')
import config
import Util
import ImpactModel


def index() :
	return(render_template('index.html'))
	

def login() :
	print('email: ', request.form['hasEmail'], ' password: ', request.form['hasPassword'])
	valid_user = valid_login(request.form['hasEmail'],request.form['hasPassword'])
	if valid_user :
		log_the_user_in(valid_user)
		
		if config.user.userType in [config.cidsrep.admin, config.cidsrep.editor]: 
			if len(config.organization.hasImpactModel) > 1 :
				impactModels = [ (im.iri, im.hasName, im.hasDescription) for im in config.organization.hasImpactModel ]
				return(render_template("impactModelSelect.html", action="display", message="Please select Impact Model workspace."))
			config.impactModel = config.organization.hasImpactModel[0]
			return(ImpactModel.render(config.impactModel, "display", "", config.organization.hasID.hasIdentifier + " Impact Model Configuration."))
		return(render_template('main.html'))
	else :
		return(render_template('index.html', message="Login Failed: Invalid email or password"))

def valid_login(email, password) :
	print("cidsServer in valid login:" , config.cidsServer)
	print('user: ', config.cidsrep.User)
	luser = config.cidsServer.search_one(type=config.cidsrep.User, hasEmail=email)
#	obj = AES.new('CARepository key2021', AES.MODE_CBC, 'This is an IV456')
#	if luser and obj.decrypt(user.password) == password	: return(luser)
	if luser and luser.hasPassword == password	: return(luser)
	return(False)
	
def log_the_user_in(luser) : 
	session['hasEmail'] = luser.hasEmail	
	# set the global variable for user
	config.user = luser
	config.organization = None if config.user.userType == config.cidsrep.superuser else config.user.forOrganization
	# default impact model is the first one, if one exists
	if config.organization and config.organization.hasImpactModel and len(config.organization.hasImpactModel) >= 1:
		config.impactModel = config.organization.hasImpactModel[0]
	else :
		config.impactModel = None

def logout():
	# remove the user Email from the session if it's there
	session.pop('hasEmail', None)
	# set session user to None
	config.user = None
	config.organization = None
	config.userType = None
	config.cidsServer.save()
	return redirect(url_for('index'))

# writes out the current database of instances (not the ontologies) into a file
def saveCADR() :
	print("saving cadr instances")
	cadrfile = path + "/cadrarchive/cadr.rdf" + "." + str(datetime.datetime.now())
	config.cadr.save(file=cadrfile)  # saves as rdf/xml as default
	return(render_template('main.html', message="CADR saved as " + cadrfile))




