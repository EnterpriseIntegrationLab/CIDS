from flask import Flask, render_template, request, session, redirect, url_for, g, flash
from werkzeug.utils import secure_filename
import os

CARepository = Flask(__name__)

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

# global variables to be used in a session
global g_user			# need to know who the user is that is logged in
global convLocatedIn 	# converts location name into object
global g_organization	# selected organization for the user
global g_impactModel	# selected impact model for the organization
global cidsServer
convLocatedIn = dict()

# definitions of database paths
path = "/Users/markfox/Dropbox/CSSE Folder/Projects/Common Approach/Repository/db/"
db = "cidsrepository.sqlite3"
dbfile = path + db

# from Crypto.Cipher import AES

@CARepository.context_processor
def injectKeyVariables() :
	global g_user, g_organization, g_impactModel, cidsServer

	return(dict(user=g_user, 
				userGname= g_user.forPerson.givenName if g_user and g_user.forPerson else "" , 
				userFname= g_user.forPerson.familyName if g_user and g_user.forPerson else "" ,
				userEmail= g_user.hasEmail if g_user else "",
				organization = g_organization,
				orgName= g_organization.hasLegalName if g_organization else "",
				impactModel = g_impactModel ,
				userType = g_user.userType if g_user else "",
				superUser = cidsrep.superuser,
				adminUser = cidsrep.admin,
				editorUser = cidsrep.editor,
				researcherUser = cidsrep.researcher ,
				convertYMDtoDTD = convertYMDtoDTD ,
				convertDTDtoYMD = convertDTDtoYMD ))
		
# ------------------------------ Login/logout/Save/logging -------------------------------

@CARepository.route('/', methods=['GET'])
def index() :
	global g_user, g_organization, g_impactModel, cidsServer

	return(render_template('index.html'))
	
@CARepository.route('/Login', methods=['POST'])
def login() :
	global g_user, g_organization, g_impactModel, cidsServer
	valid_user = valid_login(request.form['hasEmail'],request.form['hasPassword'])
	if valid_user :
		log_the_user_in(valid_user)
		
		if g_user.userType in [cidsrep.admin, cidsrep.editor]: 
			if len(g_organization.hasImpactModel) > 1 :
				impactModels = [ (im.iri, im.hasName, im.hasDescription) for im in g_organization.hasImpactModel ]
				return(render_template("impactModelSelect.html", action="display", impactModels=impactModels, message="Please select Impact Model to edit."))
			g_impactModel = g_organization.hasImpactModel[0]
			return(renderImpactModel(g_impactModel, "display", "", g_organization.hasID.hasIdentifier + " Impact Model Configuration."))
		return(render_template('main.html'))
	else :
		return(render_template('index.html', message="Login Failed: Invalid email or password"))

@CARepository.route('/Logout')
def logout():
	global g_user, g_organization, g_impactModel, cidsServer

	# remove the user Email from the session if it's there
	session.pop('hasEmail', None)
	# set session user to None
	g_user = None
	g_organization = None
	g.userType = None
	cidsServer.save()
	return redirect(url_for('index'))

@CARepository.route('/DumpInstances')
def saveCADR() :
	global g_user, g_organization, g_impactModel, cidsServer
	print("saving cadr instances")
	cadrfile = path + "/cadrarchive/cadr.rdf" + "." + str(datetime.datetime.now())
	cadr.save(file=cadrfile)  # saves as rdf/xml as default
	return(render_template('main.html', message="CADR saved as " + cadrfile))


def logIndividual(comment, *arg) :
	global g_user, g_organization, g_impactModel, cidsServer
	logchan = open("logs/cadrChanges.log" + str(datetime.date.today()), 'a+')
	for ind in arg :
		if ind : 
			print("logIndividual ", comment, ": IRI=", ind.iri)
			js = cnvIndJSONLD(ind, comment=comment)
			logchan.write("\n\n" + js)
	logchan.close()
#	cidsServer.save()	# uncomment when system is ready to really run

# -------------------- JSON conversion functions  ----------------------------------------

@CARepository.route('/RequestLoadJSONLD', methods=['GET'])
def requestLoadJSONLD() :
	global g_user, g_organization, g_impactModel, cidsServer
	
	# kick user out if they are not a superuser - should not happen as they would not get access to the registerorganization page
	if (g_user.userType != cidsrep.superuser) and (g_user.userType != cidsrep.admin) :
		return(render_template('main.html', message="You do not have access rights for loading data."))
		
	return(render_template('loadJsonld.html', path="http://localhost:5000/LoadJSONLD"))

@CARepository.route('/LoadJSONLD', methods=['POST', 'GET'])
def loadJSONLD() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	global UPLOAD_FOLDER, ALLOWED_EXTENSIONS
	
	if request.method != 'POST': return(render_template('main.html', message="Incorrect post method."))
	if not g_organization : return(render_template('main.html', message="No organization selected."))
	
	# Part 1: save the file to the subdirectory for the organization
	#	* file contents cannot be binary!!! ascii string
    # check if the post request has the file part
	if not 'file'  in request.files :
		flash('No file part')
		return(redirect(request.url))

	file = request.files['file']
	# if user does not select file
	if file.filename == '':
		flash('No selected file')
		return(redirect(request.url))
	if not (file and allowed_file(file.filename)): render_template('main.html', message="File extension not allowed.")
    
    # store the file in the organization's upload directory
	filename = secure_filename(file.filename)
	print("Filename: ", filename)
	uploadDirectory = UPLOAD_FOLDER + '/' + g_organization.hasID.hasIdentifier
	if not os.path.exists(uploadDirectory): os.makedirs(uploadDirectory)
	path = os.path.join(uploadDirectory, filename)
	file.save(path)
    
    # Part 2: convert json-ld into n-triple and then load into OWLReady2
    # Next is to read and convert the file using rdflib serialization
	g = Graph()
	g.parse(path, format="json-ld")
	nt = g.serialize(format="nt")
	nt = nt.decode('ascii')
	ntpath, ext = path.split(".")
	ntpath = ntpath + ".owl"		# have to save with owl extension for owlready2 to compile entities properly
	with open(ntpath, 'w') as f: 
		f.write(nt)
		f.close()
	uploadns = cidsServer.get_ontology(ntpath) # now load the indiv into owlready2
	uploadns.load()
	
	# get ids of and log each one by re-reading the json-ld file and pulling ids
	with open(path, "r") as f: js = json.load(f)
	if type(js) != list : js = [js]
	for ind in js :
		id = ind["@id"]
		print("Loaded ", id)
		if id :
			idp = cidsServer.search_one(iri=id)
			if not idp : 
				print("Can't find ", id)
			else :
				logIndividual("Upload", idp)
	return(render_template('main.html', message="Upload complete: " + filename))
    

def loadNtriples(js) :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	graph = cidsServer.as_rdflib_graph()
	jsonDict = json.loads(js)
	id = jsonDict["@id"]
	typ = jsonDict["@type"]
	ind = cadr.search_one(iri=id)
	if ind :
		# check that the type is consistent, if not generate an errot
		ns, entity = rdflib.namespace.split_uri(ind)
		# delete entity and replace with new data
		logIndividual("Load JSONLD - delete", ind) # log it so that it can be retrieved if need
		delete_entity(ind)

	# create individual of the correct type
	type_ns, type_entity = rdflib.namespace.split_uri(typ)
	ind_ns, ind_entity = rdflib.namespace.split_uri(ind)
	tns = rdflib.Namespace(type_ns)
	ins = rdflib.Namespace(ind_ns)
	with cadr :
		graph.add((ins[ind_entity], RDF.type, tns[type_entity]))
	
	# go through keys and produce corresponding attribute
	# ADD HANDLING OF VALUE THAT IS A LIST
	for key in jsonDict :
		if (key != "@id") and (key != "@type") and (key != "@context") :
			pns, pentity = rdflib.namespace.split_uri(key)
			rdflib_pns = rdflib.Namespace(pns)
			values =  jsonDict[key] if type(jsonDict[key]) is list else [jsonDict[key]]
			vns, ventity = rdflib.namespace.split_uri(jsonDict[key])
			for value in values :
				rdflib_vns = rdflib.Namespace(vns)
				with cadr:
					graph.add((ins[ind_entity], rdflib_pns[pentity], rdflib_vns(ventity)))

def cnvIndJSONLD(ind, comment=None, annotate=True) :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
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
		jsd['<http://ontology.eil.utoronto.ca/cids/cids#modifiedBy>'] = [g_user.hasEmail]
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


#--------------- User --------------------------------------------------------------------

@CARepository.route('/AddUser')
def addUser() :
	global g_user, g_organization, g_impactModel, cidsServer

	if g_user.userType == cidsrep.superuser : return(render_template('userEdit.html', action='add'))
	
	if g_user.userType == cidsrep.admin :	
		return(render_template('userEdit.html', orgIDValue= g_user.forOrganization.hasID.hasIdentifier, 
				readonly="readonly", action="add", path=path))

	path = "http://localhost:5000/UpdateUser"
	
	return(render_template('main.html', message="Error: User does not have permission to add a User."))

