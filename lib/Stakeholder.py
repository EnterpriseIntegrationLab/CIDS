# Stakeholder code for CA Repository

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
	if not config.user.userType in config.editEnabled : 
		return(render_template('main.html', message="Error: User does not have permission to add a Stakeholder."))
		
	path = "http://localhost:5000/UpdateStakeholder"
	return(render(None, "add", path, ""))


def select() :
	action = request.args.get('action')
	
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditStakeholder"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteStakeholder"
	else :
		return(render_template('main.html', message="Error: Unknown Stakeholder action: " + action))
		
	if not config.user.userType in config.editEnabled :
		return(render_template('main.html', message="Error: " + config.user.hasEmail + "  does not have permission to edit/display a Stakeholder."))
	
	stakeholders = config.cadr.search(type=config.cids.Stakeholder, forOrganization=config.organization)
	if not stakeholders :
		return(render_template('main.html', message="Error: No stakeholders defined for this organization."))
		
	return(render_template('stakeholderSelect.html', path=path, stakeholders=stakeholders, action=action))
	

def edit() :
	if request.method == 'POST':
		action = request.form['action']
		stkIRI = request.form['stkIRI']
	else :
		action = "display"
		stkIRI = request.args.get('stkIRI')
	
	path = "http://localhost:5000/UpdateStakeholder"
	
	if not Util.verifyOrganization(config.user) :
		return(render_template('main.html', message="Error: User-Organization mismatch."))
	
	if (not config.user.userType in config.editEnabled) and (action != 'display') :
		return(render_template('main.html', message="Error: User does not have permission to add/edit a Stakeholder."))

	stk = config.cadr.search_one(type=config.cids.Stakeholder, iri=stkIRI)
	if not stk :
		return(render_template('main.html', message="Error: Stakeholder " + request.form['stkIRI'] + " does not exist."))

	return(render(stk, action, path, ""))


def update() :
	action = request.form['action']
	
	# check if user is permitted to add a Stakeholder
	if not config.user.userType  in config.editEnabled:
		return(render_template('main.html', message="Error: User does not have permission to add/update a Stakeholder."))
	if not Util.verifyOrganization(config.user) :
		return(render_template('main.html', message="Error: User-Organization mismatch."))
	
	# check if stakeholder already exists for the org and doing add
	if request.form['action'] == 'add' :
		stk = config.cadr.search_one(type=config.cids.Stakeholder, hasName=request.form['hasName'], forOrganization=config.organization)
		if stk : return(render_template('main.html', message="Error: Stakeholder with that name already exists."))
		stk = config.cids.Stakeholder(namespace=config.cadr)
		stk.hasName = request.form['hasName']
		stk.hasStakeholderCharacteristics = []
		stk.forOrganization = config.organization
		config.impactModel.hasStakeholder.append(stk)
	elif action == 'edit' :
		stk = config.cadr.search_one(type=config.cids.Stakeholder, iri=request.form['stkIRI'])
		if not stk :return(render_template('main.html', message="Error: Stakeholder not found in database."))
	else :
		return(render_template('main.html', message="Error: Illegal action: " + action))
			
	stk.hasDescription = request.form['hasDescription']
	stk.located_in = [config.convLocatedIn[request.form['located_in']]]
		
	Util.logIndividual("Update Stakeholder", stk, config.impactModel)
	return(render(stk, "display", "", " Stakeholder " + action + " successful."))


def delete() :
	# check if user is permitted to delete stakeholder
	if not config.user.userType in config.editEnabled :
		return(render_template('main.html', message="Error: User does not have permission to delete a Stakeholder."))
	if not Util.verifyOrganization(config.user) :
		return(render_template('main.html', message="Error: User-Organization mismatch."))
	
	# check if stakeholder to delete exists
	stk = config.cadr.search_one(type=config.cids.Stakeholder, iri=request.form['stkIRI'])
	if not stk : return(render_template('main.html', message="Error: Stakeholder " + request.form['stkIRI'] + " does not exist."))
	
	Util.logIndividual("Delete Stakeholder", stk)
	hasName = stk.hasName
	destroy_entity(stk)
	return(render_template('main.html',  message="Deleted Stakeholder " + hasName + "."))
	
def render(stk, action, path, message) :
	priorValue = dict()
	priorValue['stkIRI'] = stk.iri if stk else ""
	priorValue['hasName'] = stk.hasName if stk else ""
	priorValue['hasDescription'] = stk.hasDescription if stk else ""
	priorValue['located_in'] = stk.located_in[0].has_Name if stk and stk.located_in else ""
	return(render_template('stakeholderEdit.html', action=action, path=path, message=message, priorValue=priorValue))
