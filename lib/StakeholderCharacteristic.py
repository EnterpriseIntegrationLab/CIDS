# StakeholderCharacteristic code for CA Repository

# Creator: Mark S. Fox, msf@eil.utoronto.ca
# Date: 15 Februrary 2021
# Copyright 2021 Mark S. Fox
# Available under: http://creativecommons.org/licenses/by/3.0/

import config
import datetime
from owlready2 import *
from flask import Flask, render_template, request, session, redirect, url_for, g, flash
import Util


def add() :
	if not config.user.userType in config.editEnabled : 
		return(render_template('main.html', message="Error: User does not have permission to add a Stakeholder Characteristic."))
		
	path = "http://localhost:5000/UpdateStakeholderCharacteristic"
	return(render(None, "add", path, ""))


def select() :
	action = request.args.get('action')
	
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditStakeholderCharacteristic"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteStakeholderCharacteristic"
	else :
		return(render_template('main.html', message="Error: Unknown Stakeholder Characteristic action: " + action))
		
	if not config.user.userType in config.editEnabled :
		return(render_template('main.html', message="Error: " + config.user.hasEmail + "  does not have permission to edit/display a Stakeholder Characteristic."))
		
	return(render_template('stakeholderCharacteristicSelect.html', path=path, action=action))
	

def edit() :
	if request.method == 'POST':
		action = request.form['action']
		stkcIRI = request.form['stkcIRI']
	else :
		action = "display"
		stkcIRI = request.args.get('stkcIRI')
	
	path = "http://localhost:5000/UpdateStakeholderCharacteristic"
	
	if not Util.verifyOrganization(config.user) :
		return(render_template('main.html', message="Error: User-Organization mismatch."))
	
	if (not config.user.userType in config.editEnabled) and (action != 'display') :
		return(render_template('main.html', message="Error: User does not have permission to add/edit a Stakeholder Characteristic."))

	stkc = config.cadr.search_one(type=config.cids.StakeholderCharacteristic, iri=stkcIRI)
	if not stkc :
		return(render_template('main.html', message="Error: Stakeholder Characteristic" + request.form['stkcIRI'] + " does not exist."))

	return(render(stkc, action, path, ""))


def update() :
	action = request.form['action']
	
	# check if user is permitted to add a Stakeholder
	if not config.user.userType  in config.editEnabled:
		return(render_template('main.html', message="Error: User does not have permission to add/update a Stakeholder Characteristic."))
	if not Util.verifyOrganization(config.user) :
		return(render_template('main.html', message="Error: User-Organization mismatch."))
	
	# check if stakeholder characteristic already exists for the org and doing add
	if request.form['action'] == 'add' :
		stkc = config.cadr.search_one(type=config.cids.StakeholderCharacteristic, hasName=request.form['hasName'], forOrganization=config.organization)
		if stkc : return(render_template('main.html', message="Error: Stakeholder Characteristic with that name already exists."))
		stkc = config.cids.StakeholderCharacteristic(namespace=config.cadr)
		stkc.forStakeholder = stk = config.cadr.search_one(type=config.cids.Stakeholder, iri=request.form['forStakeholder'])
		stkc.forOrganization = config.organization
		print("impact Model ", config.impactModel, " stk char: ", config.impactModel.hasCharacteristic, " stkc: ", stkc)
		config.impactModel.hasCharacteristic.append(stkc)
		stkc.forStakeholder.hasCharacteristic.append(stkc)
	elif action == 'edit' :
		stkc = config.cadr.search_one(type=config.cids.StakeholderCharacteristic, iri=request.form['stkcIRI'])
		if not stkc :return(render_template('main.html', message="Error: Stakeholder Characteristic not found in database."))
		stk = stkc.forStakeholder
		# remove characteristic if stakeholder has changed
		if stk.iri != request.form['forStakeholder'] :
			stk.hasCharacteristic.remove(stkc)
			stk = config.cadr.search_one(type=config.cids.Stakeholder, iri=request.form['forStakeholder'])
			stk.hasCharacteristic.append(stkc)
			stkc.forStakeholder = stk
	else :
		return(render_template('main.html', message="Error: Illegal action: " + action))
	
	stkc.hasSpecification = [request.form['hasSpecification']]
	stkc.hasName = request.form['hasName']
	stkc.hasDescription = request.form['hasDescription']
	stkc.hasIdentifier = request.form['hasIdentifier']
	stkc.codeValue = False if (not 'codeValue' in request.form) or (request.form['codeValue'] != "Yes") else True
		
	Util.logIndividual("Update Stakeholder Characteristic", stkc, stk, config.impactModel)
	return(render(stkc, "display", "", " Stakeholder Characteristic " + action + " successful."))


def delete() :
	# check if user is permitted to delete stakeholder Characteristic
	if not config.user.userType in config.editEnabled :
		return(render_template('main.html', message="Error: User does not have permission to delete a Stakeholder Characteristic."))
	if not Util.verifyOrganization(config.user) :
		return(render_template('main.html', message="Error: User-Organization mismatch."))
	
	# check if stakeholder to delete exists
	stkc = config.cadr.search_one(type=config.cids.StakeholderCharacteristic, iri=request.form['stkcIRI'])
	if not stkc : return(render_template('main.html', message="Error: Stakeholder Characteristic " + request.form['stkIRI'] + " does not exist."))
	
	stk = stkc.forStakeholder
	hasName = stkc.hasName
	destroy_entity(stk)
	
	Util.logIndividual("Delete Stakeholder Characteristic", stk, stkc, config.impactModel)
	return(render_template('main.html',  message="Deleted Stakeholder Characteristic" + hasName + "."))
	
def render(stkc, action, path, message) :
	priorValue = dict()
	priorValue['stkcIRI'] = stkc.iri if stkc else ""
	priorValue['hasStakeholder'] = stkc.hasStakeholder.iri if stkc and stkc.hasStakeholder else ""
	priorValue['hasSpecification'] = stkc.hasSpecification[0] if stkc and stkc.hasSpecification else ""
	priorValue['hasName'] = stkc.hasName if stkc else ""
	priorValue['hasDescription'] = stkc.hasDescription if stkc else ""
	priorValue['hasIdentifier'] = stkc.hasIdentifier if stkc else ""
	priorValue['codeValue'] = "Yes" if stkc and stkc.codeValue else "No"

	return(render_template('stakeholderCharacteristicEdit.html', action=action, path=path, message=message, priorValue=priorValue))
