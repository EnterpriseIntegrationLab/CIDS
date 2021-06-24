# ImpactReport code for CA Repository

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
		return(render_template('impactReportEdit.html', path= "http://localhost:5000/UpdateImpactReport", 
			readonly=ro, action="add", priorValue=dict()))
	
	return(render_template('main.html', message="AddImpactReport Error: User does not have permission to add an Impact Report."))
	

def select() :
	
	action = request.args.get('action')
	
	# check if user is permitted to add an Outcome
	if not config.user.userType in config.reportEnabled:
		return(render_template('main.html', message="Error: User does not have permission to add/edit an Impact Report."))
	
	if not config.impactModel.hasImpactReport and (action in [ "display", "edit", "delete" ]) : 
		return(render_template('main.html', message="Error: No ImpactReports to edit/display."))
		
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditImpactReport"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteImpactReport"
	else :
		return(render_template('main.html', message="Error: Unknown ImpactReport action: " + action))
	
	return(render_template('impactReportSelect.html', path=path, action=action))


def edit() :

	action = request.form['action']
	irIRI = request.form['irIRI']
	
	path = "http://localhost:5000/UpdateImpactReport"
	
	# check if user is permitted to add an Outcome
	if not config.user.userType in config.reportEnabled:
		return(render_template('main.html', message="Error: User does not have permission to add/Edit an Impact Report."))
	
	if not config.organization : return(render_template('main.html', message="Error: Editing organization not defined."))
	
	ro = "readonly" if config.user.userType != config.cids.superuser else ""

	if action in ["edit", "display"] :
		imprep = config.cadr.search_one(iri=irIRI)
		if not imprep : return(render_template('main.html', message="Error: Impact Report does not exist: " + irIRI))
		return(renderImpactReport(imprep, action, path, "ImpactReport " + action + " successful."))
		
	return(render_template("main.html", message="EditImpactReport Error: unknown action."))


