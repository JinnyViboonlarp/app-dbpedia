"""app.py

Wrapping DBpedia Spotlight to do named entity recognition and linking.

Usage:

$ python app.py -t example-mmif.json out.json
$ python app.py [--develop]

The first invocation is to just test the app without running a server. The
second is to start a server, which you can ping with

$ curl -H "Accept: application/json" -X POST -d@example-mmif.json http://0.0.0.0:5000/

With the --develop option you get a FLask server running in development mode,
without it Gunicorn will be used for a more stable server.

Normally you would run this in a Docker container, see README.md.

"""

import os
import sys
import re
import collections
import json
import urllib
import argparse

import spacy

from clams.app import ClamsApp
from clams.restify import Restifier
from clams.appmetadata import AppMetadata
from mmif.serialize import Mmif
from mmif.vocabulary import AnnotationTypes, DocumentTypes
from lapps.discriminators import Uri

# Load small English core model
nlp = spacy.blank('en')
# add the dbpedia_spotlight pipeline stage
nlp.add_pipe('dbpedia_spotlight')

APP_VERSION = '0.0.8'
APP_LICENSE = 'Apache 2.0'
MMIF_VERSION = '0.4.0'
MMIF_PYTHON_VERSION = '0.4.6'
CLAMS_PYTHON_VERSION = '0.5.1'
SPACY_VERSION = '3.1.2'
SPACY_LICENSE = 'MIT'


# We need this to find the text documents in the documents list
TEXT_DOCUMENT = os.path.basename(str(DocumentTypes.TextDocument))

DEBUG = False
semi_truecase_choice = False # choice to capitalize the already-recognized named entities

app_identifier = 'https://apps.clams.ai/dbpedia_spotlight'

def overlap(e1_range, e2_range): # tuple parameter is not supported in Python 3. So I have to unpack it
    (start_e1, end_e1) = e1_range
    (start_e2, end_e2) = e2_range
    if((start_e1 < end_e2) and (end_e1 > start_e2)): # in other words, (start_e1 <= (end_e2-1)) and ((end_e1-1) >= start_e2)
        return True
    return False

class SpacyApp(ClamsApp):

    def _appmetadata(self):
        metadata = AppMetadata(
            identifier=app_identifier,
            url='https://github.com/JinnyViboonlarp/app-dbpedia',
            name="spaCy-wrapped DBpedia Spotlight",
            description="Link named entities in an MMIF file with its DBpedia's information.",
            app_version=APP_VERSION,
            app_license=APP_LICENSE,
            analyzer_version=SPACY_VERSION,
            analyzer_license=SPACY_LICENSE,
            mmif_version=MMIF_VERSION
        )
        metadata.add_input(DocumentTypes.TextDocument)
        if(semi_truecase_choice):
            metadata.add_input(Uri.NE)
        metadata.add_output(Uri.NE)
        return metadata

    def _annotate(self, mmif, **kwargs):

        def get_view_with_ne(views):
            # input: list of views that have annotations anchored on the same document.
            # output: the view with NE annotation. If there are many views, only the last is returned
            views.reverse()
            for view in views:
                if(Uri.NE in list(view['metadata']['contains'].keys()) and view['metadata']['app'] != app_identifier):
                    return view
            return None

        Identifiers.reset()
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        for doc in text_documents(self.mmif.documents):
            if(semi_truecase_choice):
                doc_view = get_view_with_ne(self.mmif.get_views_for_document(doc.id))
            else:
                doc_view = None
            new_view = self._new_view(doc.id)
            self._add_tool_output(doc, doc_view, new_view)
        for view in list(self.mmif.views):
            docs = self.mmif.get_documents_in_view(view.id)
            if docs:
                new_view = self._new_view()
                for doc in docs:
                    doc_id = view.id + ':' + doc.id
                    if(semi_truecase_choice):
                        doc_view = get_view_with_ne(self.mmif.get_views_for_document(doc_id))
                    else:
                        doc_view = None
                    self._add_tool_output(doc, doc_view, new_view, doc_id=doc_id)
                     
        return self.mmif

    def _new_view(self, docid=None):
        view = self.mmif.new_view()
        self.sign_view(view)
        view.new_contain(Uri.NE, document=docid)
        return view

    def _read_text(self, textdoc):
        """Read the text content from the document or the text value."""
        if textdoc.location:
            fh = urllib.request.urlopen(textdoc.location)
            text = fh.read().decode('utf8')
        else:
            text = textdoc.properties.text.value
        if DEBUG:
            print('>>> %s%s' % (text.strip()[:100],
                                ('...' if len(text) > 100 else '')))
        return text

    def _add_tool_output(self, doc, doc_view, view, doc_id=None):

        def get_annotations_with_doc_id(annotations, doc_id):
            # filter only annotations with the specified doc_id
            # if doc_id == None, return all annotations
            if doc_id == None:
                return [annotation for annotation in annotations]
            else:
                return [annotation for annotation in annotations if ("document" in annotation.properties and \
                        annotation.properties["document"] == doc_id)]

        def find_dbpedia_type(ent):
            # select only interested types of entities
            prefix = 'DBpedia:'
            interested_types = ['Person','Place','Organisation','Device']
            try:
                types_list = ent._.dbpedia_raw_result['@types'].split(',')
                for category in interested_types:
                    if (prefix+category) in ent._.dbpedia_raw_result['@types']:
                        return category
            except:
                return None
            return None

        text_orig = self._read_text(doc)
        input_text = text_orig
        if(doc_view != None):
            ne_annotations = doc_view.get_annotations(at_type=Uri.NE)
            ne_annotations = get_annotations_with_doc_id(ne_annotations, doc_id)
            # store named entities in doc_view in a dict, using (start, end) as key
            entity_dict = {}
            for annotation in ne_annotations:
                entity_properties = annotation.properties
                entity_dict[(entity_properties['start'],entity_properties['end'])] = entity_properties

        # there is an option that the text is 'semi-truecased' (i.e. only named entities are capitalized) \
        # before going to the dbpedia pipeline. This is necessary if the text is lowercase since dbpedia \
        # has low recall for uncased person names.
        if(semi_truecase_choice == True): # which also mean that doc_view != None
            input_text_list = list(input_text.lower()) # python string is immutable, but we want to modify input_text
            for (start, end) in entity_dict.keys():
                entity_text = input_text[start:end]
                for m in re.finditer(r'\S+', entity_text):
                    capitalized_index = (start + m.start())
                    input_text_list[capitalized_index] = input_text_list[capitalized_index].upper()
            input_text = "".join(input_text_list)
            #print(input_text)

        # since dbpedia_spotlight calls outside database, there is a slim chance that it will fail \
        # we will loop here until it succeeds
        calling_success = False
        while(calling_success == False):
            try:
                spacy_doc = nlp(input_text)
                calling_success = True
            except:
                pass

        # keep track of char offsets of all tokens
        tok_idx = {}
        for (n, tok) in enumerate(spacy_doc):
            p1 = tok.idx
            p2 = p1 + len(tok.text)
            tok_idx[n] = (p1, p2)

        # do an NER task
        for (n, ent) in enumerate(spacy_doc.ents):
            start = tok_idx[ent.start][0]; end = tok_idx[ent.end - 1][1]
            category = find_dbpedia_type(ent)
            if(category != None):
                properties = { "text": text_orig[start:end], "kb_category": category, "kb_id": ent.kb_id_}
                add_annotation(view, Uri.NE, Identifiers.new("ne"), doc_id, start, end, properties)       

