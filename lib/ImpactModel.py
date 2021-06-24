# ImpactModel code for CA Repository

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
	if config.user.userType in config.editEnabled : 
		path = "http://localhost:5000/UpdateImpactModel"
		return(render(None, "add", path, config.organization.iri))
		
	return(render_template('main.html', message="Error: User does not have permission to add an ImpactModel."))


def select() :
	action = request.args.get('action')
	
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditImpactModel"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteImpactModel"
	else :
		return(render_template('main.html', message="Error: Unknown ImpactModel action: " + action))
		
	if config.user.userType in config.editEnabled :
		return(render_template('ImpactModelSelect.html', path=path, action=action))
	
	return(render_template('main.html', message="Error: " + config.user.hasEmail + "  does not have permission to edit/display a Stakeholder."))


def edit() :
	action = request.form['action']
	
	path = "http://localhost:5000/UpdateImpactModel"
	
	if (config.user.userType == config.cidsrep.researcher) and (action != 'display') :
		return(render_template('main.html', message="Error: User does not have permission to add/edit/delete a Stakeholder."))
		
	if config.user.userType in config.editEnabled : config.organization = config.user.forOrganization
	
	imIRI = request.form['imIRI']
	if not imIRI : 
		return(render_template('main.html', message="Error: No impact model selected."))
	
	im = config.cadr.search_one(iri=imIRI)
	if not im :
		return(render_template('main.html', message="Error: ImpactModel " + request.form['imIRI'] + " does not exist."))
		
	if ((config.user.userType == config.cidsrep.admin) or (config.user.userType == config.cidsrep.editor)) and (config.user.forOrganization != im.forOrganization) :
		return(render_template('main.html', message="Error: User " + config.user.hasEmail + " and ImpactModel " + request.form['imIRI'] + " organizations do not match."))
	
	return(render(im, action, path, ""))


def update() :
	action = request.form['action']
	
	if action == "add" :
		imType = config.cids.search_one(iri=request.form["imIRI"])
		im = config.cids[imType](namespace=config.cadr)
		im.hasCharacteristics = []
	else :
		im = config.cadr.search_one(iri=request.form['imIRI'])
		if not im :
			return(render_template('main.html', message="Error: editing a missing ImpactModel. " + imIRI))
	
	im.hasName = request.form['hasName']
	im.hasDescription = request.form['hasDescription']
	config.cidsServer.save()
	Util.logIndividual("Update ImpactModel", im)
	return(render(im, "display", readonly, "ImpactModel " + im.hasName + " information saved."))
	
	
def render(im, action, path, message) :
	priorValue = dict()
	hasImpactModelTypeIRI = ""
	impactModelTypes = []
	for imtype in config.cids.search(subclass_of=config.cids.ImpactModel) :
		if imtype != config.cids.ImpactModel : 
			if im and isinstance(im, imtype) : priorValue['impactModelTypeIRI'] = imtype.iri
			impactModelTypes.append(imtype)
	priorValue['hasName'] = im.hasName  if im else ""
	priorValue['hasDescription'] = im.hasDescription if im else ""
	
	print("Impact Model types: ", impactModelTypes)
	print("Desc: ", priorValue['hasDescription'])
	return(render_template('impactModelEdit.html', action=action, path=path, message=message,
		im = im,
		priorValue = priorValue ,
		impactModelTypes = impactModelTypes 
		))
	
	