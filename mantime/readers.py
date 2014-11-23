#!/usr/bin/env python
#
#   Copyright 2014 Michele Filannino
#
#   gnTEAM, School of Computer Science, University of Manchester.
#   All rights reserved. This program and the accompanying materials
#   are made available under the terms of the GNU General Public License.
#
#   author: Michele Filannino
#   email:  filannim@cs.man.ac.uk
#
#   For details, see www.cs.man.ac.uk/~filannim/

"""It contains all the readers for ManTIME.

   A reader must have a parse() method which is responsible for reading the
   input file and return a Document object, which is our internal
   representation of any input document (whetever the format is).

   In order to force the existence of the parse() method I preferred Python
   interfaces to the duck typing practice.
"""

from abc import ABCMeta, abstractmethod
import xml.etree.cElementTree as etree
from StringIO import StringIO
import sys
import os

from nltk import ParentedTree

from model import Document
from model import Sentence
from model import Word
from model import DependencyGraph
from utilities import Mute_stderr
from settings import PATH_CORENLP_FOLDER


class BatchedCoreNLP(object):

    def __init__(self, stanford_dir):
        from corenlp import batch_parse
        self.DIR = stanford_dir
        self.batch_parse = batch_parse

    def parse(self, text):
        import tempfile
        dirname = tempfile.mkdtemp()
        with tempfile.NamedTemporaryFile('w', dir=dirname) as tmp:
            tmp.write(text)
            tmp.flush()
            result = self.batch_parse(os.path.dirname(tmp.name), self.DIR)
            result = list(result)[0]
        return result

with Mute_stderr():
    CORENLP = BatchedCoreNLP(PATH_CORENLP_FOLDER)

class Reader(object):
    """This class is an abstract reader for ManTIME."""
    __metaclass__ = ABCMeta

    @abstractmethod
    def parse(self, text):
        pass


class FileReader(Reader):
    """This classs is an abstract file reader for ManTIME."""
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def parse(self, file_path):
        pass


class TempEval3FileReader(FileReader):
    """This class is a reader for TempEval-3 files."""

    def __init__(self, annotation_format='IO', extension_filter='.tml'):
        super(TempEval3FileReader, self).__init__()
        self.tags_to_spot = {'TIMEX3', 'EVENT', 'SIGNAL'}
        self.annotations = []
        self.annotation_format = annotation_format
        self.extension_filter = extension_filter

    def parse(self, file_path):
        """It parses the content of file_path and extracts relevant information
        from a TempEval-3 annotated file. Those information are packed in a
        Document object, which is our internal representation.
        """
        xml = etree.parse(file_path)
        docid = xml.findall(".//DOCID")[0]
        dct = xml.findall(".//TIMEX3[@functionInDocument='CREATION_TIME']")[0]
        title = xml.findall(".//TITLE")[0]
        text_node = xml.findall(".//TEXT")[0]
        text_string = etree.tostring(text_node, method='text')
        text_xml = etree.tostring(text_node, method='xml')
        right_chars = len(text_xml.split('</TEXT>')[1])
        text_string = text_string[:-right_chars]
        text_xml = etree.tostring(text_node)
        # StanfordParser strips internally the text :(
        left_chars = len(text_string) - len(text_string.lstrip())

        with Mute_stderr():
            stanford_tree = CORENLP.parse(text_string)
        document = Document(file_path)
        document.text_offset = left_chars
        document.file_path = os.path.abspath(file_path)
        document.doc_id = etree.tostring(docid, method='text').strip()
        document.dct = dct.attrib['value']
        document.dct_text = etree.tostring(dct, method='text')
        document.title = etree.tostring(title, method='text').strip()
        document.text = text_string
        document.gold_annotations = self._get_annotations(text_xml, -left_chars)
        document.coref = stanford_tree.get('coref', None)

        for stanford_sentence in stanford_tree['sentences']:
            dependencies = stanford_sentence.get('dependencies', None)
            i_dependencies = stanford_sentence.get('indexeddependencies', None)
            i_dependencies = DependencyGraph(i_dependencies)
            parsetree = ParentedTree(stanford_sentence.get('parsetree', u''))
            sentence_text = stanford_sentence.get('text', u'')

            sentence = Sentence(dependencies=dependencies,
                                indexed_dependencies=i_dependencies,
                                parsetree=parsetree,
                                text=sentence_text)
            for num_word, (word_form, attr) in\
                    enumerate(stanford_sentence['words']):
                offset_begin = int(attr['CharacterOffsetBegin'])-left_chars
                offset_end = int(attr['CharacterOffsetEnd'])-left_chars
                word = Word(word_form=word_form,
                            char_offset_begin=offset_begin,
                            char_offset_end=offset_end,
                            lemma=attr['Lemma'],
                            named_entity_tag=attr['NamedEntityTag'],
                            part_of_speech=attr['PartOfSpeech'],
                            id_token=num_word)
                sentence.words.append(word)
            document.sentences.append(sentence)

        document.store_gold_annotations(self.annotation_format)
        return document

    def _get_annotations(self, source, start_offset=0):
        '''It returns the annotations found in the document in the following
           format:
           [
            ('TAG', {ATTRIBUTES}, (start_offset, end_offset)),
            ('TAG', {ATTRIBUTES}, (start_offset, end_offset)),
            ...
            ('TAG', {ATTRIBUTES}, (start_offset, end_offset))
           ]
        '''
        annotations = []
        for event, element in etree.iterparse(
                StringIO(source), events=('start', 'end')):
            if event == 'start':
                if element.tag in self.tags_to_spot:
                    end_offset = start_offset + len(element.text)
                    annotations.append((element.tag, element.attrib,
                                        (start_offset, end_offset)))
                start_offset += len(element.text)
            elif event == 'end':
                if element.text is not None and element.tail is not None:
                    start_offset += len(element.tail)
        return annotations


Reader.register(FileReader)
FileReader.register(TempEval3FileReader)


def main():
    '''Simple ugly non-elegant test.'''
    import json
    file_reader = TempEval3FileReader(annotation_format='IO')
    document = file_reader.parse(sys.argv[1])
    print json.dumps(document, indent=4)

if __name__ == '__main__':
    main()
