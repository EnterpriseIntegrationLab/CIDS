# Indicator code for CA Repository

# Creator: Mark S. Fox, msf@eil.utoronto.ca
# Date: 26 January 2021
# Copyright 2021 Mark S. Fox
# Available under: http://creativecommons.org/licenses/by/3.0/

import config
import datetime
from owlready2 import *
from flask import Flask, render_template, request, session, redirect, url_for, g, flash
import Util
import Analysis


def add() :
	path = "http://localhost:5000/UpdateIndicator"
	if not Util.verifyOrganization(config.user) : 
		return(render_template('main.html', message="Error: User does not have access to organization."))
	
	if  not config.user.userType in config.editEnabled :
		return(render_template('main.html', message="Error: User does not have permission to add an Indicator."))
	
	return(render(None, "add", path, ""))
	

def select() :
	action = request.args.get('action')
	
	# check if user is permitted to add an Indicator
	if not Util.verifyOrganization(config.user) : 
		return(render_template('main.html', message="Error: User does not have access to organization."))
	
	if  not config.user.userType in config.editEnabled :
		return(render_template('main.html', message="Error: User does not have permission to add/edit/delete an Indicator."))
	
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditIndicator"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteIndicator"
	elif action == "compare" :
		path = "http://localhost:5000/SimilarIndicator"
	else :
		return(render_template('main.html', message="Error: Unknown Indicator action: " + action))
	
	inds = config.cadr.search(type=config.cids.Indicator, definedBy=config.organization) if config.organization else []
	
	if not inds and (action == "display"): return(render_template('main.html', message="Error: No indicators to display."))
	indSelect = dict()
	for ind in inds: indSelect[ind.iri] = ind.hasName
	
	return(render_template('indicatorSelect.html', action=action, path=path))


def edit() :

	if request.method == 'POST':
		action = request.form['action']
		indIRI = request.form['indIRI']
	else :
		action = "display"
		indIRI = request.args.get('indIRI')
	ind = None
	path = "http://localhost:5000/UpdateIndicator"
	
	# check if user is permitted to add an Indicator
	if not Util.verifyOrganization(config.user) : 
		return(render_template('main.html', message="Error: User does not have access to organization."))
		
	if not config.user.userType in config.editEnabled :
		return(render_template('main.html', message="Error: User does not have permission to add/edit/delete an Indicator."))
	
	if action != "add" :
		ind = config.cadr.search_one(type=config.cids.Indicator, iri=indIRI)
		if not ind : return(render_template('main.html', message="Error: Edit Indicator " + indIRI + " does not exist."))
	
	return(render(ind, action, path, ""))


def update() :
	action = request.form['action']
	indIRI = request.form['indIRI']
		
	# check if user is permitted to add an Indicator
	if not Util.verifyOrganization(config.user) : 
		return(render_template('main.html', message="Error: User does not have access to organization."))	
	if not config.user.userType in config.editEnabled :
		return(render_template('main.html', message="Error: User does not have permission to add/edit/delete an Indicator."))
	
	if action == 'add' : # create new Indicator
		if config.cadr.search_one(type=config.cids.Indicator, hasName=request.form['hasName']) :
			return(render_template('main.html', message="Error: Indicator with this name already exists"))
		ind = config.cids.Indicator(namespace=config.cadr)
		ind.definedBy = config.organization
		config.impactModel.hasIndicator.append(ind)
	elif action == "edit" :
		ind = config.cadr.search_one(type=config.cids.Indicator, iri=indIRI)
		if not ind : return(render_template('main.html', message="Error: Indicator not found: " + indIRI))
		
	ind.hasName = request.form['hasName']
	ind.hasDescription = request.form['hasDescription']
	ind.hasBaseline = config.i72.Measure(namespace=config.cadr, hasNumercalValue=request.form['hasBaseline'], hasUnit=None)
	ind.hasThreshold = config.i72.Measure(namespace=config.cadr, hasNumercalValue=request.form['hasThreshold'], hasUnit=None)
	
	# define the optional standard
	message = ""
	if request.form['stOrgID'] :
		storgID = config.cadr.search_one(type=config.org.OrganizationID, hasIdentifier=request.form['stOrgID'])
		if storgID : 
			st = ind.hasIndicatorStandard = ind.hasIndicatorStandard if ind.hasIndicatorStandard else config.cids.IndicatorStandard(namespace=config.cadr)
			st.forOrganization = storgID.forOrganization
			st.hasIdentifier = request.form['stHasIdentifier']
			Util.logIndividual("Update Indicator", st)
		else :
			message="Error: Standards Organization ID does not exist."
		
	Util.logIndividual("Update Indicator", ind, ind.hasBaseline, ind.hasThreshold )
	return(render(ind, "display", None, message))


