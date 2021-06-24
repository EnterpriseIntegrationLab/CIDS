from owlready2 import *
import gensim
import numpy as np
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize


def indicatorDistance(query) :
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
	
	result = []
	for pos in range(len(simRes)) :
		result.append((indIndex[pos], simRes[pos]))
	return(result)

cidsServer = default_world
cidsServer.set_backend(filename = "/Users/markfox/Dropbox/CSSE Folder/Projects/Common Approach/Repository/db/cidsrepository.sqlite3", exclusive=False)
	
print("set backend")
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

print("cidsrep individuals")
print(list(cidsrep.individuals()))

print("cids individuals")
print(list(cids.individuals()))

print("cadr individuals")
print(list(cadr.individuals()))

result = indicatorDistance('what can we do for the poor')


