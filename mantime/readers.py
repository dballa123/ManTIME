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
import logging
import codecs
import cPickle

from nltk import ParentedTree

from model import Document
from model import Sentence
from model import Word
from model import DependencyGraph
from utilities import Mute_stderr
from settings import PATH_CORENLP_FOLDER
from normalisers.clinical_doc_analyser import DocumentAnalyser


class BatchedCoreNLP(object):
    """It provides an interface to StanfordCoreNLP parser.

    Attributes:
        folder: a string containing the folder path of StanfordCoreNLP
    """

    def __init__(self, stanford_dir):
        self.folder = stanford_dir

    def parse(self, text, folder='../buffer/'):
        """Returns the parsing from file (if already parsed), or computes it.

        Long description...

        Args:
            text: a string containing the text to be parsed
            folder: a string representing the destination folder where the
                caching system dumps the parsing.

        Returns:

        """
        hash_value = str(hash(text))
        dest_file = os.path.join(os.path.abspath(folder), hash_value)
        try:
            return cPickle.load(open(dest_file))
        except IOError:
            return self._parse(text, dest_file)

    def _parse(self, text, dest_file):
        '''Computes the parsing calling Stanford NLP api.

        '''
        import tempfile
        from corenlp import batch_parse
        dirname = tempfile.mkdtemp()
        with tempfile.NamedTemporaryFile('w', dir=dirname, delete=False) as f:
            filename = f.name
        with codecs.open(filename, 'w', encoding='utf8') as tmp:
            tmp.write(text)
            tmp.flush()
            result = batch_parse(os.path.dirname(tmp.name), self.folder)
            result = list(result)[0]
        cPickle.dump(result, open(dest_file, 'w'))
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
        self.file_filter = None

    @abstractmethod
    def parse(self, file_path):
        pass


class TempEval3FileReader(FileReader):
    """This class is a reader for TempEval-3 files."""

    def __init__(self, file_filter='*.tml'):
        super(TempEval3FileReader, self).__init__()
        self.tags_to_spot = {'TIMEX3', 'EVENT'}
        self.annotations = []
        self.file_filter = file_filter

    def parse(self, file_path):
        """It parses the content of file_path and extracts relevant information
        from a TempEval-3 annotated file. Those information are packed in a
        Document object, which is our internal representation.
        """
        logging.info('Document {}: parsing...'.format(
            os.path.relpath(file_path)))
        xml = etree.parse(file_path)
        docid = xml.findall(".//DOCID")[0]
        dct = xml.findall(".//TIMEX3[@functionInDocument='CREATION_TIME']")[0]
        try:
            title = xml.findall(".//TITLE")[0]
        except IndexError:
            title = xml.findall(".//DOCID")[0]
        text_node = xml.findall(".//TEXT")[0]
        text_string = etree.tostring(text_node, method='text', encoding='utf8')
        text_xml = etree.tostring(text_node, method='xml', encoding='utf8')
        text_string = unicode(text_string, 'UTF-8')
        text_xml = unicode(text_xml, 'UTF-8')
        right_chars = len(text_xml.split('</TEXT>')[1])
        text_string = text_string[:-right_chars]
        text_xml = etree.tostring(text_node)
        # StanfordParser strips internally the text :(
        left_chars = len(text_string) - len(text_string.lstrip())

        with Mute_stderr():
            folder = os.path.dirname(file_path)
            stanford_tree = CORENLP.parse(text_string)
        document = Document(file_path)
        document.text_offset = left_chars
        document.file_path = os.path.abspath(file_path)
        document.doc_id = etree.tostring(docid, method='text',
                                         encoding='utf8').strip()
        document.dct = dct.attrib['value']
        document.dct_text = etree.tostring(dct, method='text', encoding='utf8')
        document.title = etree.tostring(title, method='text',
                                        encoding='utf8').strip()
        document.text = text_string
        instances = self._get_event_instances(xml)
        document.gold_annotations = self._get_annotations(text_xml,
                                                          instances,
                                                          -left_chars)
        document.coref = stanford_tree.get('coref', None)

        for stanford_sentence in stanford_tree['sentences']:
            dependencies = stanford_sentence.get('dependencies', None)
            i_dependencies = stanford_sentence.get('indexeddependencies', None)
            # i_dependencies = DependencyGraph(i_dependencies)
            parsetree = stanford_sentence.get('parsetree', u'')
            # parsetree = ParentedTree(parsetree)
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

        document.store_gold_annotations()
        logging.info('Document {}: parsed.'.format(os.path.relpath(file_path)))
        return document

    def _get_annotations(self, source, event_instances, start_offset=0):
        """It returns the annotations found in the document.

        It follows the following format:
           [
            ('TAG', {ATTRIBUTES}, (start_offset, end_offset)),
            ('TAG', {ATTRIBUTES}, (start_offset, end_offset)),
            ...
            ('TAG', {ATTRIBUTES}, (start_offset, end_offset))
           ]

        """
        annotations = []
        for event, element in etree.iterparse(
                StringIO(source), events=('start', 'end')):
            try:
                if event == 'start':
                    if element.tag in self.tags_to_spot:
                        end_offset = start_offset + len(element.text)
                        if element.tag == 'EVENT':
                            eid = element.attrib['eid']
                            if eid in event_instances.keys():
                                element.attrib.update(event_instances[eid])
                        annotations.append((element.tag, element.attrib,
                                            (start_offset, end_offset)))
                    start_offset += len(element.text)
                elif event == 'end':
                    if element.text is not None and element.tail is not None:
                        start_offset += len(element.tail)
            except TypeError:
                        continue
        return annotations

    def _get_event_instances(self, xml_document):
        """It returns the event instances found in the document.

            It follows the following format:
               [
                ('eiid', {ATTRIBUTES}),
                ('eiid', {ATTRIBUTES}),
                ...
                ('eiid', {ATTRIBUTES})
               ]

        """
        event_instance_nodes = xml_document.findall('.//MAKEINSTANCE')
        result = dict()
        for instance in event_instance_nodes:
            eiid = instance.attrib['eventID']
            atts = {a: v for (a, v) in instance.attrib.items()
                    if a != 'eventID'}
            result[eiid] = atts
        return result


