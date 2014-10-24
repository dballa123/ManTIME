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

"""It contains the classes for the document data model of ManTIME."""


def format_annotation(start_token, end_token, annotations, annotation_format):
    '''It returns the correct sequence class label for the given token.'''
    sequence_label = None
    tag_fired = ''
    for tag, _, (start_offset, end_offset) in annotations:
        tag_fired = tag
        if (start_offset, end_offset) == (start_token, end_token):
            sequence_label = 'W'
            break
        elif end_offset == end_token:
            sequence_label = 'E'
            break
        elif start_offset == start_token:
            sequence_label = 'B'
            break
        elif start_offset < start_token and end_offset > end_token:
            sequence_label = 'I'
            break
        else:
            sequence_label = 'O'
    if sequence_label not in list(annotation_format):
        sequence_label = 'I'
    if sequence_label == 'O':
        return sequence_label
    else:
        return sequence_label + '-' + tag_fired


class Document(object):
    '''It represents the root of a parsed document.'''

    def __init__(self, name, file_path='', dct=None):
        self.name = name
        self.file_path = file_path
        self.dct = dct
        self.text = ''
        self.sentences = []
        self.coref = None
        self.gold_annotations = []
        self.predicted_annotations = []
        self.annotation_format = ''

    def store_gold_annotations(self, annotation_format):
        """Enriching the Stanford Parser output with gold annotations."""
        for sentence in self.sentences:
            for word in sentence.words:
                word.attributes['CLASS'] = format_annotation(
                    int(word.character_offset_begin),
                    int(word.character_offset_end),
                    self.gold_annotations,
                    annotation_format)
        self.annotation_format = annotation_format

    def __str__(self):
        return self.__dict__

    def __repr__(self):
        return repr(self.__dict__)


class Sentence(object):

    def __init__(self, dependencies=None, indexed_dependencies=None,
                 parsetree='', text='', words=[]):
        if dependencies:
            assert type(dependencies) == list, 'Wrong dependencies type'
        if indexed_dependencies:
            assert type(indexed_dependencies) == list, \
                'Wrong indexed dependencies type'
        if parsetree:
            assert type(parsetree) == unicode, 'Wrong parsetree type'
        if text:
            assert type(text) == unicode, 'Wrong text type'
        if words:
            assert type(words) == list, 'Wrong words type'

        self.dependencies = dependencies
        self.indexed_dependencies = indexed_dependencies
        self.parsetree = parsetree
        self.words = words


class Word(object):

    def __init__(self, word_form, char_offset_begin, char_offset_end,
                 lemma, named_entity_tag, part_of_speech):
        self.word_form = word_form
        self.character_offset_begin = char_offset_begin
        self.character_offset_end = char_offset_end
        self.lemma = lemma
        self.named_entity_tag = named_entity_tag
        self.part_of_speech = part_of_speech
        self.attributes = {}

class Classifier(object):
    """
    """
    def __init__(self):
        pass


class AttributesExtractor(object):
    """
    """
    def __init__(self):
        pass
