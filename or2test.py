from flask import Flask, render_template, request, session, redirect, url_for, g, flash
from owlready2 import *
import gensim
import numpy as np
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
import json
from pyld import jsonld
import rdflib
from rdflib import RDF, FOAF
from werkzeug.utils import secure_filename
import os

import config
import Util

propertyChains = {"hasAcquired" : ["hasAcquired", "consistsOf"]}


CARepository = Flask(__name__)

config.cidsServer = default_world
config.cidsServer.set_backend(filename = "/Users/markfox/Dropbox/CSSE Folder/Projects/Common Approach/Repository/db/cidsrepository.sqlite3", exclusive=False)

print("load ontologies")
config.cidsrep = cidsrep = config.cidsServer.get_ontology('http://ontology.eil.utoronto.ca/cids/cidsrep')
config.cids = cids = config.cidsServer.get_ontology('http://ontology.eil.utoronto.ca/cids/cids')
config.cadr = cadr = config.cidsServer.get_ontology('http://ontology.eil.utoronto.ca/cids/cadr')  # instances for the data repository
	
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

print("cidsrep individuals")
print(list(config.cidsrep.individuals()))

print("cids individuals")
print(list(config.cids.individuals()))

print("cadr individuals")
print(list(config.cadr.individuals()))

og1 = config.cids.Organization(hasLegalName = "Test Organization 1")
og2 = config.cids.Organization(hasLegalName = "Test Organization 2")
og3 = config.cids.Organization(hasLegalName = "Test Organization 3")
og4 = config.cids.Organization(hasLegalName = "Test Organization 4")
og1.hasAcquired = [og2]
og2.hasSubsidiary = [og3, og4]

config.repository = rep = config.cadr.search_one(type=config.cidsrep.Repository)
un = config.cadr.search_one(type=config.cids.Organization, hasLegalName="United Nations")
im = un.hasImpactModel[0]
out1 = im.hasOutcome[0]
ind1 = im.hasIndicator[0]
superOut1 = out1.is_a[0]

import Reasoning
print("hasAcquired property chains: ", Reasoning.getPropertyChain(org.hasAcquired, w=config.cidsServer))
res = Reasoning.relatedAll(og1, org.hasAcquired)
print("related: ", res)


