#!/usr/bin/env python


import os
import random
import sys
import time
from xml.etree import cElementTree as ET

import rdflib
from rdflib import plugin
from rdflib import Namespace, URIRef
from rdflib import Graph


NEWSPAPERS = 'http://chroniclingamerica.loc.gov/newspapers.rdf'
# NEWSPAPERS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
#                           'newspapers.rdf')
BASEDIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE      = os.path.join(BASEDIR, 'data', 'newspapers.sqlite')
OUTPUT     = os.path.join(BASEDIR, 'data', 'newspapers.n3')
KML_OUTPUT = os.path.join(BASEDIR, 'data', 'newspapers.kml')

CC        = Namespace("http://creativecommons.org/ns#")
DC        = Namespace('http://purl.org/dc/elements/1.1/')
DCTERMS   = Namespace('http://purl.org/dc/terms/')
FOAF      = Namespace("http://xmlns.com/foaf/0.1/")
FRBR      = Namespace("http://purl.org/vocab/frbr/core#")
GN        = Namespace("http://www.geonames.org/ontology#")
KML       = Namespace('http://www.opengis.net/kml/2.2')
ORE       = Namespace("http://www.openarchives.org/ore/terms/")
OWL       = Namespace('http://www.w3.org/2002/07/owl#')
RDA       = Namespace("http://rdvocab.info/elements/")
RDF       = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS      = Namespace('http://www.w3.org/2000/01/rdf-schema#')
WGS84_POS = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")

NS = {
        'cc'        : CC,
        'dc'        : DC,
        'dcterms'   : DCTERMS,
        'foaf'      : FOAF,
        'frbr'      : FRBR,
        'gn'        : GN,
        'ore'       : ORE,
        'owl'       : OWL,
        'rda'       : RDA,
        'rdf'       : RDF,
        'rdfs'      : RDFS,
        'wgs84_pos' : WGS84_POS,
        }

K = 125
SLEEP = 1
MAX_ATTEMPTS = 3
FAIL_LOG = 'fails.log'


def init():
    """This initializes rdflib with the SPARQL plugins. """
    plugin.register('sparql', rdflib.query.Processor,
                    'rdfextras.sparql.processor', 'Processor')
    plugin.register('sparql', rdflib.query.Result,
                    'rdfextras.sparql.query', 'SPARQLQueryResult')


#################################################
## These functions load the data into a graph. ##
#################################################


def get_store(filename=STORE):
    """This loads a SQLite 3store. Currently unused and untested. """
    store = plugin.get('SQLite', Store)(filename)

    ret_value = store.open(filename, create=False)
    if ret_value == NO_STORE:
        store.open(filename, create=True)
    else:
        assert ret_value == VALID_STORE, 'The underlying store is corrupt.'

    return store


def parse(g, url):
    """\
    This tries to parse a URL 3 times, writing progress messages and logging
    failure.
    """
    sys.stdout.write('Loading <%s>' % (url,))

    attempt = 0
    while attempt <= MAX_ATTEMPTS:
        sys.stdout.write('...')
        sys.stdout.flush()
        time.sleep(SLEEP)

        try:
            g.parse(str(url))
        except:
            attempt += 1
        else:
            break

    else:
        with open(FAIL_LOG, 'a') as f:
            f.write(url + '\n')
        sys.stdout.write('\tFailed.\n')
        return False

    sys.stdout.write('\t%d triples.\n' % (len(g),))
    return True


def parse_graph(url):
    """This parses a URL into a new graph. """
    g = Graph()
    parse(g, url)
    return g


def get_preds(g):
    """\
    This runs a SPARQL query to get a sorted list of the predicates in a graph.
    """
    sparql = 'SELECT DISTINCT ?p WHERE { ?s ?p ?o . } ORDER BY ?p'
    return sorted(list(set(q(g, sparql))))


def query_pred(g, pred):
    """\
    This returns tuple pairs of all the (subj, obj) in the graph with the
    given predicate.
    """
    return q(g, 'SELECT ?s ?o WHERE { ?s %s ?o. }' % (pred,))


def q(g, sparql, ns=NS):
    """This runs a SPARQL query on a graph. """
    return g.query(sparql, initNs=ns)


def get_newspapers():
    """This parses the NEWSPAPERS URL and returns a new graph. """
    return parse_graph(NEWSPAPERS)


