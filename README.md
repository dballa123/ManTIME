ManTIME
=======

Temporal expression extraction pipeline for general domain. System submitted to TempEval-3 challenge.

##How to use it

Put the .tml files in a particular folder and run the pipeline.py script.

    $ python pipeline.py <folder_path>
    $

The script will create a new folder in it, called "annotated", with the annotated .tml documents.

##Dependencies

You should have installed the following softwares:
* MBSP CLIPS for Python ([web page](http://www.clips.ua.ac.be/software/mbsp-for-python))
* TreeTagger ([web page](http://www.ims.uni-stuttgart.de/projekte/corplex/TreeTagger/))
* CRF++ 0.57 ([web page](http://crfpp.googlecode.com/svn/trunk/doc/index.html))

##License

(GPL v2)

Copyright (c) 2012 Michele Filannino, <http://www.cs.man.ac.uk/~filannim/>.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

##Contact
- Email: filannim@cs.man.ac.uk
- Web: http://www.cs.man.ac.uk/~filannim/