class WikiWarsInLineFileReader(FileReader):
    """This class is a reader for WikiWars inline xml annotated files."""

    def __init__(self, file_filter='*.xml'):
        super(WikiWarsInLineFileReader, self).__init__()
        self.tags_to_spot = {'TIMEX2'}
        self.annotations = []
        self.file_filter = file_filter

    def parse(self, file_path):
        """It parses the input file and extracts relevant information.

        Those information are packed in a Document object, which is our
        internal representation.

        """
        xml = etree.parse(file_path)
        docid = xml.findall(".//DOCID")[0]
        dct = xml.findall(".//DATETIME/TIMEX2")[0]
        title = docid
        text_node = xml.findall(".//TEXT")[0]
        text_string = etree.tostring(text_node, method='text', encoding='utf8')
        text_xml = etree.tostring(text_node, method='xml', encoding='utf8')
        text_string = unicode(text_string, 'UTF-8')
        text_xml = unicode(text_xml, 'UTF-8')
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
        document.doc_id = etree.tostring(docid, method='text',
                                         encoding='utf8').strip()
        document.dct = dct.attrib['val']
        document.dct_text = etree.tostring(dct, method='text', encoding='utf8')
        document.title = etree.tostring(title, method='text',
                                        encoding='utf8').strip()
        document.text = text_string
        document.gold_annotations = self._get_annotations(text_xml,
                                                          -left_chars)
        document.coref = stanford_tree.get('coref', None)

        for stanford_sentence in stanford_tree['sentences']:
            dependencies = stanford_sentence.get('dependencies', None)
            i_dependencies = stanford_sentence.get('indexeddependencies', None)
            # i_dependencies = DependencyGraph(i_dependencies)
            parsetree = stanford_sentence.get('parsetree', u'')
            # parsetree = ParentedTree(parsetree)
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

        document.store_gold_annotations()
        logging.info('{}: parsed.'.format(os.path.relpath(file_path)))
        return document

    def _get_annotations(self, source, start_offset=0):
        """It returns the annotations found in the document.

        It follows the following format:
           [
            ('TAG', {ATTRIBUTES}, (start_offset, end_offset)),
            ('TAG', {ATTRIBUTES}, (start_offset, end_offset)),
            ...
            ('TAG', {ATTRIBUTES}, (start_offset, end_offset))
           ]

        """
        annotations = []
        for event, element in etree.iterparse(
                StringIO(source), events=('start', 'end')):
            if event == 'start':
                if element.tag in self.tags_to_spot:
                    try:
                        end_offset = start_offset + len(element.text)
                    except TypeError:
                        continue
                    annotations.append((element.tag, element.attrib,
                                        (start_offset, end_offset)))
                start_offset += len(element.text)
            elif event == 'end':
                if element.text is not None and element.tail is not None:
                    start_offset += len(element.tail)
        return annotations