@CARepository.route('/SelectUser', methods=['GET'])
def selectUser() :
	global g_user, g_organization, g_impactModel, cidsServer
	if (g_user.userType != cidsrep.superuser) and (g_user.userType != cidsrep.admin) : 
		return(render_template('main.html', message="You do not have access rights to add a User."))
	
	action = request.args.get('action')
	print("Action: ", action)
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditUser"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteUser"
	else :
		return(render_template('main.html', message="Error: Unknown User action: " + str(action)))
	
	if (g_user.userType == cidsrep.superuser) : return(render_template('userSelect.html', path=path, action=action))
	
	users = dict()
	print("gorg=", g_organization)
	for user in cadr.search(type=cidsrep.User, forOrganization=g_organization) : 
		value = user.hasEmail + " [ "
		if user.forPerson :
			if user.forPerson.familyName : value += user.forPerson.familyName + ", "
			if user.forPerson.givenName : value += user.forPerson.givenName
			value += " ]"
		users[user.hasEmail] = value
	return(render_template('userSelect.html', path=path, action=action, users=users))


@CARepository.route('/EditUser', methods=['POST'])
def editUser() :
	global g_user, g_organization, g_impactModel, cidsServer
	
	path = "http://localhost:5000/UpdateUser"

	if (g_user.userType == cidsrep.researcher) or (g_user.userType == cidsrep.editor):
		return(render_template('main.html', message="Error: " + g_user.hasEmail + " does not have permission to edit a User."))
		
	euser = cadr.search_one(type=cidsrep.User, hasEmail=request.form['hasEmail'])
	if not euser :
		return(render_template('main.html', message="Error: User " + request.form['hasEmail'] + " does not exist."))
		
	if (g_user.userType == cidsrep.admin) and (g_user.forOrganization != euser.forOrganization) :
		return(render_template('main.html', message="Error: User " + g_user.hasEmail + " and " + request.form['hasEmail'] + " organizations do not match."))
	
	action = request.form['action']
	readonly = "readonly" if g_user != cidsrep.superuser else ""
	
	return(renderUser(euser, action, path, readonly, ""))

	
@CARepository.route('/UpdateUser', methods=['POST'])
def updateUser() :
	global g_user, g_organization, g_impactModel, cidsServer

	if (g_user.userType == cidsrep.superuser) or (g_user.userType == cidsrep.admin):
		readonly = "readonly" if g_user != cidsrep.superuser else ""
		euser = cadr.search_one(type=cidsrep.User, hasEmail=request.form['hasEmail'])
		if not euser : euser = cidsrep.User(namespace=cadr, forPerson= cids.Person(namespace=cadr))
			
		euser.hasEmail = request.form['hasEmail']
		euser.hasPassword = request.form['hasPassword']
		euser.forPerson.givenName = request.form['givenName']
		euser.forPerson.familyName = request.form['familyName']
		if not euser.forPerson.hasTelephone :
			pn = ic.PhoneNumber(namespace=cadr)
			euser.forPerson.hasTelephone = [pn]
		else :
			pn = euser.forPerson.hasTelephone[0]
		pn.hasPhoneNumber = request.form['hasPhoneNumber']
		euser.forOrganization = g_user.forOrganization if g_user.userType == cidsrep.admin else getOrganization(request.form['orgID'])
		logIndividual("Update User", euser, euser.forPerson, pn)
		return(renderUser(euser, "display", "", readonly, "User " + euser.hasEmail + " added."))
	
	return(render_template('main.html', message="Error: User does not have permission to add a User."))
	
	
@CARepository.route('/DeleteUser', methods=['POST'])
def deleteUser() :
	global g_user, g_organization, g_impactModel, cidsServer
	if (g_user.userType != cidsrep.superuser) and (g_user.userType != cidsrep.admin) : 
		return(render_template('main.html', message="You do not have access rights to add a User."))
	
	euser = cadr.search_one(type=cidsrep.User, hasEmail=request.form['hasEmail'])
	if euser :
		if (g_user.userType == cidsrep.admin) and  (euser.forOrganization != g_user.forOrganization) :
			return(render_template('main.html', message="You can only delete Users associated with your organization."))
		logIndividual("Deleted User", euser)
		destroy_entity(euser)
		return(render_template('menu.html',  message="Deleted user " + request.form['hasEmail'] + "."))
	return(render_template('main.html', message="Error: User " + request.form['hasEmail'] + " does not exist."))


def renderUser(user, action, path, readonly, message) :
	global g_user, g_organization, g_impactModel, cidsServer
	
	per = user.forPerson
	pn = per.hasTelephone[0].hasPhoneNumber if per.hasTelephone else ""
	o = user.forOrganization
	bn = o.hasID.hasIdentifier
	return(render_template('userUpdate.html', readonly=readonly, action=action, message=message, path=path,
				hasEmailValue= user.hasEmail,
				hasPasswordValue= user.hasPassword,
				givenNameValue= user.forPerson.givenName,
				familyNameValue= user.forPerson.familyName,
				hasPhoneNumberValue= pn,
				orgIDValue= bn,
				userTypeValue = user.userType
				))
				
	
# -------------------- Organization -------------------------------------------------------

@CARepository.route('/AddOrganization', methods=['GET'])
def addOrganization() :
	global g_user, g_organization, g_impactModel, cidsServer

	user = cadr.search_one(type=cidsrep.User, hasEmail=session['hasEmail'])
	
	# kick user out if they are not a superuser - should not happen as they would not get access to the registerorganization page
	if user.userType != cidsrep.superuser :
		return(render_template('main.html', 
				message="You do not have access rights for Registering an Organization."))
		
	return(render_template('organizationEdit.html', action='add', path="http://localhost:5000/UpdateOrganization"))



@CARepository.route('/SelectOrganization', methods=['GET'])
def selectOrganization() :
	global g_user, g_organization, g_impactModel, cidsServer

	if g_user.userType != cidsrep.superuser : 
		return(render_template('main.html', message="You do not have access rights for an Organization."))
	
	action = request.args.get('action')
	if action == "edit" :
		path = "http://localhost:5000/EditOrganization"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteOrganization"
	else :
		return(render_template('main.html', message="Error: Unknown Organization action: " + str(action)))
	
	orgs = dict()
	for og in cadr.search(type=cids.Organization) : orgs[og.hasID.hasIdentifier] = og.hasLegalName
	return(render_template('organizationSelect.html', path=path, action=action, organizations=orgs))
	
	
@CARepository.route('/EditOrganization', methods=['POST', 'GET'])
def editOrganization() :
	global g_user, g_organization, g_impactModel, cidsServer

	action = request.args.get('action') or request.form['action']
	path = "http://localhost:5000/UpdateOrganization"
	
	# get organization for the current user
	if g_user.userType == cidsrep.superuser :
		if action == "display" : 
			if not g_organization : return(render_template('main.html', message="Organization not selected."))
			o = g_organization
		else :
			o = getOrganization(request.form["orgID"])
			g_organization = o
		ro =""
	elif  g_user.userType == cidsrep.admin : 
		o = g_user.forOrganization
		ro = "readonly"
	else :
		# kick user out if they are not a superuser or admin - should not happen as they would not get access to the registerorganization page
		return(render_template('main.html', message="You do not have access rights for Registering/Editing an Organization."))

	return(renderOrganization(o, action, path, ro, ""))
	
	
@CARepository.route('/UpdateOrganization', methods=['POST'])
def updateOrganization() :
	global g_user, g_organization, g_impactModel, cidsServer

	# kick user out if they are not a superuser - should not happen as they would not get access to the registerorganization page
	if (request.form["action"] == "add") and (g_user.userType != cidsrep.superuser) :
		return(render_template('main.html', message="You do not have access rights for Adding an Organization."))
				
	# check that the organization does not already exist
	oid = cadr.search_one(type=org.OrganizationID, hasIdentifier= request.form['orgID'])
	if oid :
		if request.form['action'] == 'add' : return(render_template('organizationUpdate.html', message="Error: Organization already exists."))
	else :
		if request.form['action'] == 'edit' : return(render_template('organizationUpdate.html', message="Error: Organization does not exist."))
	
	readonly = "readonly" if g_user.userType != cidsrep.superuser else ""
	
	if request.form['action'] == 'add' :
		neworg = cids.Organization(namespace=cadr)
	
		# create the OrganizationID and link
		newid = org.OrganizationID(namespace=cadr)
		newid.forOrganization = neworg
		newid.hasIdentifier = request.form['orgID']
		neworg.hasID = newid
		neworg.dateCreated = datetime.datetime.now().isoformat()
		
		# create impact model for common approach
		im = cids.ImpactMeasurement(namespace=cadr, forOrganization=neworg, hasStakeholder=[], 
			hasOutcome=[], hasIndicator=[], hasImpactRisk=[], hasImpactReport=[], hasStakeholderOutcome=[])
		neworg.hasImpactModel = [im]
		g_organization = neworg
		g_impactModel = im

	elif request.form['action'] == 'edit' :
		neworg = oid.forOrganization
		newid = oid
	else :
		return(render_template('main.html', message="Error: unknown action for Organization."))
	
	# Fill the instance of cids.Organization
	neworg.hasLegalName = request.form['hasLegalName']
	neworg.useOfFunds = request.form['useOfFunds']
	neworg.hasDescription = request.form['hasDescription']
	
	# Build the ic.Address instance and link
	if not neworg.hasAddress :
		addr = ic.Address(namespace=cadr)
		neworg.hasAddress = [addr]
	else :
		addr = neworg.hasAddress[0]
	print("address: ", addr, request.form['hasStreetNumber'])
	addr.hasStreetNumber = request.form['hasStreetNumber']
	addr.hasStreet = request.form['hasStreet']
	addr.hasUnitNumber = request.form['hasUnitNumber']
	addr.hasCityS = request.form['hasCityS']
	addr.hasProvince = request.form['hasProvince']
	addr.hasPostalCode = request.form['hasPostalCode']
	
	# Build Phone number for the Organization
	if not neworg.hasTelephone :
		pn1 = ic.PhoneNumber(namespace=cadr)
		neworg.hasTelephone = [pn1]
	else :
		pn1 = neworg.hasTelephone[0]
	pn1.hasPhoneNumber = request.form['hasPhoneNumber']
	
	# Build the contact as Person and link
	if not neworg.hasContact :
		contac = cids.Person(namespace=cadr)
		neworg.hasContact = [contac]
	else :
		contac = neworg.hasContact[0]
	contac.givenName = request.form['contactFirstName']
	contac.familyName = request.form['contactLastName']
	contac.hasEmail = request.form['contactEmail']
	
	if not contac.hasTelephone :
		pn2 = ic.PhoneNumber(namespace=cadr)
		contac.hasTelephone = [pn2]
	else :
		pn2 = contac.hasTelephone[0]
	pn2.hasPhoneNumber = request.form['contactPhoneNumber']
	
	logIndividual("Update Organization", neworg, newid, addr, pn1, contac, pn2, neworg.hasImpactModel[0])
	
	return(renderOrganization(neworg, "display", readonly, "Organization " + newid.hasIdentifier + " information saved."))

	
