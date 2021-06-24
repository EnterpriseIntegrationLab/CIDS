# Contains various ontology reasoning functions

# Creator: Mark S. Fox, msf@eil.utoronto.ca
# Date: 23 January 2021
# Copyright 2021 Mark S. Fox
# Available under: http://creativecommons.org/licenses/by/3.0/

import config
from owlready2 import *
import rdflib
from rdflib import Literal, BNode, URIRef, Graph, Namespace
from rdflib.namespace import RDF, OWL, RDFS, FOAF, XSD

def relatedAll(obj, prop, maxIterations=10000, w=config.cidsServer) :
	"""
		relatedAll finds all objects related to object via the property prop
		It uses both the basic DL properties of transitivity, etc. plus property chains
	
		Parameters
		----------
		obj : 	owl:Thing
					starting object for finding what is related to it by prop
		prop	:	owl:objectPropertyThing
					the property used to find what is related to the object
		
		Returns
		-------
					List of objects related to obj via prop
	"""	
	
	# get the list of property chains for prop
	propertyChains = prop.get_property_chain()
	
	currentObjects = {obj}
	relatedObjects = set()
	propIndirect = "INDIRECT_" + prop.name		# use power of owlready2 to get transitive, symmetric, inverse, etc.
	iteration = 0
	
	while (len(currentObjects) > 0) and (iteration < maxIterations) : 
		iteration += 1
		cObject = currentObjects.pop()
		relatedObjects = relatedObjects | {cObject}
		newObjects = set(getattr(cObject, propIndirect))
		currentObjects = currentObjects | (newObjects - relatedObjects)
	
		# process property chains
		for propertyChain in propertyChains :
			stageSet = {cObject}
			for chainProp in propertyChain :
				newObjects = set()
				chainPropIndirect = "INDIRECT_" + chainProp.name
				while (len(stageSet) > 0) and (iteration < maxIterations) :
					iteration += 1
					cobj = stageSet.pop()
					nobjects = set(getattr(cobj, chainPropIndirect))
					newObjects = newObjects | nobjects
				stageSet = newObjects
			currentObjects = currentObjects | (stageSet - relatedObjects)
	return(relatedObjects - {obj})

	
def related(obj1, prop, obj2, maxIterations=10000) :
	"""
		related determines whether obj1 is directly or indirectly connected to obj2
		using basic DL properties such as transitivity, inverse plus property chains
	
		Parameters
		----------
		obj1, obj2 : 	owl:Thing
					starting and ending objects for finding what is related to it by prop
		prop	:	owl:objectPropertyThing
					the property used to find what is related to the object
		
		Returns
		-------
					Boolean
	"""	
	return(obj2 in relatedAll(obj1, prop, maxIterations=maxIterations))
	
"""
prop: the property for which a property chain is defined
w: the world object in which the data is stored

returns a list of property chains, each sublist comprising a property chain
"""

def getPropertyChain(prop, w=default_world) :
	rdfGraph = w.as_rdflib_graph()
	chains = []
	
	# retrieve the property chains defined for the property
	objs = rdfGraph.objects(URIRef(prop.iri), OWL.propertyChainAxiom)
	
	# cycle through each property chain definition
	for obj in objs :
		chain = []
		# construct the chain for this property chain
		while obj != RDF.nil :
			chain.append(IRIS[str(rdfGraph.value(obj, RDF.first))])
			obj = rdfGraph.value(obj, RDF.rest)
		chains.append(chain)
	return(chains)

