# CA-Repository-save.py saves the Common Approach datat repository instances

from owlready2 import *
import datetime
import rdflib
from rdflib import RDF, FOAF, Namespace
from flask import Flask, render_template, request, session, redirect, url_for, g, flash
from werkzeug.utils import secure_filename

import config
import Util

# file name for the Common Approach CIDS repository
path = "/Users/markfox/Dropbox/CSSE Folder/Projects/Common Approach/Repository/db/"
db = "cidsrepository.sqlite3"
dbfile = path + db
cadrfile = path + "/cadrarchive/cadr.rdf" + "." + str(datetime.datetime.now())

# open persistent database
print("Opening database ", dbfile)
config.cidsServer = default_world
config.cidsServer.set_backend(filename = dbfile, exclusive=False)

print("loading ontologies")
config.cidsrep = config.cidsServer.get_ontology('http://ontology.eil.utoronto.ca/cids/cidsrep')
config.cids = config.cidsServer.get_ontology('http://ontology.eil.utoronto.ca/cids/cids')
config.cadr = config.cidsServer.get_ontology('http://ontology.eil.utoronto.ca/cids/cadr')  # instances for the data repository
	
print("setting namespaces")
config.org = config.cidsServer.get_namespace('http://ontology.eil.utoronto.ca/tove/organization')
config.ic = config.cidsServer.get_namespace('http://ontology.eil.utoronto.ca/tove/icontact')
config.act = config.cidsServer.get_namespace('http://ontology.eil.utoronto.ca/tove/activity')
config.i72 = config.cidsServer.get_namespace('http://ontology.eil.utoronto.ca/iso21972/iso21972')
config.time = config.cidsServer.get_namespace('http://www.w3.org/2006/time')
config.schema = config.cidsServer.get_namespace('http://schema.org/')
config.foaf = foaf = config.config.cidsServer.get_namespace('http://xmlns.com/foaf/0.1/')
config.dc = dc = config.cidsServer.get_namespace('http://purl.org/dc/elements/1.1/')'
config.skos = skos = config.cidsServer.get_namespace('http://www.w3.org/2004/02/skos/core')

print("saving cadr instances")
config.cadr.save(file=cadrfile)  # saves as rdf/xml as default




