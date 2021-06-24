# Analysis code for CA Repository

# Creator: Mark S. Fox, msf@eil.utoronto.ca
# Date: 23 January 2021
# Copyright 2021 Mark S. Fox
# Available under: http://creativecommons.org/licenses/by/3.0/

import config
import datetime
from owlready2 import *
from flask import Flask, render_template, request, session, redirect, url_for, g, flash
import Util

# modules for measuring distance between text in Indicators
import gensim
import numpy as np
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize

# based on article found at:
# https://dev.to/coderasha/compare-documents-similarity-using-python-nlp-4odp

def distance(query, descriptionType) :

	# find all indicators
	inds = dict()
	indIndex = []	
	for ind in config.cadr.search(type=descriptionType) :
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