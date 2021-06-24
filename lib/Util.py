
# File of utility functions for CA Repository
# Creator: Mark S. Fox, msf@eil.utoronto.ca
# Date: 23 January 2021
# Copyright 2021 Mark S. Fox
# Available under: http://creativecommons.org/licenses/by/3.0/

from markupsafe import escape
from owlready2 import *
from rdflib import Graph
import datetime
import json
import config
import logging

def logIndividual(comment, *arg) :
	logchan = open("logs/cadrChanges.log" + str(datetime.date.today()), 'a+')
	for ind in arg :
		if ind : 
			print("logIndividual ", comment, ": IRI=", ind.iri)
			js = cnvIndJSONLD(ind, comment=comment)
			logchan.write("\n\n" + js)
	logchan.close()
#	config.cidsServer.save()	# uncomment when system is ready to really run

def cnvIndJSONLD(ind, comment=None, annotate=True) :
	js = [ ("@id", ind.iri) ]
	for typ in ind.is_a : js.append(("@type", typ.iri))
	for prop in ind.get_properties() : 
		for val in prop[ind] :
			if isinstance(val, owl.Thing) : js.append((str(prop.iri), str(val.iri)))
			else : js.append((str(prop.iri), str(val)))		# need to convert to xsd format
	
	# now convert multiples of same attribute into single attribute with list of values
	jsd = dict()
	for att, val  in js :
		if att in jsd : 
			jsd[att].append(val)
		else :
			jsd[att] = [val]
	
	# if annotate is true then add modification properties
	if annotate :
		jsd["<http://purl.org/dc/terms/modified>"] = [str(datetime.datetime.now())]
		jsd['<http://ontology.eil.utoronto.ca/cids/cids#modifiedBy>'] = [config.user.hasEmail]
		if comment : jsd["<http://purl.org/dc/terms/description"] = [comment]
	
	# should convert to string for printing
	jsonString = '{ "@context : \n { "xsd": "http://www.w3.org/2001/XMLSchema#", \n"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#", \n"rdfs": "http://www.w3.org/2000/01/rdf-schema#" }'
	for att in jsd :
		val = jsd[att]
		jsonString += ' ,\n "' + att + '": '
		if len(val) == 1:
			 jsonString += '"' + val[0] + '"'
		else :
			count = 0
			jsonString += '[ '
			for v in val : 
				jsonString += '"' + v + '"'
				count += 1
				if count < len(val) : jsonString += ' ,'
			jsonString += ' ]'
	jsonString += '\n}'
	
	return(jsonString)

# returns the Organization for the given identifier - handles error if nothing found
def getOrganization(id) :
	global  convLocatedIn
	result = config.cadr.search_one(type=config.org.OrganizationID, hasIdentifier=id)
	if result :
		return(result.forOrganization)
	else :
		return(None)
		
def verifyOrganization(user) :
	if not config.organization : return(False)  # if no organization defined then return False
	if user.userType == config.cidsrep.superuser : return(True)
	if user.userType == config.cidsrep.researcher : return(False)
	return(user.forOrganization == config.organization)


# generate a time interval given a prior interval and start and end dates in YMD format
# ti: timeInterval can be None

def genTimeInterval(ti, std, ed) :
	if ti and not (std and ed) :
		logIndividual("Delete time interval - null sd and ed ", ti)
		delete_entity(ti)
		return(None)
	elif std or ed :
		if not ti :
			ti = config.time.DateTimeInterval(namespace=config.cadr, hasBegining=None, hasEnd=None)
		ti.hasBeginning = convertYMDtoDTD(std, ti.hasBeginning)
		ti.hasEnd = convertYMDtoDTD(ed, ti.hasEnd)
		logIndividual("Update time interval - time", ti, ti.hasBeginning, ti.hasEnd)
		return(ti)
	return(None)
		
# converts owl-time DateTime into yyyy-mm-dd
def convertDTDtoYMD(dte) :
	if not dte or type(dte) != config.time.DateTimeDescription: return("")
	return(dte.year + "-" + dte.month + "-" + dte.day)
	
def convertYMDtoDTD(ymd, dte=None) :
	if not ymd : return(None)
	if not dte : dte = config.time.DateTimeDescription(namespace=config.cadr)
	dte.year, dte.month, dte.day = ymd.split("-")
	return(dte)
	
def allowed_file(filename):
	return(('.' in filename) and (filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS))
	
def printUser(user, header) :
	print("User info in ", header)
	print("givenName=", user.forPerson.givenName)
	print("familyName=", user.forPerson.familyName)
	print("hasEmail=", user.hasEmail)
	print("hasPassword=", user.hasPassword)
	print("hasPhoneNumber=", user.forPerson.hasTelephone[0].hasPhoneNumber)
	print("forOrganization=", user.forOrganization)
	
def ugLog(prin, *arg) :
	"""
	Log arguments and print to console (if specified).

	Parameters
	----------
	prin : bool
		Specifies if arguments should be printed to console.
	*arg : iterable object
		Variable number of arguments to be logged (and printed).
	"""
	pline = ""
	for a in arg : pline += str(a)
	if prin : print(pline)
	logging.info(pline)
	
# ---------------------- Canadian Address Parser ----------------------------
	
# parser for Canadian addresses
# from ez_address_parser import AddressParser
# ap = AddressParser()
# res = ap.parse("21A Howland Ave, Toronto Ontario M5R 3B2")

# ---------------------- Class taxonomy Visualization -----------------------

# from Bio import Phylo
# import io
# import matplotlib.pyplot as plt
# import networkx as nx

# pip install networkx
# pip install Bio
# pip install --pre pygraphviz

#------------------------------ Trees display

"""
from ete3 import Tree, TreeStyle

def displayTaxonomy(obj, fname="render.pdf") :

	# convert hierarchy into a string
	

	t = Tree('((((H,K)D,(F,I)G)B,E)A,((L,(N,Q)O)J,(P,S)M)C);', format=1)
	ts = TreeStyle()
	ts.show_leaf_name = True
	ts.show_branch_length = True
	ts.show_branch_support = True
	t.show(tree_style=ts)
# t.render("render.pdf", units="mm", h=200, tree_style=ts)

	print(tree)
	# tree.ladderize()
	# Phylo.draw(tree)

"""
	