@CARepository.route('/DeleteOrganization', methods=['POST'])
def deleteOrganization() :
	global g_user, g_organization, g_impactModel, cidsServer

	if g_user.userType != cidsrep.superuser : 
		return(render_template('main.html', message="You do not have access rights for Deleting an Organization."))
	
	oid = cadr.search_one(type=org.OrganizationID, hasIdentifier=request.form['orgID'])
	og = oid.forOrganization
	if oid : 
		logIndividual("Delete Organization", oid)
		destroy_entity(oid)
	if og : 
		logIndividual("DeleteOrganization", og)
		destroy_entity(og)
	if og or oid: return(render_template('main.html',  message="Deleted organization " + request.form['orgID'] + "."))
	return(render_template('main.html', message="Error: Organization " + request.form['orgID'] + " does not exist."))
	
def renderOrganization(o, action, path, readonly, message) :
	global g_user, g_organization, g_impactModel, cidsServer
	
	hasImpactModelValue = None
	hasStreetNumberValue= ""
	hasStreetValue= ""
	hasUnitNumberValue= ""
	hasCitySValue= ""
	hasProvince= ""
	hasPostalCodeValue= ""
	if o.hasAddress :
		hasStreetNumberValue= o.hasAddress[0].hasStreetNumber
		hasStreetValue= o.hasAddress[0].hasStreet
		hasUnitNumberValue= o.hasAddress[0].hasUnitNumber
		hasCitySValue= o.hasAddress[0].hasCityS
		hasProvince= o.hasAddress[0].hasProvince
		hasPostalCodeValue= o.hasAddress[0].hasPostalCode
	
	hasPhoneNumberValue= ""
	if o.hasTelephone :
		hasPhoneNumberValue= o.hasTelephone[0].hasPhoneNumber
	
	contactFirstNameValue= ""
	contactLastNameValue= ""
	contactEmailValue= ""
	contactPhoneNumberValue=""
	if o.hasContact :
		contactFirstNameValue= o.hasContact[0].givenName
		contactLastNameValue= o.hasContact[0].familyName
		contactEmailValue= o.hasContact[0].hasEmail
		if o.hasContact[0].hasTelephone :
			contactPhoneNumberValue= o.hasContact[0].hasTelephone[0].hasPhoneNumber
	
	return(render_template('organizationEdit.html', readonly=readonly, action=action, path=path,
				orgIDValue = o.hasID.hasIdentifier,
				hasImpactModelValue = hasImpactModelValue,
				hasLegalNameValue = o.hasLegalName,
				hasDescriptionValue= o.hasDescription,
				useOfFundsValue= o.useOfFunds,
				hasStreetNumberValue= hasStreetNumberValue,
				hasStreetValue= hasStreetValue,
				hasUnitNumberValue= hasUnitNumberValue,
				hasCitySValue= hasCitySValue,
				hasProvince= hasProvince,
				hasPostalCodeValue= hasPostalCodeValue,
				hasPhoneNumberValue= hasPhoneNumberValue,
				contactFirstNameValue= contactFirstNameValue,
				contactLastNameValue= contactLastNameValue,
				contactEmailValue= contactEmailValue,
				contactPhoneNumberValue= contactPhoneNumberValue
				))

#--------------- ImpactModel -------------------------------------------------------------

@CARepository.route('/AddImpactModel', methods=['GET'])
def addImpactModel() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	if (g_user.userType == cidsrep.superuser) or (g_user.userType == cidsrep.admin): 
		path = "http://localhost:5000/UpdateImpactModel"
		return(renderImpactModel(None, "add", path, g_organization.iri))
		
	return(render_template('main.html', message="Error: User does not have permission to add an ImpactModel."))


@CARepository.route('/SelectImpactModel', methods=['GET'])
def selectImpactModel() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer

	action = request.args.get('action')
	
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditImpactModel"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteImpactModel"
	else :
		return(render_template('main.html', message="Error: Unknown ImpactModel action: " + action))
		
	if g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor]:
		impactModels = [ (im.iri, im.hasName, im.hasDescription) for im in g_organization.hasImpactModel ]
		return(render_template('ImpactModelSelect.html', path=path, impactModels=impactModels, action=action))
	
	return(render_template('main.html', message="Error: " + g_user.hasEmail + "  does not have permission to edit/display a Stakeholder."))


@CARepository.route('/EditImpactModel', methods=['POST'])
def editImpactModel() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	action = request.form['action']
	
	path = "http://localhost:5000/UpdateImpactModel"
	
	if (g_user.userType == cidsrep.researcher) and (action != 'display') :
		return(render_template('main.html', message="Error: User does not have permission to add/edit/delete a Stakeholder."))
		
	if (g_user.userType == cidsrep.admin) or (g_user.userType == cidsrep.editor) :
		g_organization = g_user.forOrganization
	
	imIRI = request.form['imIRI']
	if not imIRI : 
		return(render_template('main.html', message="Error: No impact model selected."))
	
	im = cadr.search_one(iri=imIRI)
	if not im :
		return(render_template('main.html', message="Error: ImpactModel " + request.form['imIRI'] + " does not exist."))
		
	if ((g_user.userType == cidsrep.admin) or (g_user.userType == cidsrep.editor)) and (g_user.forOrganization != im.forOrganization) :
		return(render_template('main.html', message="Error: User " + g_user.hasEmail + " and ImpactModel " + request.form['imIRI'] + " organizations do not match."))
	
	return(renderImpactModel(im, action, path, ""))


@CARepository.route('/UpdateImpactModel', methods=['POST'])
def updateImpactModel() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	action = request.form['action']
	
	if action == "add" :
		imType = cids.search_one(iri=request.form["imIRI"])
		im = cids[imType](namespace=cadr)
	else :
		im = cadr.search_one(iri=request.form['imIRI'])
		if not im :
			return(render_template('main.html', message="Error: editing a missing ImpactModel. " + imIRI))
	
	im.hasName = request.form['hasName']
	im.hasDescription = request.form['hasDescription']
	logIndividual("Update ImpactModel", im)
	return(renderImpactModel(im, "display", readonly, "ImpactModel " + im.hasName + " information saved."))
	
	
def renderImpactModel(im, action, path, message) :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	hasImpactModelTypeIRI = ""
	impactModelTypes = []
	for imtype in cids.search(subclass_of=cids.ImpactModel) :
		if imtype != cids.ImpactModel : 
			if im and isinstance(im, imtype) : hasImpactModelTypeIRI = imtype.iri
			impactModelTypes.append(imtype)
	stakeholders = im.hasStakeholder if im else []
	outcomes = im.hasOutcome if im else []
	indicators = im.hasIndicator  if im else []
	hasNameValue = im.hasName  if im else ""
	hasDescriptionValue = im.hasDescription if im else ""
	
	return(render_template('impactModelEdit.html', action=action, path=path, message=message,
		impactModelTypes = impactModelTypes ,
		stakeholders = stakeholders ,
		indicators = indicators ,
		outcomes = outcomes ,
		hasNameValue = hasNameValue ,
		hasDescriptionValue = hasDescriptionValue ,
		hasImpactModelTypeIRI = hasImpactModelTypeIRI
		))
	
	
	

#--------------- Stakeholder -------------------------------------------------------------

@CARepository.route('/AddStakeholder')
def addStakeholder() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	if (g_user.userType == cidsrep.superuser) or (g_user.userType == cidsrep.admin): 
		path = "http://localhost:5000/UpdateStakeholder"
		return(render_template('stakeholderEdit.html', path=path, action="add"))
	return(render_template('main.html', message="Error: User does not have permission to add a Stakeholder."))


