# Version 2 of CA Repository - restructured code

# Creator: Mark S. Fox, msf@eil.utoronto.ca
# Date: 23 January 2021
# Copyright 2021 Mark S. Fox
# Available under: http://creativecommons.org/licenses/by/3.0/

import sys
sys.path.insert(0, './lib')

from flask import Flask, render_template, request, session, redirect, url_for, g, flash

from werkzeug.utils import secure_filename
import os

import datetime
import json
# from pyld import jsonld

from markupsafe import escape
from owlready2 import *
from rdflib import Graph

# modules for measuring distance between text in Indicators
import gensim
import numpy as np
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize

import config
import Util

CARepository = Flask(__name__)


# ------------------------------ Login/logout/Save/logging -------------------------------
import Login

@CARepository.route('/', methods=['GET'])
def index() : return(Login.index())
	
@CARepository.route('/Login', methods=['POST'])
def login() : return(Login.login())

@CARepository.route('/Logout')
def logout(): return(Login.logout())

@CARepository.route('/DumpInstances')
def saveCADR() : return(Login.saveCADR())


#--------------- User --------------------------------------------------------------------
import User

@CARepository.route('/AddUser')
def addUser() : return(User.add())

@CARepository.route('/SelectUser', methods=['GET'])
def selectUser() : return(User.select())

@CARepository.route('/EditUser', methods=['POST'])
def editUser() : return(User.edit())
	
@CARepository.route('/UpdateUser', methods=['POST'])
def updateUser() : return(User.update())
	
@CARepository.route('/DeleteUser', methods=['POST'])
def deleteUser() : return(User.delete())
				
	
# -------------------- Organization -------------------------------------------------------
import Organization

@CARepository.route('/AddOrganization', methods=['GET'])
def addOrganization() : return(Organization.add())

@CARepository.route('/SelectOrganization', methods=['GET'])
def selectOrganization() : return(Organization.select())

@CARepository.route('/EditOrganization', methods=['POST', 'GET'])
def editOrganization() : return(Organization.edit())
	
@CARepository.route('/UpdateOrganization', methods=['POST'])
def updateOrganization() : return(Organization.update())
	
@CARepository.route('/DeleteOrganization', methods=['POST'])
def deleteOrganization() : return(Organization.delete())

#--------------- ImpactModel -------------------------------------------------------------
import ImpactModel

@CARepository.route('/AddImpactModel', methods=['GET'])
def addImpactModel() : return(ImpactModel.add())

@CARepository.route('/SelectImpactModel', methods=['GET'])
def selectImpactModel() : return(ImpactModel.select())

@CARepository.route('/EditImpactModel', methods=['POST'])
def editImpactModel() : return(ImpactModel.edit())

@CARepository.route('/UpdateImpactModel', methods=['POST'])
def updateImpactModel() : return(ImpactModel.update())
	

#--------------- Stakeholder -------------------------------------------------------------
import Stakeholder

@CARepository.route('/AddStakeholder')
def addStakeholder() : return(Stakeholder.add())

@CARepository.route('/SelectStakeholder', methods=['GET'])
def selectStakeholder() : return(Stakeholder.select())

@CARepository.route('/EditStakeholder', methods=['POST', 'GET'])
def editStakeholder() : return(Stakeholder.edit())

@CARepository.route('/UpdateStakeholder', methods=['POST'])
def updateStakeholder() : return(Stakeholder.update())

@CARepository.route('/DeleteStakeholder', methods=['POST'])
def deleteStakeholder() : return(Stakeholder.delete())

#--------------- Stakeholder Characteristics ---------------------------------------------
import StakeholderCharacteristic

@CARepository.route('/AddStakeholderCharacteristic')
def addStakeholderCharacteristic() : return(StakeholderCharacteristic.add())

@CARepository.route('/SelectStakeholderCharacteristic', methods=['GET'])
def selectStakeholderCharacteristic() : return(StakeholderCharacteristic.select())

@CARepository.route('/EditStakeholderCharacteristic', methods=['POST', 'GET'])
def editStakeholderCharacteristic() : return(StakeholderCharacteristic.edit())

@CARepository.route('/UpdateStakeholderCharacteristic', methods=['POST'])
def updateStakeholderCharacteristic() : return(StakeholderCharacteristic.update())

@CARepository.route('/DeleteStakeholderCharacteristic', methods=['POST'])
def deleteStakeholderCharacteristic() : return(StakeholderCharacteristic.delete())

#--------------- Indicator  -------------------------------------------------------------
import Indicator

@CARepository.route('/AddIndicator', methods=['GET'])
def addIndicator() : return(Indicator.add())