def update() :
	
	action = request.form['action']
	irIRI = request.form['irIRI']
	
	# check if user is permitted to add an ImpactReport
	if not config.user.userType in config.reportEnabled:
		return(render_template('main.html', message="Error: User does not have permission to add an ImpactReport."))
	
	if action == 'add' : # create new Outcome
		imprep = config.cids.ImpactReport(namespace=config.cadr)
		imprep.forOrganization = config.organization
		config.impactModel.hasImpactReport.append(imprep)
	else :
		imprep = config.cadr.search_one(iri=irIRI)
		if not imprep : return(render_template('main.html', message="Error: ImpactReport not found in database: " + irIRI))

	imprep.forOutcome = config.cadr.search_one(type=config.cids.Outcome, iri=request.form['forOutcome'])
	imprep.hasExpectation = request.form['hasExpectation']
	imprep.hasComment = request.form['hasComment']
	imprep.hasTimeInterval = Util.genTimeInterval(imprep.hasTimeInterval, std = request.form['hasStartDate'], ed = request.form['hasEndDate'])
		
	# encode scale
	indIRI = request.form['scaleForIndicator']
	print("scale indicator iri: ", indIRI)
	if indIRI and not (indIRI == "None") :
		if not imprep.hasImpactScale : imprep.hasImpactScale = config.cids.ImpactScale(namespace=config.cadr)
		imprep.hasImpactScale.forIndicator = config.cadr.search_one(iri=indIRI)
		imprep.hasImpactScale.hasValue = config.i72.Measure(namespace=config.cadr, hasNumericalValue=request.form['scaleValue'])
		if not imprep.hasImpactScale.hasCounterfactual: imprep.hasImpactScale.hasCounterfactual = config.cids.Counterfactual(namespace=config.cadr)
		imprep.hasImpactScale.hasCounterfactual.hasValue = config.i72.Measure(namespace=config.cadr, hasNumericalValue=request.form['scaleCounterfactualValue'])
		imprep.hasImpactScale.hasCounterfactual.hasDescription = request.form['scaleCounterfactualHasDescription']
		logIndividual("Update ImpactReport scale", imprep.hasImpactScale, imprep.hasImpactScale.hasValue, 
				imprep.hasImpactScale.hasCounterfactual, imprep.hasImpactScale.hasCounterfactual.hasValue)
	elif imprep.hasImpactScale:
		imp = imprep.hasImpactScale
		logIndividual("Update ImpactReport - delete scale", imp)
		delete_entity(imp)

	# encode depth
	indIRI = request.form['depthForIndicator']
	if indIRI and not (indIRI == "None") :
		if not imprep.hasImpactDepth : imprep.hasImpactDepth = config.cids.ImpactDepth(namespace=config.cadr)
		imprep.hasImpactDepth.forIndicator = config.cadr.search_one(iri=indIRI)
		imprep.hasImpactDepth.hasValue = config.i72.Measure(namespace=config.cadr, hasNumericalValue=request.form['depthValue'])
		if not imprep.hasImpactDepth.hasCounterfactual: imprep.hasImpactDepth.hasCounterfactual = config.cids.Counterfactual(namespace=config.cadr)
		imprep.hasImpactDepth.hasCounterfactual.hasValue = config.i72.Measure(namespace=config.cadr, hasNumericalValue=request.form['depthCounterfactualValue'])
		imprep.hasImpactDepth.hasCounterfactual.hasDescription = request.form['depthCounterfactualHasDescription']
		logIndividual("Update ImpactReport depth", imprep.hasImpactDepth, imprep.hasImpactDepth.hasValue, 
			imprep.hasImpactDepth.hasCounterfactual, imprep.hasImpactDepth.hasCounterfactual.hasValue)
	elif imprep.hasImpactDepth :
		imp = imprep.hasImpactDepth
		logIndividual("Update ImpactReport - delete depth", imp)
		delete_entity(imp)
	
	# encode duration
	indIRI = request.form['durationForIndicator']
	if indIRI and not (indIRI == "None") :
		if not imprep.hasImpactDuration : imprep.hasImpactDuration = config.cids.ImpactDuration(namespace=config.cadr)
		impdur = imprep.hasImpactDuration 
		impdur.forIndicator = config.cadr.search_one(iri=indIRI)
		impdur.hasValue = config.i72.Measure(namespace=config.cadr, hasNumericalValue=request.form['durationValue'])
		if not impdur.hasCounterfactual: impdur.hasCounterfactual = config.cids.Counterfactual(namespace=config.cadr)
		impdur.hasCounterfactual.hasValue = config.i72.Measure(namespace=config.cadr, hasNumericalValue=request.form['durationCounterfactualValue'])
		impdur.hasCounterfactual.hasDescription = request.form['durationCounterfactualHasDescription']
		logIndividual("Update ImpactReport duration", impdur, impdur.hasValue, impdur.hasCounterfactual, impdur.hasCounterfactual.hasValue)
		impdur.hasTimeInterval = Util.genTimeInterval(impdur.hasTimeInterval, std = request.form['durationHasStartDate'], ed = request.form['durationHasEndDate'])
	elif imprep.hasImpactDuration :
		imp = imprep.hasImpactDuration
		logIndividual("Update ImpactReport - delete duration", imp)
		delete_entity(imp)
	
	config.cidsServer.save()
	Util.logIndividual("Update ImpactReport", imprep)
	if not imprep in config.impactModel.hasImpactReport :
		config.impactModel.hasImpactReport.append(imprep)
		Util.logIndividual("Update ImpactReport", config.impactModel)
	if not imprep in imprep.forOutcome.hasImpactReport :
		imprep.forOutcome.hasImpactReport.append(imprep)
		Util.logIndividual("Update ImpactReport", config.impactModel.forOutcome)
	

	return(renderImpactReport(imprep, "display", "", "ImpactReport " + action + " successful."))
	

def delete() :
	
	# check if user is permitted to add an Indicator
	if not config.user.userType in config.reportEnabled:
		return(render_template('main.html', message="Error: User does not have permission to delete an Indicator Report."))
	
	ir = config.cadr.search_one(iri=request.form['irIRI'])
	
	if not ir : return(render_template('main.html', message="Error: Delete Impact Report" + request.form['irIRI'] + " does not exist."))
	
	if  (config.user.userType in [config.cidsrep.admin, config.cidsrep.editor]) and (config.user.forOrganization != ir.forOrganization):
		return(render_template('main.html', message="Error: User does not have permission to delete an Impact Report not defined by their Organization."))
	
	hasName = ir.hasName
	logIndividual("Delete Impact Report", ir) # log last version before deleting
	destroy_entity(ir)
	return(render_template('main.html',  message="Deleted Impact Report: " + hasName))
	
