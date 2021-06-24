# Outcome code for CA Repository

# Creator: Mark S. Fox, msf@eil.utoronto.ca
# Date: 23 January 2021
# Copyright 2021 Mark S. Fox
# Available under: http://creativecommons.org/licenses/by/3.0/

import config
import datetime
from owlready2 import *
from flask import Flask, render_template, request, session, redirect, url_for, g, flash
import Util
import ImpactModel

def add() :

	if not Util.verifyOrganization(config.user) :
		return(render_template('main.html', message="Error: User-Organization mismatch."))
		
	if  not config.user.userType in config.editEnabled : 
		return(render_template('main.html', message="AddOutcome Error: User does not have permission to add an Outcome."))
	
	path = "http://localhost:5000/UpdateOutcome"

	return(render(None, "add", path, ""))	
	

def select() :
	action = request.args.get('action')
	
	# check if user and organization match
	if not Util.verifyOrganization(config.user) :
		return(render_template('main.html', message="Error: User-Organization mismatch."))
	
	# check if user is permitted to add an Outcome
	if not config.user.userType in config.editEnabled:
		return(render_template('main.html', message="Error: User does not have permission to add an Outcome."))
	
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditOutcome"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteOutcome"
	elif action == "compare" :
		path = "http://localhost:5000/SimilarOutcome"
	else :
		return(render_template('main.html', message="Error: Unknown Outcome action: " + action))
	
	if not config.impactModel.hasOutcome : return(render_template('main.html', message="Error: No Outcomes for the Impact Model to select from."))
	
	return(render_template('outcomeSelect.html', path=path, action=action))


def edit() :

	if request.method == 'POST':
		action = request.form['action']
		outIRI = request.form['outIRI']
	else :
		action = "display"
		outIRI = request.args.get('outIRI')
	
	path = "http://localhost:5000/UpdateOutcome"
	
	# check if user and organization match
	if not Util.verifyOrganization(config.user) :
		return(render_template('main.html', message="Error: User-Organization mismatch."))
		
	# check if user is permitted to add an Outcome
	if not config.user.userType in config.editEnabled:
		return(render_template('main.html', message="Error: User does not have permission to add/Edit an Outcome."))
	
	ro = "readonly" if config.user.userType != config.cids.superuser else ""

	if not action in ["edit", "display"] : return(render_template("main.html", message="EditOutcome Error: unknown action."))
	
	out = config.cadr.search_one(type=config.cids.Outcome, iri=request.form["outIRI"])
	if not out : return(render_template('main.html', message="Error: Outcome does not exist: " + request.form["outIRI"]))
		
	return(render(out, action, path, ""))


def update() :
	action = request.form['action']
	
	# check if user and organization match
	if not Util.verifyOrganization(config.user) :
		return(render_template('main.html', message="Error: User-Organization mismatch."))
	
	# check if user is permitted to add an Outcome
	if not config.user.userType in config.editEnabled:
		return(render_template('main.html', message="Error: User does not have permission to add an Outcome."))
	
	# check if Outcome already exists for the org and doing add
	if (request.form['action'] == 'add')  :
		if config.cadr.search_one(type=config.cids.Outcome, hasName=request.form['hasName'], forOrganization=config.organization) :
			return(render_template('main.html', message="Error: Outcome with that name already exists."))
		# create new Outcome
		out = config.cids.Outcome(namespace=config.cadr, hasStakeholderOutcome = [], forDomain=[], hasImpactRisk=[], canProduce=[])
		out.definedBy = config.organization
		config.impactModel.hasOutcome.append(out)
	elif (request.form['action'] == 'edit') :
		out = config.cadr.search_one(type=config.cids.Outcome, iri=request.form['outIRI'])
		if not out : return(render_template('main.html', message="Error: Outcome not found in database."))
	else :
		return(render_template('main.html', message="Error: Unknown action."))

	out.hasName = request.form['hasName']
	out.hasDescription = request.form['hasDescription']
	
	doms = []
	for domiri in request.form.getlist('forDomain') :
		dom = config.cidsrep.search_one(type=config.cids.Domain, iri=domiri)
		if dom : doms.append(dom)
	out.forDomain = doms

	# UPDATE STAKEHOLDER IMPACTs ---------------
	
	# cycle through each of the stakeholders
	names = []
	count = 0
	previousStos = out.hasStakeholderOutcome
	newstos = []   # this list will replace the outcome's previous list incase of deletions
	
	for stakeholder in config.impactModel.hasStakeholder :
		count += 1
		stk = "forStakeholder" + str(count)
		ser = "ser" + str(count)
		imp = "imp" + str(count)
		if request.form[stk] :
			stk = config.cadr.search_one(type=config.cids.Stakeholder, iri=request.form[stk])
			sto = retrieveStakeholderOutcome(out, stk)
			sto.forStakeholder = stk
			sto.hasImportance = request.form[imp]
			sto.isUnderserved = True if request.form[ser] == "Yes" else False
			newstos.append(sto)
			Util.logIndividual("Update Outcome", sto)
	out.hasStakeholderOutcome = newstos
	for sto in previousStos : 
		if not sto in out.hasStakeholderOutcome : 
			Util.logIndividual("Update Outcome - delete stakeholderOutcome", sto)
			destroy_entity(sto)

	for riskType, riskl, rdes in config.risks :
		r = findRisk(out, riskType)
		if request.form[riskl] :
			if not r : 
				r = riskType(namespace=config.cadr)
				if out.hasImpactRisk :
					out.hasImpactRisk.append(r)
				else :
					out.hasImpactRisk = [r]
			r.hasLikelihood = request.form[riskl]
			r.hasDescription = request.form[rdes]
			r.forOutcome = out
			Util.logIndividual("Update Outcome", r)
		else : 
			if r : 
				Util.logIndividual("Update Outcome - destroyed ", r)
				destroy_entity(r)
	
	Util.logIndividual("Update Outcome", out)
	return(render(out, "display", "", "Outcome " + action + " successful."))
	