def text_documents(documents):
    """Utility method to get all text documents from a list of documents."""
    return [doc for doc in documents if str(doc.at_type).endswith(TEXT_DOCUMENT)]
    # TODO: replace with the following line and remove TEXT_DOCUMENT variable
    # when mmif-python is updated
    # return [doc for doc in documents if doc.is_type(DocumentTypes.TextDocument)]


def add_annotation(view, attype, identifier, doc_id, start, end, properties):
    """Utility method to add an annotation to a view."""
    a = view.new_annotation(attype, identifier)
    if doc_id is not None:
        a.add_property('document', doc_id)
    if start is not None:
        a.add_property('start', start)
    if end is not None:
        a.add_property('end', end)
    for prop, val in properties.items():
        a.add_property(prop, val)

class Identifiers(object):

    """Utility class to generate annotation identifiers. You could, but don't have
    to, reset this each time you start a new view. This works only for new views
    since it does not check for identifiers of annotations already in the list
    of annotations."""

    identifiers = collections.defaultdict(int)

    @classmethod
    def new(cls, prefix):
        cls.identifiers[prefix] += 1
        return "%s%d" % (prefix, cls.identifiers[prefix])

    @classmethod
    def reset(cls):
        cls.identifiers = collections.defaultdict(int)



def test(infile, outfile):
    """Run spacy on an input MMIF file. This bypasses the server and just pings
    the annotate() method on the SpacyApp class. Prints a summary of the views
    in the end result."""
    print(SpacyApp().appmetadata(pretty=True))
    with open(infile) as fh_in, open(outfile, 'w') as fh_out:
        mmif_out_as_string = SpacyApp().annotate(fh_in.read(), pretty=True)
        mmif_out = Mmif(mmif_out_as_string)
        fh_out.write(mmif_out_as_string)
        for view in mmif_out.views:
            print("<View id=%s annotations=%s app=%s>"
                  % (view.id, len(view.annotations), view.metadata['app']))


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--test',  action='store_true', help="bypass the server")
    parser.add_argument('--develop',  action='store_true', help="start a development server")
    parser.add_argument('--truecase',  action='store_true', help="capitalize the already-recognized named entities")
    parser.add_argument('infile', nargs='?', help="input MMIF file")
    parser.add_argument('outfile', nargs='?', help="output file")
    args = parser.parse_args()

    if args.truecase:
        semi_truecase_choice = True

    if args.test:
        test(args.infile, args.outfile)
    else:
        app = SpacyApp()
        service = Restifier(app)
        if args.develop:
            service.run()
        else:
            service.serve_production()