def iter_newspapers(g):
    """This iterates over the newspapers in the graph. """
    return g.subjects(RDF['type'],
                      URIRef('http://purl.org/ontology/bibo/Newspaper'))


def create_sample(g, k=K, s='iri:script/n/sample', p='iri:script/v/member'):
    """\
    This creates a sample of k newspapers from the graph, adds them to a new
    sample object, and returns them.
    """
    sample = random.sample(list(iter_newspapers(g)), k)

    s = URIRef(s)
    p = URIRef(p)
    for newspaper in sample:
        g.add((s, p, newspaper))

    return sample


def load_newspapers(g, newspapers):
    """This loads the data from the individual newspapers into the graph. """
    for item in newspapers:
        parse(g, item)


def load_coverage(g, newspapers):
    """\
    This loads the coverage for all the newspapers in the graph.

    NB: I should probably collapse these loops into one SPARQL query.
    """
    for s in newspapers:
        print('Loading coverage for %s.' % (s,))

        for cov in g.objects(s, DCTERMS['coverage']):
            parse(g, cov)


def load_data(filename=OUTPUT):
    """This loads the data and serializes it. """
    g = get_newspapers()
    sample = create_sample(g)
    load_newspapers(g, sample)
    load_coverage(g, sample)

    print('Serializing to %s.' % (filename,))
    with open(filename, 'w') as f:
        g.serialize(f, format='n3')

    return g


##########################################################################
## These functions load the data created by load_data and generate KML. ##
##########################################################################


def read_data(filename=OUTPUT):
    """This reads the data from load_data into a new graph. """
    sys.stdout.write('Reading <%s>.\n' % (filename,))
    g = Graph()
    g.parse(OUTPUT, format='n3')
    return g


def query_coverage(g):
    """\
    This runs a SPARQL query that returns the title of the newspapers, their
    location, and their lat/longs.

    Actually, this just queries the database, because the parser erroneously
    thinks there's a problem with the query.
    """
    sys.stdout.write('Querying for coverage data.\n')
    sparql = '''
        SELECT ?news ?title ?pub ?locname ?lon ?lat 
        WHERE {
            ?news rdf:type <http://purl.org/ontology/bibo/Newspaper> ;
                  dcterms:title ?title ;
                  dc:publisher ?pub ;
                  rda:placeOfPublication ?loc ;
                  dcterms:coverage ?cov .
            ?cov wgs84_pos:long ?lon ;
                 wgs84_pos:lat ?lat .
        }
        '''

    for news in iter_newspapers(g):
        for title in g.objects(news, DCTERMS['title']):
            for pub in g.objects(news, DC['publisher']):
                for loc in g.objects(news, RDA['placeOfPublication']):
                    for cov in g.objects(news, DCTERMS['coverage']):
                        for lon in g.objects(cov, WGS84_POS['long']):
                            for lat in g.objects(cov, WGS84_POS['lat']):
                                yield (news, title, pub, loc, lon, lat)


def make_kml(coverage, output=KML_OUTPUT):
    """\
    This converts the output of query_coverages and writes it to output as KML.
    """
    sys.stdout.write('Generating KML to <%s>.\n' % (output,))
    kml = ET.Element('kml', xmlns=str(KML))
    doc = ET.SubElement(kml, 'Document')

    for (iri, title, pub, loc, long, lat) in coverage:
        pm = ET.SubElement(doc, 'Placemark')
        ET.SubElement(pm, 'name').text = title
        ET.SubElement(pm, 'description').text = '''
            <strong><a href="%(iri)s">%(title)s</a></strong><br />
            published by %(pub)s in %(loc)s.
            ''' % {
                    'iri'   : iri,
                    'title' : title,
                    'pub'   : pub,
                    'loc'   : loc,
                    }
        p = ET.SubElement(pm, 'Point')
        ET.SubElement(p, 'coordinates').text = '%s,%s' % (long, lat)

    et = ET.ElementTree(kml)
    et.write(output, 'UTF-8')


def data_to_kml(g=None, input=OUTPUT, output=KML_OUTPUT):
    """This reads the data from input and writes it to output as KML. """
    g = (g if g is not None else read_data(input))
    coverage = query_coverage(g)
    make_kml(coverage, output)


##

def main():
    init()
    g = load_data(filename=OUTPUT)
    data_to_kml(g=g, output=KML_OUTPUT)


if __name__ == '__main__':
    main()