@CARepository.route('/SelectStakeholder', methods=['GET'])
def selectStakeholder() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer

	
	action = request.args.get('action')
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditStakeholder"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteStakeholder"
	else :
		return(render_template('main.html', message="Error: Unknown Stakeholder action: " + action))
		
	if (g_user.userType == cidsrep.superuser) :
		return(render_template('stakeholderSelect.html', path=path, action=action))
		
	if (g_user.userType == cidsrep.admin)  or (g_user.userType == cidsrep.editor):
		stakeholders = cadr.search(type=cids.Stakeholder, forOrganization=g_organization)
		stkList = []
		for stk in stakeholders : stkList.append(stk.hasName)
		return(render_template('stakeholderSelect.html', path=path, stakeholders=stkList, action=action))
	
	return(render_template('main.html', message="Error: " + g_user.hasEmail + "  does not have permission to edit/display a Stakeholder."))


@CARepository.route('/EditStakeholder', methods=['POST', 'GET'])
def editStakeholder() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	if request.method == 'POST':
		action = request.form['action']
		stkIRI = request.form['stkIRI']
	else :
		action = "display"
		stkIRI = request.args.get('stkIRI')
	
	path = "http://localhost:5000/UpdateStakeholder"
	
	if (g_user.userType == cidsrep.researcher) and (action != 'display') :
		return(render_template('main.html', message="Error: User does not have permission to add/edit/delete a Stakeholder."))
		
	if (g_user.userType == cidsrep.admin) or (g_user.userType == cidsrep.editor) :
		g_organization = g_user.forOrganization

	stk = cadr.search_one(type=cids.Stakeholder, iri=stkIRI)
	
	if not stk :
		return(render_template('main.html', message="Error: Stakeholder " + request.form['hasName'] + " does not exist."))
		
	if ((g_user.userType == cidsrep.admin) or (g_user.userType == cidsrep.editor)) and (g_user.forOrganization != stk.forOrganization) :
		return(render_template('main.html', message="Error: User " + g_user.hasEmail + " and Stakeholder " + request.form['hasName'] + " organizations do not match."))
	
	return(renderStakeholder(stk, action, path, ""))


@CARepository.route('/UpdateStakeholder', methods=['POST'])
def updateStakeholder() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	action = request.form['action']
	
	# check if user is permitted to add a Stakeholder
	if (g_user.userType != cidsrep.superuser) and (g_user.userType != cidsrep.admin):
		return(render_template('main.html', message="Error: User does not have permission to add/update a Stakeholder."))
	
	# check if stakeholder already exists for the org and doing add
	stk = cadr.search_one(type=cids.Stakeholder, iri=request.form['stkIRI'], forOrganization=g_organization)
	if stk and (request.form['action'] == 'add') :
		return(render_template('main.html', message="Error: Stakeholder with that name already exists."))
	
	if not stk and (request.form['action'] == 'edit') :
		return(render_template('main.html', message="Error: Stakeholder not found in database."))
	
	if request.form['action'] == 'add' : # create new stakeholder
		stk = cids.Stakeholder(namespace=cadr)
		stk.hasName = request.form['hasName']
		stk.forOrganization = g_organization
		g_impactModel.hasStakeholder.append(stk)
			
	stk.hasDescription = request.form['hasDescription']
	stk.located_in = [convLocatedIn[request.form['located_in']]]
		
	logIndividual("Update Stakeholder", stk, g_impactModel)
	return(renderStakeholder(stk, "display", "", " Stakeholder " + action + " successful."))


@CARepository.route('/DeleteStakeholder', methods=['POST'])
def deleteStakeholder() :
	global g_user, g_organization, g_impactModel, cidsServer
	if (g_user.userType != cidsrep.superuser) and (g_user.userType != cidsrep.admin):
		return(render_template('main.html', message="Error: User does not have permission to delete a Stakeholder."))
		
	stk = cadr.search_one(type=cids.Stakeholder, forOrganization=g_organization, hasName=request.form['hasName'])
	if not stk : return(render_template('main.html', message="Error: Stakeholder " + request.form['hasName'] + " does not exist."))
	if (g_user.userType == cidsrep.admin) and (g_user.forOrganization != stk.forOrganization) :
		return(render_template('main.html', message="Error: User does not have permission to delete a Stakeholder not associated with their Organization."))
	
	logIndividual("Delete Stakeholder", stk)
	destroy_entity(stk)
	return(render_template('main.html',  message="Deleted Stakeholder " + request.form['hasName'] + "."))
	
def renderStakeholder(stk, action, path, message) :
	return(render_template('stakeholderEdit.html', action=action, path=path, message=message, 
				stkIRIValue = stk.iri ,
				hasNameValue = stk.hasName,
				hasDescriptionValue= stk.hasDescription,
				located_inValue= stk.located_in[0].has_Name
				))
#--------------- Indicator  -------------------------------------------------------------

@CARepository.route('/AddIndicator', methods=['GET'])
def addIndicator() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer

	orgID = g_organization.hasID.hasIdentifier if g_organization and g_organization.hasID else None
	if (g_user.userType == cidsrep.superuser) : return(render_template('indicatorEdit.html', orgIDValue=orgID, action="add", ))
	
	if (g_user.userType == cidsrep.admin) and (g_user.forOrganization) : 
		g_organization = g_user.forOrganization
		orgID = g_organization.hasID.hasIdentifier if g_organization and g_organization.hasID else None
		return(render_template('indicatorEdit.html', orgIDValue=orgID, readonly="readonly", action="add", path="http://localhost:5000/UpdateIndicator"))
	
	return(render_template('main.html', message="Error: User does not have permission to add an Indicator."))

@CARepository.route('/SelectIndicator', methods=['GET'])
def selectIndicator() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	action = request.args.get('action')
	
	# check if user is permitted to add an Indicator
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor]:
		return(render_template('main.html', message="Error: User does not have permission to add an Indicator."))
	
	# reset g_organization to be the same as the user's
	if (g_user.userType == cidsrep.admin) or (g_user.userType == cidsrep.editor) : g_organization = g_user.forOrganization
	
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditIndicator"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteIndicator"
	elif action == "compare" :
		path = "http://localhost:5000/SimilarIndicator"
	else :
		return(render_template('main.html', message="Error: Unknown Indicator action: " + action))
	
	inds = cadr.search(type=cids.Indicator, definedBy=g_organization) if g_organization else []
	
	if not inds and (action == "display"): return(render_template('main.html', message="Error: No indicators to display."))
	indSelect = dict()
	for ind in inds: indSelect[ind.iri] = ind.hasName
	
	return(render_template('indicatorSelect.html', path=path, action=action, indicators=indSelect))

@CARepository.route('/EditIndicator', methods=['POST', 'GET'])
def editIndicator() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	if request.method == 'POST':
		action = request.form['action']
		indIRI = request.form['indIRI']
	else :
		action = "display"
		indIRI = request.args.get('indIRI')

	print("indIRI=", indIRI)
	path = "http://localhost:5000/UpdateIndicator"
	
	if (g_user.userType == cidsrep.Researcher) and (action != 'display') :
		return(render_template('main.html', message="Error: User does not have permission to add/edit/delete an Indicator."))
	
	ind = cadr.search_one(type=cids.Indicator, iri=indIRI)
	if not ind : return(render_template('main.html', message="Error: Edit Indicator " + indIRI + " does not exist."))
	
	if not canModify(g_user, ind) : 
		return(render_template('main.html', message="Error: User does not have permission to add/edit/delete the Indicator."))
	
	return(renderIndicator(ind, action, path, "readonly", ""))
		
def canModify(user, entity) :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	og = entity.definedBy if type(entity) in [cids.Indicator, cids.Outcome] else entity.forOrganization
	if user.userType == cidsrep.superuser : return(True)
	elif user.userType == cidsrep.admin :
		if user.forOrganization == og : return(True)
	elif user.userType == cidsrep.editor :
		if user.forOrganization == og: return(True)
	return(False)

@CARepository.route('/UpdateIndicator', methods=['POST'])
def updateIndicator() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	# check if user is permitted to add an Indicator
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor]:
		return(render_template('main.html', message="Error: User does not have permission to add/update an Indicator."))
		
	# verify returned orgID 
	if (g_user.userType == cidsrep.admin) or (g_user.userType == cidsrep.editor) :
		if request.form['orgID'] != g_user.forOrganization.hasID.hasIdentifier :
			return(render_template('main.html', message="Error: Organization ID mismatch: req=" + request.form['orgID'] + "; g_org=" + g_user.forOrganization.hasID.hasIdentifier ))
	else:
		oid = cadr.search_one(type=org.OrganizationID, hasIdentifier=request.form['orgID']) if request.form['orgID'] else None
		g_organization = oid.forOrganization  if oid else None	# set g_organization to superuser specified organization
	
	# check if Indicator already exists for the org and doing add
	indIRI = flask.unescape(request.form['indIRI'])
	
	ind = cadr.search_one(type=cids.Indicator, iri=indIRI) if indIRI else None
	
	if not ind and (request.form['action'] == 'edit') :
		return(render_template('main.html', message="Error: Indicator not found in database."))
	
	if request.form['action'] == 'add' : # create new Indicator
		ind = cids.Indicator(namespace=cadr)
		ind.definedBy = g_organization
		
		# NEED TO UPDATE CODE SO IF THERE IS MORE THAN ONE IMPACT MODEL, IT REQUESTS WHICH ONE
		if g_organization : g_impactModel.hasIndicator.append(ind)

			
	ind.hasName = request.form['hasName']
	ind.hasDescription = request.form['hasDescription']
	ind.hasBaseline = i72.Measure(namespace=cadr, hasNumercalValue=request.form['hasBaseline'], hasUnit=None)
	ind.hasThreshold = i72.Measure(namespace=cadr, hasNumercalValue=request.form['hasThreshold'], hasUnit=None)

	
	# define the optional standard
	indst = cadr.search_one(type=cids.IndicatorStandard, forOrganization = getOrganization(request.form['stOrgID']), hasIdentifier=request.form['stHasIdentifier'])
	mess = "Standard organization of standard ID not found." if indst else ""
		
	logIndividual("Update Indicator", ind, ind.hasBaseline, ind.hasThreshold )
	return(renderIndicator(ind, "display", None, "readonly", "Indicator " + ind.hasName + " added. " + mess ))