def render(outcome, action, path, message) :
	if not config.impactModel.hasStakeholder : 
		return(ImpactModel.render(config.impactModel, "display", None, "Error: No Stakeholders defined for this Organization."))
		
	priorValue = dict()
	outIRI = outcome.iri if outcome else ""
	# dynamically generate the list of domains and stakeholders for the pull down list
	domains = genDomains() # list all domains
	selectedDomains = [dom.iri for dom in outcome.forDomain] if outcome else [] # identified domains that were selected
	stknames = genStakeholders(outcome)
	priorValue['hasName'] = outcome.hasName  if outcome else ""
	priorValue['hasDescription'] = outcome.hasDescription if outcome else ""
	
	# set the prior values for each of the risk types	
	for risk, riskLikelihood, riskDescription in config.risks :
		priorValue[riskLikelihood], priorValue[riskDescription] = getRiskValue(outcome, risk) if outcome else ("", "")
	
	return(render_template("outcomeEdit.html", outIRI=outIRI, path=path, action=action,
		domains=domains, selectedDomains=selectedDomains, stknames = stknames,
		message=message , risks=config.risks, priorValue=priorValue ))

# retrieve stakeholderoutcome finds the existing stout, if it exists, otherwise creates it
def retrieveStakeholderOutcome(outcome, stk) :
	for sto in outcome.hasStakeholderOutcome :
		if sto.forStakeholder == stk :
			return(sto)
	return(config.cids.StakeholderOutcome(namespace=config.cadr, hasImpactReport=[], isUnderserved=None, intendedImpact="", hasIndicator=[], hasImportance="", fromPerspectiveOf = None, forStakeholder=None))

	
def findRisk(outcome, riskType) :
	for r in outcome.hasImpactRisk :
		if type(r) == riskType: return(r)
	return(None)
	
# get risk value returns the values for an outcome's risk
def getRiskValue(outcome, riskType) :
	for risk in outcome.hasImpactRisk :
		if type(risk) == riskType : return (risk.hasLikelihood, risk.hasDescription)
	return("", "")
	
# generate the list of domains for outcomeEdit.html
def genDomains():
	domains =[]
	for dom in config.cidsrep.search(type=config.cidsrep.UNSDGDomain) : domains.append((dom.iri, dom.description[0]))
	return(domains)
	
# generate list of stakeholders for outcomeEdit.html
def genStakeholders(outcome) :

	stknames = []
	count = 0
	stouts = outcome.hasStakeholderOutcome if outcome else []
	for stk in config.impactModel.hasStakeholder :
		count += 1
		nosto = True
		for sto in stouts :		# cycle through stakeholderOutcomes to see if one exists already
			if stk == sto.forStakeholder :
				stknameIri = stk.iri
				impVal = sto.hasImportance
				serVal = "Yes" if sto.isUnderserved else "No"
				nosto = False
				break
		if nosto :
			stknameIri = ""
			impVal = ""
			serVal = ""
		stknames.append(("forStakeholder" + str(count), stknameIri, "imp" + str(count), impVal, "ser" + str(count), serVal))
	return(stknames)