def delete() :
	action = request.form['action']
	indIRI = request.form['indIRI']
		
	# check if user is permitted to add an Indicator
	if not Util.verifyOrganization(config.user) : 
		return(render_template('main.html', message="Error: User does not have access to organization."))	
	if not config.user.userType in config.editEnabled :
		return(render_template('main.html', message="Error: User does not have permission to add/edit/delete an Indicator."))
	if action != "delete" :
		return(render_template('main.html', message="Error: Incorrect action"))
	
	ind = config.cadr.search_one(type=config.cids.Indicator, iri=indIRI)
	if not ind : return(render_template('main.html', message="Error: Delete Indicator " + indIRI + " does not exist."))
	
	Util.logIndividual("Delete Indicator", ind)
	destroy_entity(ind)
	return(render_template('main.html',  message="Deleted Indicator " + request.form['indIRI'] + "."))

	
def render(ind, action, path, message) :
	priorValue = dict()
	priorValue['indIRI'] = ind.iri if ind else ""
	priorValue['hasName'] = ind.hasName if ind else ""
	priorValue['hasDescription'] = ind.hasDescription if ind else ""
	priorValue['located_in'] = ind.located_in if ind else ""
	priorValue['hasBaseline'] = ind.hasBaseline.hasNumercalValue if ind and ind.hasBaseline else ""
	priorValue['hasThreshold'] = ind.hasThreshold.hasNumercalValue if ind and ind.hasThreshold else ""
	priorValue['stOrgID'] = ind.hasIndicatorStandard.forOrganization.hasID.hasIdentifier if ind and ind.hasIndicatorStandard and ind.hasIndicatorStandard.forOrganization  and ind.hasIndicatorStandard.forOrganization.hasID else ""
	priorValue['stHasIdentifier'] = ind.hasIndicatorStandard.hasIdentifier if ind and ind.hasIndicatorStandard else ""
		
	return(render_template("indicatorEdit.html", action=action, path=path, priorValue=priorValue, message=message))

def oldsimilarIndicator() :
	inds = config.cadr.search(type=config.cids.Indicator, definedBy=config.organization)
	indSelect = dict()
	for ind in inds: indSelect[ind.iri] = ind.hasName
	return(render_template('indicatorSelect.html', indicators=indSelect, action="compare", path="http://localhost:5000/FindSimilarIndicator"))
	

def findSimilar() :

	if request.form["indIRI"] :
		queryIndicator = config.cadr.search_one(type=config.cids.Indicator, iri=request.form["indIRI"])
		queryDescription = queryIndicator.hasDescription
		mess = str(queryIndicator) + "; " + queryDescription
	elif request.form["hasDescription"] :
		queryDescription = request.form["hasDescription"]
		mess = ""
	else :
		return(render_template('main.html', message="no indicator or description provided."))
		
	result = Analysis.distance(queryDescription, config.cids.Indicator)
	resultTable = []
	for ind, dist in result: resultTable.append((ind.hasName, ind.iri, ind.hasDescription, dist))
	
	return(render_template('displayDistance.html', result=resultTable, query=queryDescription, message=mess))
	