def renderIndicator(ind, action, path, readonly, message) :
	global g_user, g_organization, g_impactModel, cidsServer
	
	orgIDValue = g_user.forOrganization.hasID.hasIdentifier 
	hasNameValue = ind.hasName if ind else ''
	hasDescriptionValue = ind.hasDescription if ind else ""
	located_inValue = ind.located_in if ind else None
	hasBaselineValue = None
	hasThresholdValue = None
	hasBaselineValue = ind.hasBaseline.hasNumercalValue if ind.hasBaseline else None
	hasThresholdValue = ind.hasThreshold.hasNumercalValue if ind.hasThreshold else None
		
	return(render_template("indicatorEdit.html", action=action, path=path, indIRIValue=ind.iri,
		orgIDValue = orgIDValue,
		hasNameValue = hasNameValue,
		hasDescriptionValue = hasDescriptionValue,
		located_inValue = located_inValue,
		hasBaselineValue = hasBaselineValue,
		hasThresholdValue = hasThresholdValue))

@CARepository.route('/DeleteIndicator', methods=['POST'])
def deleteIndicator() :
	global g_user, g_organization, g_impactModel, cidsServer
	
	# check if user is permitted to add an Indicator
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor]:
		return(render_template('main.html', message="Error: User does not have permission to delete an Indicator."))
	
	ind = cadr.search_one(type=cids.Indicator, iri=request.form['indIRI'])
	if not ind : return(render_template('main.html', message="Error: Delete Indicator " + request.form['hasName'] + " does not exist."))
	if  (g_user.userType in [cidsrep.admin, cidsrep.editor]) and (g_user.forOrganization != ind.definedBy):
		return(render_template('main.html', message="Error: User does not have permission to delete an Indicator not defined by their Organization."))
	
	if not canModify(g_user, ind) :
		return(render_template('main.html', message="Error: User does not have permission to delete Indicator."))
	
	logIndividual("Delete Indicator", ind)
	destroy_entity(ind)
	return(render_template('main.html',  message="Deleted Indicator " + request.form['indIRI'] + "."))
	
@CARepository.route('/SimilarIndicator', methods=['GET'])
def oldsimilarIndicator() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	inds = cadr.search(type=cids.Indicator, definedBy=g_organization)
	indSelect = dict()
	for ind in inds: indSelect[ind.iri] = ind.hasName
	return(render_template('indicatorSelect.html', indicators=indSelect, action="compare", path="http://localhost:5000/FindSimilarIndicator"))
	
@CARepository.route('/FindSimilarIndicator', methods=['POST'])
def findSimilarIndicator() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer

	if request.form["indIRI"] :
		queryIndicator = cadr.search_one(type=cids.Indicator, iri=request.form["indIRI"])
		queryDescription = queryIndicator.hasDescription
		mess = str(queryIndicator) + "; " + queryDescription
	elif request.form["hasDescription"] :
		queryDescription = request.form["hasDescription"]
		mess = ""
	else :
		return(render_template('main.html', message="no indicator or description provided."))
		
	result = indicatorDistance(queryDescription)
	resultTable = []
	for ind, dist in result: resultTable.append((ind.hasName, ind.iri, ind.hasDescription, dist))
	
	return(render_template('displayDistance.html', result=resultTable, query=queryDescription, message=mess))
	
def indicatorDistance(query) :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	# find all indicators
	inds = dict()
	indIndex = []	
	for ind in cadr.search(type=cids.Indicator) :
		if ind.hasDescription : 
			inds[ind] = ind.hasDescription
			indIndex.append(ind)
	
	# tokenize words
	for key in inds : inds[key] = [ w.lower() for w in word_tokenize(inds[key]) ]

	# create the dictionary mapping words to id
	dictionary = gensim.corpora.Dictionary([inds[key] for key in inds])

	# create a word count (bag of words)
	corpus = [ dictionary.doc2bow(inds[key]) for key in inds ]

	# Perform TFIDF analysis on inds
	tf_idf = gensim.models.TfidfModel(corpus)

	# create index in indDist
	sims = gensim.similarities.Similarity('indDist/',tf_idf[corpus], num_features=len(dictionary))

	# create query
	query_doc = [w.lower() for w in word_tokenize(query) ]
	query_doc_bow = dictionary.doc2bow(query_doc)
	query_doc_tf_idf = tf_idf[query_doc_bow]

	for doc in tf_idf[corpus]:
		print([[dictionary[id], np.around(freq, decimals=2)] for id, freq in doc])
	simRes = sims[query_doc_tf_idf]
	
	result =[]
	for pos in range(len(simRes)) :
		result.append((indIndex[pos], simRes[pos]))
	return(result)

#--------------- Outcome  -------------------------------------------------------------

@CARepository.route('/AddOutcome')
def addOutcome() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer

	orgID = g_organization.hasID.hasIdentifier if g_organization and g_organization.hasID else None
	domains = genDomains()
	stakeholders, stknames = genStakeholders(None)

	if (g_user.userType == cidsrep.superuser) : return(render_template('outcomeEdit.html', 
			path = "http://localhost:5000/UpdateOutcome",
			domains=domains, stakeholders=stakeholders, names=stknames, orgIDValue=orgID, action="add" ))
	
	if g_user.userType in [cidsrep.admin, cidsrep.editor] : 
		return(render_template('outcomeEdit.html', domains=domains, stknames=stknames,
			stakeholders=stakeholders, path = "http://localhost:5000/UpdateOutcome", 
			orgIDValue=orgID, readonly="readonly", action="add"))
	
	return(render_template('main.html', message="AddOutcome Error: User does not have permission to add an Outcome."))
	
@CARepository.route('/SelectOutcome', methods=['GET'])
def selectOutcome() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	action = request.args.get('action')
	print("select: action=", action)
	
	# check if user is permitted to add an Outcome
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor]:
		return(render_template('main.html', message="Error: User does not have permission to add an Outcome."))
	
	# reset g_organization to be the same as the user's
	if (g_user.userType == cidsrep.admin) or (g_user.userType == cidsrep.editor) : g_organization = g_user.forOrganization
	
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditOutcome"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteIOutcome"
	elif action == "compare" :
		path = "http://localhost:5000/SimilarOutcome"
	else :
		return(render_template('main.html', message="Error: Unknown Outcome action: " + action))
	
	outs = cadr.search(type=cids.Outcome, definedBy=g_organization) if g_organization else []
	
	if not outs and (action == "display"): return(render_template('main.html', message="Error: No Outcomes to display."))
	outSelect = dict()
	for out in outs: outSelect[out.iri] = out.hasName
	
	orgID = g_organization.hasID.hasIdentifier if g_organization else ""
	
	return(render_template('outcomeSelect.html', path=path, action=action, outcomes=outSelect, orgIDValue=orgID))


@CARepository.route('/EditOutcome', methods=['POST', 'GET'])
def editOutcome() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	if request.method == 'POST':
		action = request.form['action']
		outIRI = request.form['outIRI']
	else :
		action = "display"
		outIRI = request.args.get('outIRI')
	
	path = "http://localhost:5000/UpdateIOutcome"
	
	# check if user is permitted to add an Outcome
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor]:
		return(render_template('main.html', message="Error: User does not have permission to add/Edit an Outcome."))
	
	if not g_organization : return(render_template('main.html', message="Error: Editing organization not defined."))
	
	ro = "readonly" if g_user.userType != cids.superuser else ""
	
	if action == "add" : # this should not occur as AddOutcome goes directly to the outcomeEdit.html page
		return(render_template("outcomeEdit.html", path="http://localhost:5000/UpdateOutcome", readonly=ro, orgIDValue=g_organization.hasID.hasIdentifier))
	
	# verify returned orgID 
	#if not verifyOrganization(out.forOrganization) :
	#	return(render_template('main.html', message="Error: Organization ID mismatch: req=" + out.forOrganization.hasID.hasIdentifier + "; g_org=" + g_user.forOrganization.hasID.hasIdentifier ))

	if action in ["edit", "display"] :
		out = cadr.search_one(type=cids.Outcome, iri=request.form["outIRI"])
		print("editoutcome stos: ", out.hasStakeholderOutcome)
		if not out : return(render_template('main.html', message="Error: Outcome does not exist."))
		
		return(renderOutcome(out, action, path, "Outcome " + action + " successful."))
		
	return(render_template("main.html", message="EditOutcome Error: unknown action."))

