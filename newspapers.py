#!/usr/bin/env python


import os
import sys

import rdflib


NEWSPAPERS = 'http://chroniclingamerica.loc.gov/newspapers.rdf'
NEWSPAPERS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'newspapers.rdf')

NS = {
        'dc': rdflib.Namespace('http://purl.org/dc/elements/1.1/'),
        'dcterm': rdflib.Namespace('http://purl.org/dc/terms/'),
        'rdfs': rdflib.Namespace('http://www.w3.org/2000/01/rdf-schema#'),
        'owl': rdflib.Namespace('http://www.w3.org/2002/07/owl#'),
        }


def init():
    rdflib.plugin.register('sparql', rdflib.query.Processor,
                           'rdfextras.sparql.processor', 'Processor')
    rdflib.plugin.register('sparql', rdflib.query.Result,
                           'rdfextras.sparql.query', 'SPARQLQueryResult')

def get_graph(url):
    g = rdflib.Graph()
    g.parse(url)
    return g


def get_preds(g):
    sparql = 'SELECT DISTINCT ?p WHERE { ?s ?p ?o . } ORDER BY ?p'
    return sorted(list(set(q(g, sparql))))


def query_pred(g, pred):
    return q(g, 'SELECT ?s ?o WHERE { ?s %s ?o. }' % (pred,))


def q(g, sparql, ns=NS):
    return g.query(sparql, initNs=ns)


def get_newspapers():
    return get_graph(NEWSPAPERS)


def main():
    init()


if __name__ == '__main__':
    main()