def renderImpactReport(imprep, action, path, message) :
	
	priorValue = dict()
	priorValue['irIRI'] = imprep.iri if imprep else ""
	priorValue['hasName'] = imprep.hasName if imprep else ""
	priorValue['forOutcome'] = imprep.forOutcome.iri if imprep else None
	priorValue['hasExpectation'] = imprep.hasExpectation if imprep else ""
	ti = imprep.hasTimeInterval
	priorValue['hasStartDate'] = convertDTDtoYMD(imprep.hasTimeInterval.hasBeginning) if ti else ""
	priorValue['hasEndDate'] = convertDTDtoYMD(imprep.hasTimeInterval.hasEnd) if ti else ""
	priorValue['hasComment']= imprep.hasComment
	
	priorValue['scaleForIndicator'] = imprep.hasImpactScale.forIndicator.iri if imprep.hasImpactScale and imprep.hasImpactScale.forIndicator else ""
	priorValue['scaleValue'] = imprep.hasImpactScale.hasValue.hasNumericalValue if imprep.hasImpactScale and imprep.hasImpactScale.hasValue else ""
	priorValue['scaleCounterfactualValue'] = imprep.hasImpactScale.hasCounterfactual.hasValue.hasNumericalValue if imprep.hasImpactScale and imprep.hasImpactScale.hasCounterfactual else ""
	priorValue['scaleCounterfactualHasDescription'] = imprep.hasImpactScale.hasCounterfactual.hasDescription if imprep.hasImpactScale and imprep.hasImpactScale.hasCounterfactual else ""
	
	priorValue['depthForIndicator'] = imprep.hasImpactDepth.forIndicator.iri if imprep.hasImpactDepth and imprep.hasImpactDepth.forIndicator else ""
	priorValue['depthValue'] = imprep.hasImpactDepth.hasValue.hasNumericalValue if imprep.hasImpactDepth and imprep.hasImpactDepth.hasValue else ""
	priorValue['depthCounterfactualValue'] = imprep.hasImpactDepth.hasCounterfactual.hasValue.hasNumericalValue if imprep.hasImpactDepth and imprep.hasImpactDepth.hasCounterfactual else ""
	priorValue['depthCounterfactualHasDescription'] = imprep.hasImpactDepth.hasCounterfactual.hasDescription if imprep.hasImpactDepth and imprep.hasImpactDepth.hasCounterfactual else ""
	
	priorValue['durationForIndicator'] = imprep.hasImpactDuration.forIndicator.iri if imprep.hasImpactDuration and imprep.hasImpactDuration.forIndicator else ""
	priorValue['durationValue'] = imprep.hasImpactDuration.hasValue.hasNumericalValue if imprep.hasImpactDuration and imprep.hasImpactDuration.hasValue else ""
	priorValue['durationCounterfactualValue'] = imprep.hasImpactDuration.hasCounterfactual.hasValue.hasNumericalValue if imprep.hasImpactDuration and imprep.hasImpactDuration.hasCounterfactual else ""
	priorValue['durationCounterfactualHasDescription'] = imprep.hasImpactDuration.hasCounterfactual.hasDescription if imprep.hasImpactDuration and imprep.hasImpactDuration.hasCounterfactual else ""
	ti = imprep.hasImpactDuration.hasTimeInterval if imprep.hasImpactDuration and imprep.hasImpactDuration.hasTimeInterval else None
	priorValue['durationHasStartDate'] = convertDTDtoYMD(imprep.hasImpactDuration.hasTimeInterval.hasBeginning) if ti else ""
	priorValue['durationHasEndDate'] = convertDTDtoYMD(imprep.hasImpactDuration.hasTimeInterval.hasEnd) if ti else ""
	
	return(render_template("impactReportEdit.html", path=path, action=action, message=message , priorValue=priorValue))