# get risk value returns the values for an outcome's risk
def getRiskValue(outcome, riskType) :
	for risk in outcome.hasImpactRisk :
		if type(risk) == riskType : return (risk.hasLikelihood, risk.hasDescription)
	return("", "")
	
# generate the list of domains for outcomeEdit.html
def genDomains():
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	domains =[]
	for dom in cidsrep.search(type=cidsrep.UNSDGDomain) : domains.append((dom.iri, dom.description[0]))
	return(domains)
	
# generate list of stakeholders for outcomeEdit.html
def genStakeholders(outcome) :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	stakeholders =[("empty", "")]
	stknames = []
	count = 0
	stks = cadr.search(type=cids.Stakeholder, forOrganization=g_organization)
	stouts = outcome.hasStakeholderOutcome if outcome else []
	print("stouts: ", stouts)
	for stk in stks :
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
		stakeholders.append((stk.iri, stk.hasName))
	if not stakeholders : return(render_template('main.html', message="Error: No Stakeholders defined for this Organization."))
	print(stknames)
	return((stakeholders, stknames))

@CARepository.route('/UpdateOutcome', methods=['POST'])
def updateOutcome() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	action = request.form['action']
	
	# check if user is permitted to add an Outcome
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor]:
		return(render_template('main.html', message="Error: User does not have permission to add an Outcome."))
		
	# verify returned orgID 
	if g_user.userType in [cidsrep.admin, cidsrep.editor] :
		if request.form['orgID'] != g_user.forOrganization.hasID.hasIdentifier :
			return(render_template('main.html', message="Error: Organization ID mismatch: req=" + request.form['orgID'] + "; g_org=" + g_user.forOrganization.hasID.hasIdentifier ))
	else:
		oid = cadr.search_one(type=org.OrganizationID, hasIdentifier=request.form['orgID']) if request.form['orgID'] else None
		g_organization = oid.forOrganization  if oid else None	# set g_organization to superuser specified organization
	
	# check if Outcome already exists for the org and doing add
	out = cadr.search_one(type=cids.Outcome, hasName=request.form['hasName'], forOrganization=g_organization)
	if out and (request.form['action'] == 'add') :
		return(render_template('main.html', message="Error: Outcome with that name already exists."))
	
	if not out and (request.form['action'] == 'edit') :
		return(render_template('main.html', message="Error: Outcome not found in database."))
	
	if request.form['action'] == 'add' : # create new Outcome
		out = cids.Outcome(namespace=cadr, hasStakeholderOutcome = [], forDomain=[], hasImpactRisk=[], canProduce=[])
		out.definedBy = g_organization
		g_impactModel.hasOutcome.append(out)

	out.hasName = request.form['hasName']
	out.hasDescription = request.form['hasDescription']
	
	doms = []
	for domiri in request.form.getlist('forDomain') :
		dom = cidsrep.search_one(type=cids.Domain, iri=domiri)
		if dom : doms.append(dom)
	out.forDomain = doms

	# UPDATE STAKEHOLDER IMPACTs ---------------
	
	# cycle through each of the stakeholders
	names = []
	count = 0
	previousStos = out.hasStakeholderOutcome
	newstos = []   # this list will replace the outcome's previous list incase of deletions
	
	stks = cadr.search(type=cids.Stakeholder, forOrganization=g_organization)
	for stk in stks :
		count += 1
		stk = "forStakeholder" + str(count)
		ser = "ser" + str(count)
		imp = "imp" + str(count)
		if request.form[stk] :
			stk = cadr.search_one(type=cids.Stakeholder, iri=request.form[stk])
			sto = retrieveStakeholderOutcome(out, stk)
			sto.forStakeholder = stk
			sto.hasImportance = request.form[imp]
			sto.isUnderserved = True if request.form[ser] == "Yes" else False
			newstos.append(sto)
			logIndividual("Update Outcome", sto)
	out.hasStakeholderOutcome = newstos
	for sto in previousStos : 
		if not sto in out.hasStakeholderOutcome : 
			logIndividual("Update Outcome - delete stakeholderOutcome", sto)
			destroy_entity(sto)
	
	# UPDATE RISKs ---------------
	
	# add each risk, if specified
	risks = [(cids.EvidenceRisk, "evrl", "evrd"), 
			 (cids.ExternalRisk, "exrl", "exrd"),
			 (cids.StakeholderParticipationRisk, "strl", "strd"),
			 (cids.DropOffRisk, "dorl", "dord"),
			 (cids.EfficiencyRisk, "efrl", "efrd"),
			 (cids.ExecutionRisk, "ecrl", "ecrd"),
			 (cids.AlignmentRisk, "alrl", "alrd"),
			 (cids.EnduranceRisk, "enrl", "enrd"),
			 (cids.UnexpectedImpactRisk, "uirl", "uird") ]

	for riskType, riskl, rdes in risks :
		r = findRisk(out, riskType)
		if request.form[riskl] :
			if not r : 
				r = riskType(namespace=cadr)
				if out.hasImpactRisk :
					out.hasImpactRisk.append(r)
				else :
					out.hasImpactRisk = [r]
			r.hasLikelihood = request.form[riskl]
			r.hasDescription = request.form[rdes]
			r.forOutcome = out
			logIndividual("Update Outcome", r)
		else : 
			if r : 
				logIndividual("Update Outcome - destroyed ", r)
				destroy_entity(r)
	
	logIndividual("Update Outcome", out)
	return(renderOutcome(out, "display", "", "Outcome " + action + " successful."))
	
def renderOutcome(outcome, action, path, message) :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	orgIDValue = g_organization.hasID.hasIdentifier if g_organization and g_organization.hasID else None
	# dynamically generate the list of domains and stakeholders for the pull down list
	domains = genDomains() # list all domains
	selectedDomains = [dom.iri for dom in outcome.forDomain] # identified domains that were selected
	stakeholders, stknames = genStakeholders(outcome)
	hasNameValue = outcome.hasName
	hasDescriptionValue = outcome.hasDescription

	# Compile list of risk values
	evrlValue, evrdValue = getRiskValue(outcome, cids.EvidenceRisk)
	exrlValue, exrdValue = getRiskValue(outcome, cids.ExternalRisk)
	strlValue, strdValue = getRiskValue(outcome, cids.StakeholderParticipationRisk)
	dorlValue, dordValue = getRiskValue(outcome, cids.DropOffRisk)
	efrlValue, efrdValue = getRiskValue(outcome, cids.EfficiencyRisk)
	ecrlValue, ecrdValue = getRiskValue(outcome, cids.ExecutionRisk)
	alrlValue, alrdValue = getRiskValue(outcome, cids.AlignmentRisk)
	enrlValue, enrdValue = getRiskValue(outcome, cids.EnduranceRisk)
	uirlValue, uirdValue = getRiskValue(outcome, cids.UnexpectedImpactRisk)
	
	return(render_template("outcomeEdit.html", path=path, action=action,
		domains=domains, selectedDomains=selectedDomains, stakeholders=stakeholders, stknames = stknames,
		message=message ,
		orgIDValue = orgIDValue ,
		hasNameValue = hasNameValue ,
		hasDescriptionValue = hasDescriptionValue ,
		evrlValue = evrlValue ,
		evrdValue = evrdValue ,
		exrlValue = exrlValue ,
		exrdValue = exrdValue ,
		strlValue = strlValue ,
		strdValue = strdValue ,
		dorlValue = dorlValue ,
		dordValue = dordValue ,
		efrlValue = efrlValue ,
		efrdValue = efrdValue ,
		ecrlValue = ecrlValue , 
		ecrdValue = ecrdValue ,
		alrlValue = alrlValue ,
		alrdValue = alrdValue ,
		enrlValue = enrlValue ,
		enrdValue = enrdValue ,
		uirlValue = uirlValue ,
		uirdValue = uirdValue
		))

# retrieve stakeholderoutcome finds the existing stout, if it exists, otherwise creates it
def retrieveStakeholderOutcome(outcome, stk) :
	for sto in outcome.hasStakeholderOutcome :
		if sto.forStakeholder == stk :
			return(sto)
	return(cids.StakeholderOutcome(namespace=cadr, hasImpactReport=[], isUnderserved=None, intendedImpact="", hasIndicator=[], hasImportance="", fromPerspectiveOf = None, forStakeholder=None))

	
def findRisk(outcome, riskType) :
	for r in outcome.hasImpactRisk :
		if type(r) == riskType: return(r)
	return(None)


#--------------- Impact Report  -------------------------------------------------------------

@CARepository.route('/AddImpactReport')
def addImpactReport() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer

	ro = "readonly" if g_user.userType != cidsrep.superuser else ""

	if g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor, cidsrep.reporter] : 
		return(render_template('impactReportEdit.html', path= "http://localhost:5000/UpdateImpactReport", 
			readonly=ro, action="add", priorValue=dict()))
	
	return(render_template('main.html', message="AddImpactReport Error: User does not have permission to add an Impact Report."))
	