@CARepository.route('/SelectIndicator', methods=['GET'])
def selectIndicator() : return(Indicator.select())

@CARepository.route('/EditIndicator', methods=['POST', 'GET'])
def editIndicator() : return(Indicator.edit())

@CARepository.route('/UpdateIndicator', methods=['POST'])
def updateIndicator() : return(Indicator.update())

@CARepository.route('/DeleteIndicator', methods=['POST'])
def deleteIndicator() : return(Indicator.delete())

@CARepository.route('/SimilarIndicator', methods=['GET'])
def oldsimilarIndicator() : return(Indicator.oldsimilarIndicator())

@CARepository.route('/FindSimilarIndicator', methods=['POST'])
def findSimilarIndicator() : return(Indicator.findSimilar())

#--------------- Outcome  -------------------------------------------------------------
import Outcome

@CARepository.route('/AddOutcome')
def addOutcome() : return(Outcome.add())
	
@CARepository.route('/SelectOutcome', methods=['GET'])
def selectOutcome() : return(Outcome.select())

@CARepository.route('/EditOutcome', methods=['POST', 'GET'])
def editOutcome() : return(Outcome.edit())

@CARepository.route('/UpdateOutcome', methods=['POST'])
def updateOutcome() : return(Outcome.update())

@CARepository.route('/EditOutcome', methods=['POST'])
def deleteOutcome() : return(Outcome.delete())


#--------------- Impact Report  -------------------------------------------------------------
import ImpactReport

@CARepository.route('/AddImpactReport')
def addImpactReport() : return(ImpactReport.add())
	
@CARepository.route('/SelectImpactReport', methods=['GET'])
def selectImpactReport() : return(ImpactReport.select())

@CARepository.route('/EditImpactReport', methods=['POST'])
def editImpactReport() : return(ImpactReport.edit())

@CARepository.route('/UpdateImpactReport', methods=['POST'])
def updateImpactReport() : return(ImpactReport.update())
	
@CARepository.route('/DeleteImpactReport', methods=['POST'])
def deleteImpactReport() : return(ImpactReport.delete())


#--------------- Indicator Report  -------------------------------------------------------------
import IndicatorReport

@CARepository.route('/AddIndicatorReport')
def addIndicatorReport() : return(IndicatorReport.add())
	
@CARepository.route('/SelectIndicatorReport', methods=['GET'])
def selectIndicatorReport() : return(IndicatorReport.select())
	
@CARepository.route('/EditIndicatorReport', methods=['POST'])
def editIndicatorReport() : return(IndicatorReport.edit())

@CARepository.route('/UpdateIndicatorReport', methods=['POST'])
def updateIndicatorReport() : return(IndicatorReport.update())

@CARepository.route('/DeleteIndicatorReport', methods=['POST'])
def deleteIndicatorReport() : return(IndicatorReport.delete())

# -------------------- JSON conversion functions  ----------------------------------------
import Load

@CARepository.route('/RequestLoadJSONLD', methods=['GET'])
def requestLoadJSONLD() : return(LoadJSON.requestLoad())

@CARepository.route('/LoadJSONLD', methods=['POST', 'GET'])
def loadJSONLD() : return(LoadJSON.load())

# -------------------- Error handling  ----------------------------------------

# @CARepository.errorhandler(Exception)
# def all_exception_handler(error):
#    return 'Error', 500

# -------------------- Inject key variables  ----------------------------------------

@CARepository.context_processor
def injectKeyVariables() :
	return(dict(user=config.user, 
				userGname= config.user.forPerson.givenName if config.user and config.user.forPerson else "" , 
				userFname= config.user.forPerson.familyName if config.user and config.user.forPerson else "" ,
				userEmail= config.user.hasEmail if config.user else "",
				organization = config.organization,
				orgName= config.organization.hasLegalName if config.organization else "",
				impactModel = config.impactModel ,
				userType = config.user.userType if config.user else "",
				superUser = config.cidsrep.superuser,
				adminUser = config.cidsrep.admin,
				editorUser = config.cidsrep.editor,
				researcherUser = cidsrep.researcher ,
				convertYMDtoDTD = Util.convertYMDtoDTD ,
				convertDTDtoYMD = Util.convertDTDtoYMD,
				cids = config.cids,
				cadr = config.cadr ))

# ----------------------------------------------------------------------------------------
# initialize the global variables defined in config.py
#-----------------------------------------------------------------------------------------

print("+++++++++++++++++++++ Initializing the CA REpository Server +++++++++++++++++++++++++++")
# deal with json-ld file uploads
CARepository.config['UPLOAD-FOLDER'] = config.UPLOAD_FOLDER

