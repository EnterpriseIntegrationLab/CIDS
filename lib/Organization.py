# Organization code for CA Repository

# Creator: Mark S. Fox, msf@eil.utoronto.ca
# Date: 23 January 2021
# Copyright 2021 Mark S. Fox
# Available under: http://creativecommons.org/licenses/by/3.0/


import datetime
from owlready2 import *
from flask import Flask, render_template, request, session, redirect, url_for, g, flash

import config
import Util


def add() :

	# kick user out if they are not a superuser - should not happen as they would not get access to the registerorganization page
	if config.user.userType != config.cidsrep.superuser :
		return(render_template('main.html', message="You do not have access rights for Registering an Organization."))
		
	return(render(None, 'add', "http://localhost:5000/UpdateOrganization", False, ""))


def select() :
	if config.user.userType != config.cidsrep.superuser : 
		return(render_template('main.html', message="You do not have access rights for selecting an Organization."))
	
	action = request.args.get('action')
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditOrganization"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteOrganization"
	else :
		return(render_template('main.html', message="Error: Unknown Organization action: " + str(action)))
	
	return(render_template('organizationSelect.html', path=path, action=action))
	

def edit() :
	
	action = request.args.get('action') or request.form['action']
	path = "http://localhost:5000/UpdateOrganization"
	
	# get organization for the current user
	if config.user.userType == config.cidsrep.superuser :
		if action == "add" :
			og = config.organization = None
		else : 
			config.organization = og = config.cadr.search_one(iri=request.form['orgIRI'])
			if not og : return(render_template('main.html', message="Organization does not exist."))
	elif  (config.user.userType == config.cidsrep.admin) and ((action == "edit") or (action == "display")) : 
		og = config.user.forOrganization
	else :
		# kick user out if they are not a superuser or admin - should not happen as they would not get access to the registerorganization page
		return(render_template('main.html', message="You do not have access rights for Registering/Editing an Organization."))

	return(render(og, action, path, ""))
	

def update() :
	action = request.form["action"]
				
	# check that the organization does not already exist
	if action == 'add' :
		if config.user.userType != config.cidsrep.superuser :
			return(render_template('main.html', message="You do not have access rights for Adding an Organization."))
		oid = config.cadr.search_one(type=config.org.OrganizationID, hasIdentifier= request.form['orgID'])
		if oid : return(render_template('main.html', message="Error: Organization already exists."))
		neworg = config.cids.Organization(namespace=config.cadr)
		config.repository.hasOrganization.append(neworg)
		# create the OrganizationID and link
		orgID = config.org.OrganizationID(namespace=config.cadr)
		orgID.forOrganization = neworg
		orgID.hasIdentifier = request.form['orgID']
		neworg.hasID = orgID
		neworg.dateCreated = datetime.datetime.now().isoformat()
		
		# create impact model for common approach
		im = config.cids.ImpactMeasurement(namespace=config.cadr, forOrganization=neworg, hasStakeholder=[], 
			hasOutcome=[], hasIndicator=[], hasImpactRisk=[], hasImpactReport=[], hasStakeholderOutcome=[])
		neworg.hasImpactModel = [im]
		config.impactModel = im
		
	elif (action == "edit") and (config.user.userType in config.editEnabled) :
		orgID = config.cadr.search_one(type=config.org.OrganizationID, hasIdentifier = request.form['orgID'])
		if not orgID :  return(render_template('main.html', message="Error: Organization does not exist."))
		neworg = orgID.forOrganization
		print("Imapct models: ", neworg.hasLegalName, neworg.hasImpactModel)
		im = neworg.hasImpactModel[0]
	else :
		return(render_template('main.html', message="Error: Illegal action: " + action))
	
	config.organization = neworg
	readonly = "readonly" if config.user.userType != config.cidsrep.superuser else ""
	
	# Fill the instance of config.cids.Organization
	neworg.hasLegalName = request.form['hasLegalName']
	neworg.useOfFunds = request.form['useOfFunds']
	neworg.hasDescription = request.form['hasDescription']
	
	# Build the ic.Address instance and link
	if not neworg.hasAddress :
		addr = config.ic.Address(namespace=config.cadr)
		neworg.hasAddress = [addr]
	else :
		addr = neworg.hasAddress[0]
	print("address: ", addr, request.form['hasStreetNumber'])
	addr.hasStreetNumber = request.form['hasStreetNumber']
	addr.hasStreet = request.form['hasStreet']
	addr.hasUnitNumber = request.form['hasUnitNumber']
	addr.hasCityS = request.form['hasCityS']
	addr.hasProvince = request.form['hasProvince']
	addr.hasPostalCode = request.form['hasPostalCode']
	
	# Build Phone number for the Organization
	if not neworg.hasTelephone :
		pn1 = config.ic.PhoneNumber(namespace=config.cadr)
		neworg.hasTelephone = [pn1]
	else :
		pn1 = neworg.hasTelephone[0]
	pn1.hasPhoneNumber = request.form['hasPhoneNumber']
	
	# Build the contact as Person and link
	if not neworg.hasContact :
		contac = config.cids.Person(namespace=config.cadr)
		neworg.hasContact = [contac]
	else :
		contac = neworg.hasContact[0]
	contac.givenName = request.form['contactFirstName']
	contac.familyName = request.form['contactLastName']
	contac.hasEmail = request.form['contactEmail']
	
	if not contac.hasTelephone :
		pn2 = config.ic.PhoneNumber(namespace=config.cadr)
		contac.hasTelephone = [pn2]
	else :
		pn2 = contac.hasTelephone[0]
	pn2.hasPhoneNumber = request.form['contactPhoneNumber']
	
	config.cidsServer.save()
	Util.logIndividual("Update Organization", neworg, orgID, addr, pn1, contac, pn2, neworg.hasImpactModel[0])
	
	return(render(neworg, "display", readonly, "Organization " + orgID.hasIdentifier + " information saved."))