@CARepository.route('/SelectImpactReport', methods=['GET'])
def selectImpactReport() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	action = request.args.get('action')
	
	# check if user is permitted to add an Outcome
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor, cidsrep.reporter]:
		return(render_template('main.html', message="Error: User does not have permission to add/edit an Impact Report."))
	
	if not g_impactModel.hasImpactReport and (action in [ "display", "edit", "delete" ]) : 
		return(render_template('main.html', message="Error: No ImpactReports to edit/display."))
		
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditImpactReport"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteImpactReport"
	else :
		return(render_template('main.html', message="Error: Unknown ImpactReport action: " + action))
	
	return(render_template('impactReportSelect.html', path=path, action=action))


@CARepository.route('/EditImpactReport', methods=['POST'])
def editImpactReport() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer

	action = request.form['action']
	irIRI = request.form['irIRI']

	
	path = "http://localhost:5000/UpdateImpactReport"
	
	# check if user is permitted to add an Outcome
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor, cidsrep.reporter]:
		return(render_template('main.html', message="Error: User does not have permission to add/Edit an Impact Report."))
	
	if not g_organization : return(render_template('main.html', message="Error: Editing organization not defined."))
	
	ro = "readonly" if g_user.userType != cids.superuser else ""

	if action in ["edit", "display"] :
		imprep = cadr.search_one(type=cids.ImpactReport, iri=irIRI)
		if not imprep : return(render_template('main.html', message="Error: Impact Report does not exist: " + irIRI))
		return(renderImpactReport(imprep, action, path, "ImpactReport " + action + " successful."))
		
	return(render_template("main.html", message="EditImpactReport Error: unknown action."))


@CARepository.route('/UpdateImpactReport', methods=['POST'])
def updateImpactReport() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	action = request.form['action']
	irIRI = request.form['irIRI']
	
	# check if user is permitted to add an ImpactReport
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor, cidsrep.reporter]:
		return(render_template('main.html', message="Error: User does not have permission to add an ImpactReport."))
	
	if action == 'add' : # create new Outcome
		imprep = cids.ImpactReport(namespace=cadr)
		imprep.forOrganization = g_organization
		g_impactModel.hasImpactReport.append(imprep)
	else :
		imprep = cadr.search_one(type=cids.ImpactReport, iri=irIRI)
		if not imprep : return(render_template('main.html', message="Error: ImpactReport not found in database: " + irIRI))

	imprep.forOutcome = cadr.search_one(type=cids.Outcome, iri=request.form['forOutcome'])
	imprep.hasExpectation = request.form['hasExpectation']
	imprep.hasComment = request.form['hasComment']
	imprep.hasTimeInterval = genTimeInterval(imprep.hasTimeInterval, std = request.form['hasStartDate'], ed = request.form['hasEndDate'])
		
	# encode scale
	indIRI = request.form['scaleForIndicator']
	print("scale indicator iri: ", indIRI)
	if indIRI and not (indIRI == "None") :
		if not imprep.hasImpactScale : imprep.hasImpactScale = cids.ImpactScale(namespace=cadr)
		imprep.hasImpactScale.forIndicator = cadr.search_one(type=cids.Indicator, iri=indIRI)
		imprep.hasImpactScale.hasValue = i72.Measure(namespace=cadr, hasNumericalValue=request.form['scaleValue'])
		if not imprep.hasImpactScale.hasCounterfactual: imprep.hasImpactScale.hasCounterfactual = cids.Counterfactual(namespace=cadr)
		imprep.hasImpactScale.hasCounterfactual.hasValue = i72.Measure(namespace=cadr, hasNumericalValue=request.form['scaleCounterfactualValue'])
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
		if not imprep.hasImpactDepth : imprep.hasImpactDepth = cids.ImpactDepth(namespace=cadr)
		imprep.hasImpactDepth.forIndicator = cadr.search_one(type=cids.Indicator, iri=indIRI)
		imprep.hasImpactDepth.hasValue = i72.Measure(namespace=cadr, hasNumericalValue=request.form['depthValue'])
		if not imprep.hasImpactDepth.hasCounterfactual: imprep.hasImpactDepth.hasCounterfactual = cids.Counterfactual(namespace=cadr)
		imprep.hasImpactDepth.hasCounterfactual.hasValue = i72.Measure(namespace=cadr, hasNumericalValue=request.form['depthCounterfactualValue'])
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
		if not imprep.hasImpactDuration : imprep.hasImpactDuration = cids.ImpactDuration(namespace=cadr)
		impdur = imprep.hasImpactDuration 
		impdur.forIndicator = cadr.search_one(type=cids.Indicator, iri=indIRI)
		impdur.hasValue = i72.Measure(namespace=cadr, hasNumericalValue=request.form['durationValue'])
		if not impdur.hasCounterfactual: impdur.hasCounterfactual = cids.Counterfactual(namespace=cadr)
		impdur.hasCounterfactual.hasValue = i72.Measure(namespace=cadr, hasNumericalValue=request.form['durationCounterfactualValue'])
		impdur.hasCounterfactual.hasDescription = request.form['durationCounterfactualHasDescription']
		logIndividual("Update ImpactReport duration", impdur, impdur.hasValue, impdur.hasCounterfactual, impdur.hasCounterfactual.hasValue)
		impdur.hasTimeInterval = genTimeInterval(impdur.hasTimeInterval, std = request.form['durationHasStartDate'], ed = request.form['durationHasEndDate'])
	elif imprep.hasImpactDuration :
		imp = imprep.hasImpactDuration
		logIndividual("Update ImpactReport - delete duration", imp)
		delete_entity(imp)
	
	logIndividual("Update ImpactReport", imprep)
	if not imprep in g_impactModel.hasImpactReport :
		g_impactModel.hasImpactReport.append(imprep)
		logIndividual("Update ImpactReport", g_impactModel)
	if not imprep in imprep.forOutcome.hasImpactReport :
		imprep.forOutcome.hasImpactReport.append(imprep)
		logIndividual("Update ImpactReport", g_impactModel.forOutcome)
		
	return(renderImpactReport(imprep, "display", "", "ImpactReport " + action + " successful."))
	
@CARepository.route('/DeleteImpactReport', methods=['POST'])
def deleteImpactReport() :
	global g_user, g_organization, g_impactModel, cidsServer
	
	# check if user is permitted to add an Indicator
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor, cids.reporter]:
		return(render_template('main.html', message="Error: User does not have permission to delete an Indicator Report."))
	
	ir = cadr.search_one(iri=request.form['irIRI'])
	
	if not ir : return(render_template('main.html', message="Error: Delete Impact Report" + request.form['irIRI'] + " does not exist."))
	
	if  (g_user.userType in [cidsrep.admin, cidsrep.editor]) and (g_user.forOrganization != ir.forOrganization):
		return(render_template('main.html', message="Error: User does not have permission to delete an Impact Report not defined by their Organization."))
	
	hasName = ir.hasName
	logIndividual("Delete Impact Report", ir) # log last version before deleting
	destroy_entity(ir)
	return(render_template('main.html',  message="Deleted Impact Report: " + hasName))
	
def renderImpactReport(imprep, action, path, message) :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
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


#--------------- Indicator Report  -------------------------------------------------------------

@CARepository.route('/AddIndicatorReport')
def addIndicatorReport() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer

	ro = "readonly" if g_user.userType != cidsrep.superuser else ""

	if g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor, cidsrep.reporter] : 
		return(renderIndicatorReport(None, "add", "http://localhost:5000/UpdateIndicatorReport", ""))
	
	return(render_template('main.html', message="AddImpactReport Error: User does not have permission to add an Impact Report."))
	
@CARepository.route('/SelectIndicatorReport', methods=['GET'])
def selectIndicatorReport() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	action = request.args.get('action')
	
	# check if user is permitted to add an Outcome
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor, cidsrep.reporter]:
		return(render_template('main.html', message="Error: User does not have permission to add/edit an Indicator Report."))
	
	if not g_impactModel.hasIndicatorReport and (action in [ "display", "edit", "delete" ]) : 
		return(render_template('main.html', message="Error: No IndicatorReports to edit/display."))
		
	if (action == "edit") or (action == "display") :
		path = "http://localhost:5000/EditIndicatorReport"
	elif action == "delete" :
		path = "http://localhost:5000/DeleteIndicatorReport"
	else :
		return(render_template('main.html', message="Error: Unknown IndicatorReport action: " + action))
	
	return(render_template('indicatorReportSelect.html', path=path, action=action))
	
@CARepository.route('/EditIndicatorReport', methods=['POST'])
def editIndicatorReport() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer

	action = request.form['action']
	irIRI = request.form['irIRI']
	path = "http://localhost:5000/UpdateIndicatorReport"
	
	# check if user is permitted to add an Indicator Report
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor, cidsrep.reporter]:
		return(render_template('main.html', message="Error: User does not have permission to add/Edit an Indicator Report."))
	
	if not g_organization : return(render_template('main.html', message="Error: Editing organization not defined."))
	
	ro = "readonly" if g_user.userType != cids.superuser else ""

	if action in ["edit", "display"] :
		indrep = cadr.search_one(type=cids.IndicatorReport, iri=irIRI)
		if not indrep : return(render_template('main.html', message="Error: Indicator Report does not exist: " + irIRI))
		return(renderIndicatorReport(indrep, action, path, ""))
		
	return(render_template("main.html", message="EditImpactReport Error: unknown action."))


