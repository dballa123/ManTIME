TO-DO List
=======

This document lists all the things I should look more carefully in the future.

- [ ] Attributes models should include identification feature (heavier but better).
- [ ] Implement the feature extractor for Temporal Links.
- [ ] Implement the classifier for Temporal Links.
- [ ] Adapt the writers to output temporal links too.
- [ ] Implement the add-on for clinical domain.
- [ ] Look carefully at all the features and possibly cut them.
- [ ] Introduce model folders instead of files.
- [ ] Correct some morphological gazetteer features according to the English grammar. Are all the things called prepositions actually prepositions?
- [ ] Do I really need to load Stanford Core NLP everytime for every document? Once (the problem)[https://github.com/dasmith/stanford-corenlp-python/issues/13] with long texts is solved I should switch to the new stanford-core-nlp.
- [ ] Remove the output produced by CRF++ in the training phase.
- [ ] Probably you can avoid some variables for Document and Sentence objects.
- [ ] Group the annotations token based at sentence level.
- [ ] Instead of the settings.py file, use OS.ENVIRONS variable.
- [ ] Comment the code: better and more verbously using Google Commenting Style.
- [ ] Have a look at argparse ... it's not correct right now.
- [x] Split identification models (TIMEXes and EVENTs).
- [x] CRF based attributes extraction
- [x] There are some print statement somewhere (WARNING cases). I should use
  something more appropriate for them (log).
- [x] Remove the output produced from Stanford Parser in the stdout/stderr (if
  everything goes ok).  
- [x] Find documentation about how to comment the code so that nice Python-doc
  style web pages can be automatically generated.
- [x] Love ManTIME!