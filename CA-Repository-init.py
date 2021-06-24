# CA-Repository-init.py initializes the Common Approach repository
# It loads all of the ontologies and datafiles into the database

import sys
sys.path.insert(0, './lib')

from owlready2 import *
# from crypto.Cipher import AES
import shutil
import os
import config as config
import Util as Util
import Load as Load


# file name for the Common Approach CIDS repository
path = "./db/"
db = "cidsrepository.sqlite3"
dbfile = path + db

# backup current database
if os.path.exists(dbfile) :
	shutil.move(dbfile, path + "Backup/" + db + "." + str(datetime.datetime.now()))

# create the CA repository database
default_world.set_backend(filename = dbfile, exclusive=False)

# load cids ontology
print("Loading CIDS ontology.")
config.cids = get_ontology("http://ontology.eil.utoronto.ca/cids/cids.owl")
config.cids.load()

# load the cids user related ontology
print("Loading CIDSREP ontology.")
config.cidsrep = default_world.get_ontology("http://ontology.eil.utoronto.ca/cids/cidsrep.owl")
config.cidsrep.load()

#load saved instances in repository
print("Loading CADR ontology.")
config.cadr = default_world.get_ontology('file:///Users/markfox/Dropbox/Repository/ontology/cadr.owl')
config.cadr.load()
print(list(config.cadr.individuals()))

config.org = default_world.get_namespace('http://ontology.eil.utoronto.ca/tove/organization')

# set up repository instance
config.repository = config.cidsrep.Repository(namespace=config.cadr)
config.repository.hasUser =[]
config.repository.hasOrganization =[]

# Create superuser - note that the password and email should be parameters of the script
# and not hardwired
superuser = config.cidsrep.User(namespace=config.cidsrep)
config.repository.hasUser.append(superuser)
superuser.userType = config.cidsrep.superuser
superuser.hasEmail = "msf@eil.utoronto.ca"

# encrypt password and store in superuser - not working - problem with Crypto module
# enc = AES.new('CARepository $-% key2021', AES.MODE_CBC, 'This is an IV456')
# superuser.hasPassword = enc.encrypt("sdic5!Pass-%")
superuser.hasPassword = "p"

# Create test organization
o1 = config.cids.SocialPurposeOrganization(namespace=config.cadr)
config.repository.hasOrganization.append(o1)
o1.hasLegalName = "Test Organization 1"
o1.hasImpactModel = [config.cids.ImpactMeasurement(namespace=config.cadr, forOrganization=o1, 
	hasName="Test Org 1 Impact Measurement Model" , hasStakeholder=[], hasDescription="Test Org1 impact Model",
	hasOutcome=[], hasIndicator=[], hasImpactRisk=[], hasImpactReport=[], hasStakeholderOutcome=[])]
im = o1.hasImpactModel[0]
im.hasCharacteristic=[]
oid = config.org.OrganizationID(namespace=config.cadr)
o1.hasID = oid
oid.hasIdentifier = "TestOrg1"
oid.forOrganization = o1

ind1 = config.cids.Indicator(namespace=config.cadr, definedBy=o1)
ind1.hasName = "Poor Population Ratio"
ind1.hasDescription = "Measures the ratio of poor to city population."
ind1.forOrganization = o1
ind1.hasBaseline = None
ind1.hasThreshold = None
o1.hasImpactModel[0].hasIndicator =[ind1]

stk1 = config.cids.Stakeholder(namespace=config.cadr, forOrganization=o1)
stk1.hasDescription = "Stakeholder 1 for Org 1"
stk1.hasName = "Stakeholder 1"
stk1.hasCharacteristic = []
stk1.located_in = [config.cidsrep.locall]
o1.hasImpactModel[0].hasStakeholder =[stk1]

# Create second test organization
o2 = config.cids.SocialPurposeOrganization(namespace=config.cadr, hasLegalName = "Test Organization 2")
config.repository.hasOrganization.append(o2)
o2.hasImpactModel = [config.cids.ImpactMeasurement(namespace=config.cadr, forOrganization=o2, 
	hasName="Test Org 2 Impact Measurement Model", hasStakeholder=[], 
	hasOutcome=[], hasIndicator=[], hasImpactRisk=[], hasImpactReport=[], hasStakeholderOutcome=[],
	hasCharacteristic=[])]
oid = config.org.OrganizationID(namespace=config.cadr, hasIdentifier = "TestOrg2", forOrganization = o2)
o2.hasID = oid

ind2 = config.cids.Indicator(namespace=config.cadr, definedBy=o2)
ind2.hasName = "Rich Population Ratio"
ind2.hasDescription = "Measures ratio of rich to city population."
ind2.forOrganization = o2
ind2.hasBaseline = None
ind2.hasThreshold = None
o2.hasImpactModel[0].hasIndicator =[ind2]

# Create test org user
normaluser = config.cidsrep.User(namespace=config.cadr)
config.repository.hasUser.append(normaluser)
normaluser.userType = config.cidsrep.admin
normaluser.hasEmail = "user@test.org"
normaluser.hasPassword = "p"
normaluser.forOrganization = o1
normaluser.forPerson = config.cids.Person(namespace=config.cadr, givenName="John", familyName="Smith")

print("CIDSREP final list of individuals:")
print(list(config.cidsrep.individuals()))

print("CADR final list of individuals:")
print(list(config.cadr.individuals()))

default_world.save()

# load IRIS Indicators with IRIS as an organization
print("Loading IRIS")
Load.loadIRIS("codelist-library/IRIS Taxonomy 5.1_June2020.xlsx")

default_world.save()

# load UNSDGs with UN as an organization
print("Loading UNSDGs")
Load.loadUNSDG("codelist-library/UNSDG.xlsx")

# save all to the database before exiting
default_world.save()