def delete() :
	if config.user.userType != config.cidsrep.superuser : 
		return(render_template('main.html', message="You do not have access rights for Deleting an Organization."))
	
	og = config.cadr.search_one(iri=request.form['orgIRI'])
	if og and og.hasID : 
		logIndividual("Delete Organization", og.hasID.hasIdentifier)
		destroy_entity(og.hasID)
	if og : 
		logIndividual("DeleteOrganization", og)
		destroy_entity(og)
	if og : return(render_template('main.html',  message="Deleted organization " + request.form['orgIRI'] + "."))
	return(render_template('main.html', message="Error: Organization " + request.form['orgIRI'] + " does not exist."))


def render(og, action, path, message) :
	priorValue = dict()
	priorValue['orgID'] = og.hasID.hasIdentifier if og and og.hasID else ""
	priorValue['hasLegalName'] = og.hasLegalName if og else ""
	priorValue['hasStreetNumber'] = og.hasAddress[0].hasStreetNumber if og and og.hasAddress else ""
	priorValue['hasStreet'] = og.hasAddress[0].hasStreet  if og and og.hasAddress else ""
	priorValue['hasUnitNumber'] = og.hasAddress[0].hasUnitNumber if og and og.hasAddress else ""
	priorValue['hasCityS'] = og.hasAddress[0].hasCityS if og and og.hasAddress else ""
	priorValue['hasState'] = og.hasAddress[0].hasState if og and og.hasAddress else ""
	priorValue['hasPostalCode'] = og.hasAddress[0].hasPostalCode if og and og.hasAddress else ""
	
	priorValue['hasPhoneNumber'] = og.hasTelephone[0].hasPhoneNumber if og and og.hasTelephone and og.hasTelephone[0].hasPhoneNumber else ""

	priorValue['contactFirstName'] = og.hasContact[0].givenName if og and og.hasContact else ""
	priorValue['contactLastName'] = og.hasContact[0].familyName if og and og.hasContact else ""
#	print("contact: ", og, og.hasContact, og.hasContact[0].hasTelephone, og.hasContact[0].hasTelephone[0].hasPhoneNumber)
	tel = og.hasContact[0].hasTelephone[0] if og and og.hasContact  and og.hasContact[0].hasTelephone else None
	priorValue['contactPhoneNumber'] = tel.hasPhoneNumber if tel and tel.hasPhoneNumber else ""
	
	return(render_template('organizationEdit.html', action=action, path=path, priorValue=priorValue ))