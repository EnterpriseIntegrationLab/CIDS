# IndicatorReport code for CA Repository

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

	ro = "readonly" if config.user.userType != config.cidsrep.superuser else ""

	if config.user.userType in config.reportEnabled : 
		return(render(None, "add", "http://localhost:5000/UpdateIndicatorReport", ""))
	
	return(render_template('main.html', message="AddImpactReport Error: User does not have permission to add an Impact Report."))
	

def select() :
	
	action = request.args.get('action')
	
	# check if user is permitted to add an Outcome
	if not config.user.userType in config.reportEnabled:
		return(render_template('main.html', message="Error: User does not have permission to add/edit an Indicator Report."))
	
	if not config.impactModel.hasIndicatorReport and (action in [ "display", "edit", "delete" ]) : 
		return(render_template('main.html', message="Error: No IndicatorReports to edit/display."))
		
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditIndicatorReport"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteIndicatorReport"
	else :
		return(render_template('main.html', message="Error: Unknown IndicatorReport action: " + action))
	
	return(render_template('indicatorReportSelect.html', path=path, action=action))
	

def edit() :

	action = request.form['action']
	irIRI = request.form['irIRI']
	path = "http://localhost:5000/UpdateIndicatorReport"
	
	# check if user is permitted to add an Indicator Report
	if not config.user.userType in config.reportEnabled:
		return(render_template('main.html', message="Error: User does not have permission to add/Edit an Indicator Report."))
	
	if not config.organization : return(render_template('main.html', message="Error: Editing organization not defined."))
	
	ro = "readonly" if config.user.userType != config.cids.superuser else ""

	if action in ["edit", "display"] :
		indrep = config.cadr.search_one(type=config.cids.IndicatorReport, iri=irIRI)
		if not indrep : return(render_template('main.html', message="Error: Indicator Report does not exist: " + irIRI))
		return(render(indrep, action, path, ""))
		
	return(render_template("main.html", message="EditImpactReport Error: unknown action."))


def update() :
	
	action = request.form['action']
	irIRI = request.form['irIRI']
	
	# check if user is permitted to add an ImpactReport
	if not config.user.userType in config.reportEnabled:
		return(render_template('main.html', message="Error: User does not have permission to add/edit an Indicator Report."))
	
	if action == 'add' : # create new Outcome
		indrep = config.cids.IndicatorReport(namespace=config.cadr)
		indrep.forOrganization = config.organization
		config.impactModel.hasIndicatorReport.append(indrep)
	else :
		indrep = config.cadr.search_one(type=config.cids.IndicatorReport, iri=irIRI)
		if not indrep : return(render_template('main.html', message="Error: IndicatorReport not found in database: " + irIRI))

	indrep.hasName = request.form['hasName']
	indrep.forIndicator = config.cadr.search_one(type=config.cids.Indicator, iri=request.form['forIndicator'])
	indrep.hasValue = config.i72.Measure(namespace=config.cadr, hasNumericalValue=request.form['hasValue'])
	indrep.hasTimeInterval = Util.genTimeInterval(indrep.hasTimeInterval, std = request.form['hasStartDate'], ed = request.form['hasEndDate'])
	indrep.hasComment = request.form['hasComment']
	Util.logIndividual("Update IndicatorReport", indrep)

	return(render(indrep, "display", None, "Indicator Report Created/Updated"))


def delete() :
	
	# check if user is permitted to add an Indicator
	if not config.user.userType in config.reportEnabled:
		return(render_template('main.html', message="Error: User does not have permission to delete an Indicator Report."))
	
	ir = config.cadr.search_one(iri=request.form['irIRI'])
	
	if not ir : return(render_template('main.html', message="Error: Delete Indicator Report" + request.form['irIRI'] + " does not exist."))
	
	if  (config.user.userType in [config.cidsrep.admin, config.cidsrep.editor]) and (config.user.forOrganization != ir.forOrganization):
		return(render_template('main.html', message="Error: User does not have permission to delete an Indicator Report not defined by their Organization."))
	
	hasName = ir.hasName
	Util.logIndividual("Delete Indicator Report", ir) # log last version before deleting
	destroy_entity(ir)
	return(render_template('main.html',  message="Deleted Indicator Report: " + hasName))

def render(indrep, action, path, message) :
	
	if len(config.impactModel.hasIndicator) == 0: 
		return(render_template('main.html', message="Error: Impact Model does not have Indicators to report on."))
	
	priorValue = dict()
	priorValue['irIRI'] = indrep.iri if indrep else ""
	priorValue['hasName'] = indrep.hasName if indrep else ""
	priorValue['forIndicator'] = indrep.forIndicator.iri if indrep else ""
	priorValue['hasValue'] = indrep.hasValue.hasNumericalValue if indrep else ""
	priorValue['hasStartDate'] = Util.convertDTDtoYMD(indrep.hasTimeInterval.hasBeginning) if indrep  and indrep.hasValue else ""
	priorValue['hasEndDate'] = Util.convertDTDtoYMD(indrep.hasTimeInterval.hasEnd) if indrep  and indrep.hasValue else ""
	priorValue['hasComment'] = indrep.hasComment if indrep else ""

	return(render_template("indicatorReportEdit.html", path=path, action=action, message=message , priorValue=priorValue))