# User  code for CA Repository

# Creator: Mark S. Fox, msf@eil.utoronto.ca
# Date: 23 January 2021
# Copyright 2021 Mark S. Fox
# Available under: http://creativecommons.org/licenses/by/3.0/

import config
import datetime
from owlready2 import *
from flask import Flask, render_template, request, session, redirect, url_for, g, flash
import Util


def add() :

	path = "http://localhost:5000/UpdateUser"
	if config.user.userType == config.cidsrep.superuser : return(render(None, 'add', path, False, "Adding User in Superuse mode."))
	
	if config.user.userType == config.cidsrep.admin :	
		return(render(None, "add", path, True, "Adding User in Admin mode."))
	
	return(render_template('main.html', message="Error: User does not have permission to add a User."))


def select() :
	if not config.user.userType in config.adminEnabled : 
		return(render_template('main.html', message="You do not have access rights to add a User."))
	
	action = request.args.get('action')

	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditUser"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteUser"
	else :
		return(render_template('main.html', message="Error: Unknown User action: " + str(action)))
	
	if (config.user.userType == config.cidsrep.superuser) : return(render_template('userSelect.html', path=path, action=action))
	
	users = config.cadr.search(type=config.cidsrep.User, forOrganization=config.organization)
	return(render_template('userSelect.html', path=path, action=action, users=users))


def edit() :
	
	path = "http://localhost:5000/UpdateUser"

	if not config.user.userType in config.adminEnabled :
		return(render_template('main.html', message="Error: " + config.user.hasEmail + " does not have permission to edit a User."))
		
	euser = config.cadr.search_one(iri=request.form['userIRI'])
	if not euser :
		return(render_template('main.html', message="Error: User " + request.form['userIRI'] + " does not exist."))
		
	if (config.user.userType == config.cidsrep.admin) and (config.user.forOrganization != euser.forOrganization) :
		return(render_template('main.html', message="Error: User " + config.user.hasEmail + " and " + request.form['hasEmail'] + " organizations do not match."))
	
	action = request.form['action']
	readonly = "readonly" if config.user != config.cidsrep.superuser else ""
	
	return(render(euser, action, path, readonly, ""))

	
def update() :
	action = request.form['action']
	
	# check if user already is defined for this organization with same email address, when adding
	if action == "add" :
		euser = config.cadr.search_one(type=config.cidsrep.User, hasEmail=request.form['hasEmail'], forOrganization=config.organization)
		if euser : return(render_template('main.html', message="Error: User already exists: " + request.form['hasEmail']))
	
	# kick out update if user is not admin enables
	if not config.user.userType in config.adminEnabled: 
		return(render_template('main.html', message="Error: User does not have permission to add a User."))

	if not request.form['userIRI'] : 
		euser = config.cidsrep.User(namespace=config.cadr, forPerson= config.cids.Person(namespace=config.cadr))
		config.repository.hasUser.append(euser)
	else :
		euser = config.cadr.search_one(iri=request.form['userIRI'])
		if not euser : return(render_template('main.html', message="Error: User does not exist. " + request.form['userIRI']))

	euser.hasEmail = request.form['hasEmail']
	euser.hasPassword = request.form['hasPassword']
	euser.forPerson.givenName = request.form['givenName']
	euser.forPerson.familyName = request.form['familyName']
	if not euser.forPerson.hasTelephone :
		pn = config.ic.PhoneNumber(namespace=config.cadr)
		euser.forPerson.hasTelephone = [pn]
	else :
		pn = euser.forPerson.hasTelephone[0]
	euser.userType = config.userTypesMap[request.form['userType']]
	pn.hasPhoneNumber = request.form['hasPhoneNumber']
	euser.forOrganization = config.user.forOrganization if config.user.userType == config.cidsrep.admin else config.organization
	
	config.cidsServer.save()
	Util.logIndividual("Update User", euser, euser.forPerson, pn)

	readonly = "readonly" if config.user != config.cidsrep.superuser else ""
	return(render(euser, "display", "", readonly, "User " + euser.hasEmail + " added."))
	
	
	
	

def delete() :
	
	if not config.user.userType in config.adminEnabled : 
		return(render_template('main.html', message="You do not have access rights to add a User."))
	
	euser = config.cadr.search_one(iri=request.form['userIRI'])
	if euser :
		if (config.user.userType == config.cidsrep.admin) and  (euser.forOrganization != config.user.forOrganization) :
			return(render_template('main.html', message="You can only delete Users associated with your organization."))
		Util.logIndividual("Deleted User", euser)
		userEmail = euser.hasEmail
		destroy_entity(euser)
		return(render_template('menu.html',  message="Deleted user " + userEmail + "."))
	return(render_template('main.html', message="Error: User " + request.form['hasEmail'] + " does not exist."))


def render(user, action, path, readonly, message) :
	priorValue = dict()
	priorValue['userIRI'] = user.iri if user else ""
	priorValue['hasEmail'] = user.hasEmail if user and user.forPerson else ""
	priorValue['hasPassword'] = user.hasPassword if user and user.forPerson else ""
	priorValue['givenName'] = user.forPerson.givenName  if user and user.forPerson else ""
	priorValue['familyName'] = user.forPerson.familyName if user and user.forPerson else ""
	priorValue['hasPhoneNumber'] =  user.forPerson.hasTelephone[0].hasPhoneNumber if user and user.forPerson and user.forPerson.hasTelephone else ""
	priorValue['userType'] = user.userType.label if user and user.forPerson else ""
	
	return(render_template('userEdit.html', priorValue=priorValue, readonly=readonly, action=action, message=message, path=path))
				
	