# Set the secret key to some random bytes. Keep this really secret!
CARepository.secret_key = b'_7#y1L"F4Q8zFoX\xec]/'


# definitions of database paths
# path = "/Users/markfox/Dropbox/Repository/db/"
path = "./db/"
db = "cidsrepository.sqlite3"
dbfile = path + db

# open persistent database
config.cidsServer = cidsServer = default_world
print("cidsServer in Main:" , cidsServer)
default_world.set_backend(filename = dbfile, exclusive=False)
# config.cidsServer.set_backend(filename = "/Users/markfox/Dropbox/CSSE Folder/Projects/Common Approach/Repository/db/cidsrepository.sqlite3", exclusive=False)
	
print("load ontologies")
config.cidsrep = cidsrep = cidsServer.get_ontology('http://ontology.eil.utoronto.ca/cids/cidsrep')
config.cids = cids = cidsServer.get_ontology('http://ontology.eil.utoronto.ca/cids/cids')
config.cadr = cadr = cidsServer.get_ontology('http://ontology.eil.utoronto.ca/cids/cadr')  # instances for the data repository
	
print("set namespaces")
config.org = org = config.cidsServer.get_namespace('http://ontology.eil.utoronto.ca/tove/organization')
config.ic =ic = config.cidsServer.get_namespace('http://ontology.eil.utoronto.ca/tove/icontact')
config.act = act = config.cidsServer.get_namespace('http://ontology.eil.utoronto.ca/tove/activity')
config.i72 = i72 = config.cidsServer.get_namespace('http://ontology.eil.utoronto.ca/ISO21972/iso21972')
config.time = time = config.cidsServer.get_namespace('http://www.w3.org/2006/time')
config.schema = schema = config.cidsServer.get_namespace('http://schema.org/')
config.foaf = foaf = config.cidsServer.get_namespace('http://xmlns.com/foaf/0.1/')
config.dc = dc = config.cidsServer.get_namespace('http://purl.org/dc/elements/1.1/')
config.skos = skos = config.cidsServer.get_namespace('http://www.w3.org/2004/02/skos/core')

# set of conversion dictionaries
config.convLocatedIn['local'] = config.cidsrep.locall
config.convLocatedIn['regional'] = config.cidsrep.regional
config.convLocatedIn['provincial'] = config.cidsrep.provincial
config.convLocatedIn['national'] = config.cidsrep.national
config.convLocatedIn['multinational'] = config.cidsrep.multinational
config.convLocatedIn['global'] = config.cidsrep.globall

# defined levels of editing
config.adminEnabled = [config.cidsrep.superuser, config.cidsrep.admin]
config.editEnabled = [config.cidsrep.superuser, config.cidsrep.admin, config.cidsrep.editor]
config.reportEnabled = [config.cidsrep.superuser, config.cidsrep.admin, config.cidsrep.editor, config.cidsrep.reporter]
config.researchEnabled = [config.cidsrep.superuser, config.cidsrep.admin, config.cidsrep.editor, config.cidsrep.reporter, config.cidsrep.researcher]

config.userTypesMap = {"superuser" : config.cidsrep.superuser, "admin" : config.cidsrep.admin,
					 "editor" : config.cidsrep.editor, "reporter" : config.cidsrep.reporter,
					 "researcher" : config.cidsrep.researcher}

# define the risk types in the repository - need to generalize so HTML names are embedded 
# as annotations, just as name and title are
config.risks = [(config.cids.EvidenceRisk, "evrl", "evrd"), 
				(config.cids.ExternalRisk, "exrl", "exrd") ,
				(config.cids.StakeholderParticipationRisk, "strl", "strd") ,
				(config.cids.DropOffRisk, "dorl", "dord") ,
				(config.cids.EfficiencyRisk, "efrl", "efrd") ,
				(config.cids.ExecutionRisk, "ecrl", "ecrd") ,
				(config.cids.AlignmentRisk, "alrl", "alrd") ,
				(config.cids.EnduranceRisk, "enrl", "enrd") ,
				(config.cids.UnexpectedImpactRisk, "uirl", "uird")
				]
					 
# start the repository server on port 5000 $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

config.user = None
config.organization = None
config.impactModel = None

cidsServer.save()
print("+++++++++++++++++++++ Running the CA REpository Server +++++++++++++++++++++++++++")

print("starting server")
CARepository.run(debug=True)

# close database before exiting
cidsServer.save()
session.pop('hasEmail', None)  # remove email from session
session.pop('forOrganization', None)  # remove email from session

