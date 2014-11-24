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

"""It contains all the writers for ManTIME.

   A writer must have a write() method which is responsible for returning a
   string representation of each document (Writer) or writing on a file
   (FileWriter). In any case a writer always takes in input a single document.

   In order to force the existence of the write() method I preferred Python
   interfaces to the duck typing practice.
"""

from abc import ABCMeta, abstractmethod
import logging
import os
from collections import Counter


class Writer(object):
    """This class is an abstract writer for ManTIME."""
    __metaclass__ = ABCMeta

    @abstractmethod
    def write(self, document):
        pass


class FileWriter(Writer):
    """This classs is an abstract file writer for ManTIME."""
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def write(self, document):
        pass


class SimpleXMLFileWriter(FileWriter):
    """This class is a simple XML writer."""

    def __init__(self):
        super(SimpleXMLFileWriter, self).__init__()

    def write(self, document):
        """
        """
        return [(word.word_form, word.predicted_label)
                for sent in document.sentences
                for word in sent.words]


class TempEval3Writer(FileWriter):
    """This class is a writer in the TempEval-3 format."""

    def __init__(self):
        super(TempEval3Writer, self).__init__()

    def write(self, documents):
        """It writes on an external file in the TempEval-3 format.

        """
        from normalisers.timex_general import normalise as timex_normalise

        def write_tag(word, memory, text):
            annotated_text = text[memory['start']:memory['end']]
            attribs = ''
            if memory['tag'] == 'EVENT':
                event_class = ''
                event_eid = memory['tag_ids'].get(memory['tag'], 1)
                memory['tag_ids'][memory['tag']] = event_eid + 1
                attribs = 'class="{}" eid="e{}"'.format(event_class, event_eid)
            elif memory['tag'] == 'TIMEX3':
                timex3_type, timex3_value = '', ''
                timex3_tid = memory['tag_ids'].get(memory['tag'], 1)
                memory['tag_ids'][memory['tag']] = timex3_tid + 1
                attribs = 'type="{}" value="{}" tid="t{}"'.format(timex3_type,
                                                                  timex3_value,
                                                                  timex3_tid)
            if memory['tag']:
                text.insert(memory['start'], '<{} {}>'.format(memory['tag'],
                                                              attribs))
                text.insert(memory['end']+1, '</{}>'.format(memory['tag']))
                memory['offset'] += 2
            memory['start'] = 0
            memory['end'] = 0
            memory['tag'] = None

        outputs = []
        for document in documents:
            output = []
            output.append('<?xml version="1.0" ?>')
            output.append('<TimeML xmlns:xsi="http://www.w3.org/2001/XMLSche' +
                          'ma-instance" xsi:noNamespaceSchemaLocation="http:' +
                          '//timeml.org/timeMLdocs/TimeML_1.2.1.xsd">\n')
            output.append('<DOCID>{doc_id}</DOCID>\n'.format(
                doc_id=document.doc_id))
            output.append(str('<DCT><TIMEX3 tid="t0" type="DATE" value="{}" ' +
                              'temporalFunction="false" functionInDocument="' +
                              'CREATION_TIME">{}</TIMEX3></DCT>\n'
                              ).format(document.dct, document.dct_text))
            output.append('<TITLE>{}</TITLE>\n'.format(document.title))

            text = list(document.text)
            memory = {'start': 0, 'end': 0, 'tag': None, 'offset': 0,
                      'tag_ids': Counter()}
            # TO-DO: This works properly only for IO annotation schema!
            for sentence in document.sentences:
                for word in sentence.words:
                    current_start = word.character_offset_begin + \
                        document.text_offset + memory['offset']
                    current_end = word.character_offset_end + \
                        document.text_offset + memory['offset']
                    if word.predicted_label != 'O':
                        # Labelled token
                        if memory['start']:
                            # Next labelled token
                            if memory['tag'] == word.predicted_label:
                                # Continuing previous annotation
                                memory['end'] = current_end
                            else:
                                # Starting a new annotation
                                write_tag(word, memory, text)
                                memory['start'] = current_start
                        else:
                            # First labelled token
                            memory['start'] = current_start
                            memory['end'] = current_end
                            _, memory['tag'] = word.predicted_label.split('-')
                    else:
                        # Unlabelled token
                        if memory['start']:
                            write_tag(word, memory, text)
            # An annotation can possibly end on the very last token
            if memory['start']:
                write_tag(word, memory, text)
            # TO-DO: end.
            output.append('<TEXT>{}</TEXT>\n\n'.format(''.join(text)))
            # MAKEINSTANCEs
            # TLINKs
            output.append('</TimeML>\n')
            outputs.append('\n'.join(output))
        return '\n----------\n'.join(outputs)


class AttributeMatrixWriter(Writer):
    """This class writes the attribute matrix taken by ML algorithms."""

    def __init__(self, separator='\t', include_header=False):
        super(AttributeMatrixWriter, self).__init__()
        self.separator = separator
        self.header = include_header

    def write(self, documents):
        # save_to = os.path.abspath(save_to)
        # with open(save_to, 'w') as output:
        output = []
        if self.header:
            first_word = documents[0].sentences[0].words[0]
            header = [k for k, _ in sorted(first_word.attributes.items())]
            output.append(self.separator.join(header))
        for document in documents:
            for sentence in document.sentences:
                for word in sentence.words:
                    row = [v for _, v in sorted(word.attributes.items())]
                    row.append(word.predicted_label)
                    output.append(self.separator.join(row))
                output.append('')
        # logging.info('{} exported.'.format(save_to))
        return '\n'.join(output)

Writer.register(FileWriter)
FileWriter.register(SimpleXMLFileWriter)
FileWriter.register(TempEval3Writer)
FileWriter.register(AttributeMatrixWriter)


def main():
    '''Simple ugly non-elegant test.'''
    import sys
    from readers import TempEval3FileReader

    file_reader = TempEval3FileReader(annotation_format='IO')
    document = file_reader.parse(sys.argv[1])
    file_writer = SimpleWriter()
    print file_writer.write([document])

if __name__ == '__main__':
    main()
