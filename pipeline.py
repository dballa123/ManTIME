#!/usr/bin/python
#
#	Copyright 2012 Michele Filannino
#
#	gnTEAM, School of Computer Science, University of Manchester.
#	All rights reserved. This program and the accompanying materials
#	are made available under the terms of the GNU General Public License.
#	
#	author: Michele Filannino
#	email:  filannim@cs.man.ac.uk
#	
#	This work is part of TempEval-3 challenge.	
#	For details, see www.cs.man.ac.uk/~filannim/

from __future__ import division
import multiprocessing
from multiprocessing import Pool
from functools import partial
import os
from os import listdir
from os.path import abspath
from os.path import basename
from os.path import dirname
import sys


import components.nlp_functions
from components.feature_factory import FeatureFactory
from components.KMP import KMP
from components.nlp_functions import NLP
from components.nlp_functions import TreeTaggerTokeniser
from components.text_extractor import TextExtractor
from components.tagger import Tagger
from components.normalisers.general_timex_normaliser import normalise as generally_normalise


def pipeline(file_set, post_processing=False, debug=False):
	te = TextExtractor();
	ff = FeatureFactory();
	tagger = Tagger();
	start_id = 1
	for file in file_set:
		source_folder_path = abspath(dirname(file))
		original_file = abspath(file)
		annotated_file = source_folder_path + '/annotated_output/' + basename(file).replace(".TE3input","")
		
		utterance = te.get_utterance(original_file)
		save_file = open(annotated_file,'w')
		save_file_content = open(original_file,'r').read()
		for sentence, offsets in te.read(original_file, ['TIMEX3','EVENT','SIGNAL'], debug=False):
			sentence = sentence.replace('__space__', ' ').strip()
			if debug: print 'SENTENCE:', sentence
			sentence_iob = ff.getFeaturedSentence([sentence, offsets], 'TIMEX3', True, debug=False)
			tagged = tagger.tag(sentence, sentence_iob, utterance, start_id, withPipeline=True, debug=False)
			if debug: print 'TAGGED:', tagged
			save_file_content = save_file_content.replace(sentence.replace("&", "&amp;"), tagged['sentence'])
			start_id = tagged['start_id']
		start_id = 1
		save_file.write(save_file_content)
		save_file.close()

def main():
	# Path check
	try:
		original_path = abspath(sys.argv[1])
	except:
		print '\033[1m'+'SYNOPSIS:'+'\033[0m'
		print '>> python ' + sys.argv[0] + ' <source_directory> [-pp]'
		print
		print '\033[1m'+'DESCRIPTION:'+'\033[0m'
		print 'It scans the content of <source_directory> and annotates all the .TE3input files in it. The annotated documents are saved as .tml and stored in a new sub-folder (<source_directory>/annoted_output).'
		print
		print 'The following options are available:'
		print
		print '-pp\tUses the post-processing pipeline on top of the CRF module.'
		print 
		return None

	post_processing = True if '-pp' in sys.argv[2:] else False
	call_pipeline = partial(pipeline, post_processing=post_processing)

	os.system('rm -Rf '+original_path+'/annotated_output')
	os.system('mkdir '+original_path+'/annotated_output')


	processes_num = multiprocessing.cpu_count()*2
	files = [str(original_path+'/'+f) for f in listdir(original_path) if f.endswith('.tml.TE3input')]
	chunk_dim = int(len(files)/(processes_num))
	if chunk_dim<1: chunk_dim = 1
	file_chunks = [files[i:i+chunk_dim] for i in range(0, len(files), chunk_dim)]
	#print file_chunks

	pool = Pool(processes=processes_num)
	result = pool.map(call_pipeline, file_chunks)

	# TEST
	# pipeline(['/Users/michele/Dropbox/Workspace/ManTIME/data/test/test.tml.TE3input'], post_processing, debug=False)


if __name__ == '__main__':
	main()
