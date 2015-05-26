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

'''It returns the ISO-TimeML-annotated input documents.'''
__author__ = "Michele Filannino <filannino.m@gmail.com>"
__version__ = "0.1"
__codename__ = "purple tempo"

import argparse
import codecs
import cPickle
import glob
import logging
import os
import xml.etree.cElementTree as cElementTree

from readers import i2b2FileReader, TempEval3FileReader
from writers import i2b2Writer, TempEval3Writer, HTMLWriter
from attributes_extractor import FullExtractor
from classifier import IdentificationClassifier
from classifier import NormalisationClassifier
from classifier import RelationClassifier
from settings import PATH_MODEL_FOLDER


class ManTIME(object):

    def __init__(self, reader, writer, extractor, model_name, pipeline=True,
                 domain='general'):
        assert domain in ('general', 'clinical')
        self.post_processing_pipeline = pipeline
        self.reader = reader
        self.writer = writer
        self.extractor = extractor
        self.documents = []
        self.model_name = model_name
        self.model_path = '{}/{}/model.pickle'.format(PATH_MODEL_FOLDER,
                                                      self.model_name)
        try:
            self.model = cPickle.load(open(self.model_path))
            logging.info('{} model: loaded.'.format(self.model.name))
        except IOError:
            self.model = None
            logging.info('{} model: built.'.format(model_name))
        self.domain = domain

    def train(self, folder):
        folder = os.path.abspath(folder)
        assert os.path.isdir(folder), 'Folder doesn\'t exist.'

        identifier = IdentificationClassifier()
        normaliser = NormalisationClassifier()
        linker = RelationClassifier()

        # corpus collection
        input_files = os.path.join(folder, self.reader.file_filter)
        for input_file in glob.glob(input_files):
            try:
                doc = self.extractor.extract(self.reader.parse(input_file))
                self.documents.append(doc)
            except cElementTree.ParseError:
                msg = 'Document {} skipped: parse error.'.format(
                    os.path.relpath(input_file))
                logging.error(msg)

        # storing the attribute extractors caches
        self.extractor.store_caches()
        logging.info('Extractors\'s caches: stored.')

        # training models (identification and normalisation)
        modl = identifier.train(self.documents, self.model_name)
        modl = normaliser.train(self.documents, modl)
        modl = linker.train(self.documents, modl)
        self.model = modl
        # dumping models
        cPickle.dump(modl, open(self.model_path, 'w'))

        return modl

    def label(self, file_name):
        # according to the type
        assert os.path.isfile(file_name), 'Input file does not exist.'
        assert self.model, 'Model not loaded.'

        identifier = IdentificationClassifier()
        normaliser = NormalisationClassifier()
        linker = RelationClassifier()

        try:
            doc = self.extractor.extract(self.reader.parse(file_name))
            annotated_doc = identifier.test([doc], self.model,
                                            self.post_processing_pipeline)
            annotated_doc = normaliser.test([doc], self.model, self.domain)
            annotated_doc = linker.test([doc], self.model)

            output = self.writer.write(annotated_doc)
            return output
        except cElementTree.ParseError:
            msg = 'Document {} skipped: parse error.'.format(
                os.path.relpath(file_name))
            logging.error(msg)
            return ['']


def main():
    """ It annotates documents in a specific folder.
    """
    logging.basicConfig(format='%(asctime)s: %(message)s',
                        level=logging.DEBUG,
                        datefmt='%m/%d/%Y %I:%M:%S %p')
    # Parse input
    parser = argparse.ArgumentParser(
        description='ManTIME: temporal information extraction')
    parser.add_argument('mode', choices=['train', 'test'],
                        help='Train or Test mode?')
    parser.add_argument('input_folder', help='Input data folder path')
    parser.add_argument('model',
                        help='Name of the model to use (case sensitive)')
    parser.add_argument('-v', '--version', help='show the version and exit',
                        action='store_true')
    parser.add_argument('-ppp', '--post_processing_pipeline',
                        action='store_true',
                        help='it uses the post processing pipeline.')
    args = parser.parse_args()

    # ManTIME
    mantime = ManTIME(reader=i2b2FileReader(),
                      writer=i2b2Writer(),
                      extractor=FullExtractor(),
                      model_name=args.model,
                      pipeline=args.post_processing_pipeline,
                      domain='clinical')

    if args.mode == 'train':
        # Training
        mantime.train(args.input_folder)
    else:
        # Testing
        assert os.path.exists(args.input_folder), 'Model not found.'
        input_files = os.path.join(args.input_folder, '*.*')
        documents = sorted(glob.glob(input_files))
        assert documents, 'Input folder is empty.'
        for index, doc in enumerate(documents, start=1):
            basename = os.path.basename(doc)
            writein = os.path.join('./output/', basename)
            position = '[{}/{}]'.format(index, len(documents))
            if writein not in glob.glob('./output/*.*'):
                file_path = writein
                with codecs.open(file_path, 'w', encoding='utf8') as output:
                    # try:
                    logging.info('{} Doc {}.'.format(position, basename))
                    output.write(mantime.label(doc)[0])
                    logging.info('{} Doc {} annotated.'.format(position,
                                                               basename))
                    # except Exception:
                    #     logging.error('{} Doc {} ** skipped **!'.format(
                    #         position, basename))
                    #     os.remove(file_path)

if __name__ == '__main__':
    main()