@CARepository.route('/UpdateIndicatorReport', methods=['POST'])
def updateIndicatorReport() :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	action = request.form['action']
	irIRI = request.form['irIRI']
	
	# check if user is permitted to add an ImpactReport
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor, cidsrep.reporter]:
		return(render_template('main.html', message="Error: User does not have permission to add/edit an Indicator Report."))
	
	if action == 'add' : # create new Outcome
		indrep = cids.IndicatorReport(namespace=cadr)
		indrep.forOrganization = g_organization
		g_impactModel.hasIndicatorReport.append(indrep)
	else :
		indrep = cadr.search_one(type=cids.IndicatorReport, iri=irIRI)
		if not indrep : return(render_template('main.html', message="Error: IndicatorReport not found in database: " + irIRI))

	indrep.hasName = request.form['hasName']
	indrep.forIndicator = cadr.search_one(type=cids.Indicator, iri=request.form['forIndicator'])
	indrep.hasValue = i72.Measure(namespace=cadr, hasNumericalValue=request.form['hasValue'])
	indrep.hasTimeInterval = genTimeInterval(indrep.hasTimeInterval, std = request.form['hasStartDate'], ed = request.form['hasEndDate'])
	indrep.hasComment = request.form['hasComment']
	logIndividual("Update IndicatorReport", indrep)

	return(renderIndicatorReport(indrep, "display", path, "Indicator Report Created/Updated"))

@CARepository.route('/DeleteIndicatorReport', methods=['POST'])
def deleteIndicatorReport() :
	global g_user, g_organization, g_impactModel, cidsServer
	
	# check if user is permitted to add an Indicator
	if not g_user.userType in [cidsrep.superuser, cidsrep.admin, cidsrep.editor, cids.reporter]:
		return(render_template('main.html', message="Error: User does not have permission to delete an Indicator Report."))
	
	ir = cadr.search_one(iri=request.form['irIRI'])
	
	if not ir : return(render_template('main.html', message="Error: Delete Indicator Report" + request.form['irIRI'] + " does not exist."))
	
	if  (g_user.userType in [cidsrep.admin, cidsrep.editor]) and (g_user.forOrganization != ir.forOrganization):
		return(render_template('main.html', message="Error: User does not have permission to delete an Indicator Report not defined by their Organization."))
	
	hasName = ir.hasName
	logIndividual("Delete Indicator Report", ir) # log last version before deleting
	destroy_entity(ir)
	return(render_template('main.html',  message="Deleted Indicator Report: " + hasName))

def renderIndicatorReport(indrep, action, path, message) :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	
	if len(g_impactModel.hasIndicator) == 0: 
		return(render_template('main.html', message="Error: Impact Model does not have Indicators to report on."))
	
	priorValue = dict()
	priorValue['irIRI'] = indrep.iri if indrep else ""
	priorValue['hasName'] = indrep.hasName if indrep else ""
	priorValue['forIndicator'] = indrep.forIndicator.iri if indrep else ""
	priorValue['hasValue'] = indrep.hasValue.hasNumericalValue if indrep else ""
	priorValue['hasStartDate'] = convertDTDtoYMD(indrep.hasTimeInterval.hasBeginning) if indrep  and indrep.hasValue else ""
	priorValue['hasEndDate'] = convertDTDtoYMD(indrep.hasTimeInterval.hasEnd) if indrep  and indrep.hasValue else ""
	priorValue['hasComment'] = indrep.hasComment if indrep else ""

	return(render_template("indicatorReportEdit.html", path=path, action=action, message=message , priorValue=priorValue))
# ----------------------------------------------------------------------------------------
	
# returns the Organization for the given identifier - handles error if nothing found
def getOrganization(id) :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	result = cadr.search_one(type=org.OrganizationID, hasIdentifier=id)
	if result :
		return(result.forOrganization)
	else :
		return(None)
		
def verifyOrganization(og) :
	if g_user.userType == cidsrep.superuser : return(True)
	if g_user.userType == cidsrep.researcher : return(False)
	if g_user.forOrganization == og : return(True) # assume editor or admin
	return(False)

# generate a time intervale given a prior interval and start and end dates in YMD format
# ti: timeInterval can be None

def genTimeInterval(ti, std, ed) :
	if ti and not (std and ed) :
		logIndividual("Delete time interval - null sd and ed ", ti)
		delete_entity(ti)
		return(None)
	elif std or ed :
		if not ti :
			ti = time.DateTimeInterval(namespace=cadr, hasBegining=None, hasEnd=None)
		ti.hasBeginning = convertYMDtoDTD(std, ti.hasBeginning)
		ti.hasEnd = convertYMDtoDTD(ed, ti.hasEnd)
		logIndividual("Update time interval - time", ti, ti.hasBeginning, ti.hasEnd)
		return(ti)
	return(None)
		

# converts owl-time DateTime into yyyy-mm-dd
def convertDTDtoYMD(dte) :
	if not dte or type(dte) != time.DateTimeDescription: return("")
	return(dte.year + "-" + dte.month + "-" + dte.day)
	
def convertYMDtoDTD(ymd, dte=None) :
	if not ymd : return(None)
	if not dte : dte = time.DateTimeDescription(namespace=cadr)
	dte.year, dte.month, dte.day = ymd.split("-")
	return(dte)
	
def valid_login(email, password) :
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	user = cidsServer.search_one(type=cidsrep.User, hasEmail=email)
#	obj = AES.new('CARepository key2021', AES.MODE_CBC, 'This is an IV456')
#	if user and obj.decrypt(user.password) == password	: return(user)
	if user and user.hasPassword == password	: return(user)
	return(False)
	
def log_the_user_in(user) : 
	global g_user, g_organization, g_impactModel, convLocatedIn, cidsServer
	session['hasEmail'] = user.hasEmail	
	# set the global variable for user
	global g_user, g_organization
	g_user = user
	g_organization = None if user.userType == cidsrep.superuser else user.forOrganization
	# default impact model is the first one, if one exists
	if g_organization and g_organization.hasImpactModel and len(g_organization.hasImpactModel) >= 1:
		g_impactModel = g_organization.hasImpactModel[0]
	else :
		g_impactModel = None

def allowed_file(filename):
	global UPLOAD_FOLDER, ALLOWED_EXTENSIONS
	return(('.' in filename) and (filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS))

def printUser(user, header) :
	print("User info in ", header)
	print("givenName=", user.forPerson.givenName)
	print("familyName=", user.forPerson.familyName)
	print("hasEmail=", user.hasEmail)
	print("hasPassword=", user.hasPassword)
	print("hasPhoneNumber=", user.forPerson.hasTelephone[0].hasPhoneNumber)
	print("forOrganization=", user.forOrganization)

# parser for Canadian addresses
# from ez_address_parser import AddressParser
# ap = AddressParser()
# res = ap.parse("21A Howland Ave, Toronto Ontario M5R 3B2")

# deal with json-ld file uploads
global UPLOAD_FOLDER, ALLOWED_EXTENSIONS
UPLOAD_FOLDER = '/Users/markfox/Dropbox/CSSE Folder/Projects/Common Approach/Repository/jsonUploads'
ALLOWED_EXTENSIONS = {'txt', 'jsonld'}
CARepository.config['UPLOAD-FOLDER'] = UPLOAD_FOLDER

# Set the secret key to some random bytes. Keep this really secret!
CARepository.secret_key = b'_7#y1L"F4Q8zFoX\xec]/'

# open persistent database
cidsServer = default_world
cidsServer.set_backend(filename = dbfile, exclusive=False)
	
print("load ontologies")
cidsrep = cidsServer.get_ontology('http://ontology.eil.utoronto.ca/cids/cidsrep')
cids = cidsServer.get_ontology('http://ontology.eil.utoronto.ca/cids/cids')
cadr = cidsServer.get_ontology('http://ontology.eil.utoronto.ca/cids/cadr')  # instances for the data repository
	
print("set namespaces")
org = cidsServer.get_namespace('http://ontology.eil.utoronto.ca/tove/organization')
ic = cidsServer.get_namespace('http://ontology.eil.utoronto.ca/tove/icontact')
act = cidsServer.get_namespace('http://ontology.eil.utoronto.ca/tove/activity')
i72 = cidsServer.get_namespace('http://ontology.eil.utoronto.ca/ISO21972/iso21972')
time = cidsServer.get_namespace('http://www.w3.org/2006/time')
schema = cidsServer.get_namespace('http://schema.org/')
foaf = cidsServer.get_namespace('http://xmlns.com/foaf/0.1/')

# set of conversion dictionaries
convLocatedIn = dict()
convLocatedIn['local'] = cidsrep.locall
convLocatedIn['regional'] = cidsrep.regional
convLocatedIn['provincial'] = cidsrep.provincial
convLocatedIn['national'] = cidsrep.national
convLocatedIn['multinational'] = cidsrep.multinational
convLocatedIn['global'] = cidsrep.globall

# start the repository server on port 5000 $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

g_user = None
g_organization = None
g_impactModel = None

print("starting server")
CARepository.run(debug=True)
	
# close database before exiting
cidsServer.save()
session.pop('hasEmail', None)  # remove email from session
session.pop('forOrganization', None)  # remove email from session
