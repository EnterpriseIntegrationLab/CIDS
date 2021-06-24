from rdflib import Graph
# import json, rdflib_jsonld
# from rdflib.plugin import register, Serializer
# from SPARQLWrapper import SPARQLWrapper
# register('json-ld', Serializer, 'rdflib_jsonld.serializer', 'JsonLDSerializer')

g = Graph()
path = "example.json-ld"
g.parse(path, format="json-ld")
j = g.serialize(format="nt")
filename, ext = path.split(".")
with open(filename + ".nt", 'w') as f: f.write(str(j))
f.close()