class i2b2FileReader(FileReader):
    """This class is a reader for TempEval-3 files."""

    def __init__(self, file_filter='*.xml'):
        super(i2b2FileReader, self).__init__()
        self.tags_to_spot = {'TIMEX3', 'EVENT', 'TLINK'}
        self.annotations = []
        self.file_filter = file_filter
        self.clinical_doc_analyser = DocumentAnalyser()

    def get_dct(self, file_path):
        """ It returns the utterance date for the timexes normalisation.

        """
        path = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        sec_rels = self.clinical_doc_analyser.analyse(path, filename, True)
        return sec_rels

    def parse(self, file_path):
        """It parses the content of file_path and extracts relevant information
        from a TempEval-3 annotated file. Those information are packed in a
        Document object, which is our internal representation.
        """
        logging.info('Document {}: parsing...'.format(
            os.path.relpath(file_path)))
        xml = etree.parse(file_path)
        text_node = xml.findall(".//TEXT")[0]
        text_string = etree.tostring(text_node, method='text', encoding='utf8')
        text_xml = etree.tostring(text_node, method='xml', encoding='utf8')
        text_string = unicode(text_string, 'UTF-8')
        text_xml = unicode(text_xml, 'UTF-8')
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
        document.doc_id = os.path.basename(file_path)
        document.sec_times = self.get_dct(file_path)
        document.dct = document.sec_times.admission_date
        document.dct_text = document.dct.replace('-', '')
        document.title = os.path.basename(file_path)
        document.text = text_string
        document.gold_annotations = self._get_annotations(xml, -left_chars)
        document.coref = stanford_tree.get('coref', None)

        for stanford_sentence in stanford_tree['sentences']:
            dependencies = stanford_sentence.get('dependencies', None)
            i_dependencies = stanford_sentence.get('indexeddependencies', None)
            # i_dependencies = DependencyGraph(i_dependencies)
            parsetree = stanford_sentence.get('parsetree', u'')
            # parsetree = ParentedTree(parsetree)

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

        document.store_gold_annotations()

        logging.info('Document {}: parsed.'.format(os.path.relpath(file_path)))
        return document

    def _get_annotations(self, source, start_offset=0):
        """It returns the annotations found in the document.

        It follows the following format:
           [
            ('TAG', {ATTRIBUTES}, (start_offset, end_offset)),
            ('TAG', {ATTRIBUTES}, (start_offset, end_offset)),
            ...
            ('TAG', {ATTRIBUTES}, (start_offset, end_offset))
           ]

        """
        annotations = []
        elements = source.findall(".//EVENT")
        elements.extend(source.findall(".//TIMEX3"))
        for element in elements:
            try:
                start = int(element.attrib['start']) + start_offset
                end = int(element.attrib['end']) + start_offset
                annotations.append((element.tag, element.attrib, (start, end)))
            except TypeError:
                continue
        return annotations


Reader.register(FileReader)
FileReader.register(TempEval3FileReader)
FileReader.register(WikiWarsInLineFileReader)
FileReader.register(i2b2FileReader)


def main():
    '''Simple ugly non-elegant test.'''
    import json
    file_reader = TempEval3FileReader()
    document = file_reader.parse(sys.argv[1])
    print json.dumps(document, indent=4)

if __name__ == '__main__':
    main()
