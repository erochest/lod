#!/usr/bin/env python


import rdflib


def init():
    rdflib.plugin.register('sparql', rdflib.query.Processor,
                           'rdfextras.sparql.processor', 'Processor')
    rdflib.plugin.register('sparql', rdflib.query.Result,
                           'rdfextras.sparql.query', 'SPARQLQueryResult')

def main():
    init()


if __name__ == '__main__':
    main()

