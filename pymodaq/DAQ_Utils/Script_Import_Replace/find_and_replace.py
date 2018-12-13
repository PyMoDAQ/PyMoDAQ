import os
import re
import sys

"""
	#==========================================================#
	| WARNING !!! NO WAY BACK !!! , please be extremely careful|
	| The script treat full directory tree including           |
	| subdirectories and files without go back option          |
	#==========================================================#

	 The algorithm replace parts of codes into a source code in each
	 extension specified file found in the tree from the local 
	 directory root.
	 The replaced code could be single word or a sequence.
	 In case of sequence please replace the full line to keep file 
	 structure.
	 To treat big packages including differents levels of tree,
	 the algorithm is recursive and will act on each .ext file.
	 extension is given as the first argument
	 original code to replace is given as the second one
	 the replaced code is given as the third.

	 Explanations:
	 =============
	 -Create directory list and .ext file list from current directory 
	 -Rebuild original string path for each source file 
	 -Open and replace the original code samples given by the replace part of code
	 -Write modified contents in source file
"""
	

def find_directory(liste):
	"""
		Find directory list from the given string and the regular expression

		=============== ========== ================================
		**Parameters**   **Type**   **Description**
		*liste*          string     The os command result to treat
		=============== ========== ================================

		Returns
		-------
		string list
			The directory list of the os command

		Examples
		--------
		>>> print(test)
		 Le volume dans le lecteur C n'a pas de nom.
		 Le num‚ro de s‚rie du volume est 064A-6BB0

		 R‚pertoire de C:\Users\flim-users\Documents\Tests install\test_script

		04/05/2018  11:55    <DIR>          .
		04/05/2018  11:55    <DIR>          ..
		04/05/2018  11:55    <DIR>          DAQ_Analysis
		04/05/2018  11:53             8ÿ758 find_and_replace.py
		03/05/2018  13:04             1ÿ327 find_py.py
		03/05/2018  13:25             3ÿ119 find_py_and_replace.py
		03/05/2018  15:47               619 find_words_in_line.py
		03/05/2018  16:02               524 replace_QtDesRess.py
		03/05/2018  13:20               142 test.py
		04/05/2018  11:53    <DIR>          __pycache__
		               6 fichier(s)           14ÿ489 octets

		 R‚pertoire de C:\Users\flim-users\Documents\Tests install\test_script\DAQ_Analysis

		04/05/2018  11:55    <DIR>          .

		>>> # Given input is the 'dir /s' command result
		... res=find_directory(test)
		>>> for i in range(0,len(res)):
		...     print(res[i])
		...
		C:\Users\flim-users\Documents\Tests install\test_script
		C:\Users\flim-users\Documents\Tests install\test_script\DAQ_Analysis
	"""
	regex = re.compile("[C-G]:.*$",re.MULTILINE)
	ret=[]
	ret=re.findall(regex,liste)
	return ret

def find_file(string,extension):
	"""
		Find .extension file list from the given list and the regular expression

		============== ========== =======================================================
		**Parameters**   **Type**   **Description**
		*string*         string     raw splitted command result containing the file name
		*extension*      string     file extension (without .)
		============== ========== =======================================================

		Returns
		-------
		string list
			The file list of the splitted os command result

		Examples
		--------
		>>> print(test_file)
		04/05/2018  11:55    <DIR>          .
		04/05/2018  11:55    <DIR>          ..
		04/05/2018  11:55    <DIR>          DAQ_Analysis
		04/05/2018  11:53             8ÿ758 find_and_replace.py
		03/05/2018  13:04             1ÿ327 find_py.py
		03/05/2018  13:25             3ÿ119 find_py_and_replace.py
		03/05/2018  15:47               619 find_words_in_line.py
		03/05/2018  16:02               524 replace_QtDesRess.py
		03/05/2018  13:20               142 test.py
		04/05/2018  11:53    <DIR>          __pycache__
		               6 fichier(s)           14ÿ489 octets
		>>> found_file=find_file(test_file,'py')
		>>> for i in range(0,len(found_file)):
		...     print(found_file[i])
		...
		find_and_replace.py
		find_py.py
		find_py_and_replace.py
		find_words_in_line.py
		replace_QtDesRess.py
		test.py
	"""
	string_reg="([a-zA-Z0-9-_]*"+"\."+extension+")"
	regex=re.compile(string_reg,re.MULTILINE)
	ret=[]
	ret=re.findall(regex,string)
	return ret

def find_path(extension):
	"""
		Find full path list of .extension file with their associated directory

		=============== ========== =============================
		**Parameters**   **Type**   **Description**
		*extension*      string      file extension (without .)
		=============== ========== =============================

		Returns
		-------
		string list list
			The path list reconstructed from a directory and a file list

		See Also
		--------
		find_directory, find_file

		Examples
		--------
		>>> path_list=find_path('py')
		>>> for i in range(0,len(path_list)):
		...     print(path_list[i])
		...   #if path_list[i] is a string, it's a directory
		C:\Users\flim-users\Documents\Tests install\test_script
		['find_and_replace.py', 'find_py.py', 'find_py_and_replace.py', 'find_words_in_line.py', 'replace_QtDesRess.py', 'test.py']
		C:\Users\flim-users\Documents\Tests install\test_script\DAQ_Analysis
		['DAQ_analysis_main.py', '__init__.py']
		C:\Users\flim-users\Documents\Tests install\test_script\DAQ_Analysis\setup
		['dep_setup.py', 'ez_setup.py', 'refresh_path.py', 'setup.py']
		>>>   #else it's a list file
	"""
	regex_dir = re.compile("C:.*$",re.MULTILINE)
	py_files=[]
	liste=''
	if (os.name=='nt'):    # windows users command
		cmd="dir \"*."+extension+"\" /s"
	else:                  # posix users command
		cmd="ls -R"
	liste=os.popen(cmd).read()
	dir_liste=find_directory(liste)
	splitted=re.split(regex_dir,liste)
	final_path=[]
	for i in range(0,len(splitted)-1):
		final_path.append(dir_liste[i])
		final_path.append(find_file(splitted[i+1],extension))
	return final_path

def rebuild_string(liste):
	"""
		Rebuild string_path from computed list
	
		=============== ================== =========================================
		**Parameters**   **Type**           **Description**
		*liste*          string list list   If element is :
											 * string : it contain a directory path
											 * string list : it conatin a file list
		=============== ================== =========================================

		Returns
		-------
		string list
			The usable string full path list rebuilt from the given list

		Examples
		--------
		>>> #input : the find_path computed list : 
		>>> for i in range(0,len(path_list)):
		...     print(path_list[i])
		...
		C:\Users\flim-users\Documents\Tests install\test_script
		['find_and_replace.py', 'find_py.py', 'find_py_and_replace.py', 'find_words_in_line.py', 'replace_QtDesRess.py', 'test.py']
		>>>     # Function rebuild usable string path list from arguments
		>>> real_path_list=rebuild_string(path_list)
		>>> for i in range(0,len(real_path_list)):
		...     print(real_path_list[i])
		...
		C:\Users\flim-users\Documents\Tests install\test_script\find_and_replace.py
		C:\Users\flim-users\Documents\Tests install\test_script\find_py.py
		C:\Users\flim-users\Documents\Tests install\test_script\find_py_and_replace.py
		C:\Users\flim-users\Documents\Tests install\test_script\find_words_in_line.py
		C:\Users\flim-users\Documents\Tests install\test_script\replace_QtDesRess.py
		C:\Users\flim-users\Documents\Tests install\test_script\test.py

	"""
	path_list=[]
	tmp_name=''
	for i in range(0,len(liste)):
		if(i%2==0):
			tmp_name=liste[i]
		else:
			for j in range(0,len(liste[i])):
				path_list.append(tmp_name+"\\"+liste[i][j])
	return path_list

def concat(liste):
	"""
		Concatenate lines_list to rebuild the treated file content

		=============== ============ ==============================================================
		**Parameters**   **Type**      **Description**
		*liste*          string list   a string list representing the content of a .extension file
		=============== ============ ==============================================================

		Returns
		-------
		string
			The rebuilt file contents from given list

		Example
		-------
		>>> for i in range(0,len(test)):
		...     print(test[i])
		...
		#include<stdio.h>

		void myfunction(int arg){

		int some_things;

		}

		>>> concatenated=concat(test)
		>>> print(concatenated)
		#include<stdio.h>
		void myfunction(int arg){
		int some_things;
		}
	"""
	res=""
	for line in liste:
		res+=line
	return res

def find_word_in_string(string):
	"""
		Create the words list from the given string

		=============== ========== ==================================
		**Parameters**   **Type**   **Description**
		*string*         string     the string to be "word-splitted"
		=============== ========== ==================================

		Returns
		-------
		string list
			A list containing each word of the given string

		Example
		-------
		>>> test="This is the test sentence to be splitted"
		>>> splitted=find_word_in_string(test)
		>>> for i in range(0,len(splitted)):
		...     print(splitted[i])
		...
		This
		is
		the
		test
		sentence
		to
		be
		splitted
	"""
	regex=re.compile("\s",re.MULTILINE)
	words=re.split(regex,string)
	return words

def replace_word_in_string(string,word_or,word_re):
	"""
		Replace any occurence of word_or by word_re in the given string

		============== =========== ====================================
		**Parameters**   **Type**   **Description**
		*string*         string     The sentence to treat
		*word_or*        string     The original word pattern to match
		*word_re*        string     The replacement word
		============== =========== ====================================

		Returns
		-------
		string
			The sentence where word_or words have been replaced by word_re.

		See Also
		--------
		find_word_in_string

		Example
		-------
		>>> test="This is the test sentence to be replace"
		>>> replaced=replace_word_in_string(test,'sentence','string')
		>>> print(replaced)
		This is the test string to be replace
	"""
	ret=""
	words=find_word_in_string(string)
	for i in range(0,len(words)):
		if(word_or in words[i]):
			words[i]=word_re
		ret+=words[i]+(" ")
	return ret

def get_nb_words(string):
	"""
		Count the words in the given string.

		=============== ========== ================================
		**Parameters**   **Type**   **Description**
		*string*         string     the string to be "word-counted"
		=============== ========== ================================

		Returns
		-------
		int
			The number of words in the sentence

		See Also
		--------
		find_word_in_string

		Example
		-------
		>>> test="This is the test sentence to be word-count, even if i know there is 16 words"
		>>> number=get_nb_words(test)
		>>> print(number)
		16
	"""
	return len(find_word_in_string(string))


def replace_code(path_list,original_code,replaced_code,mode):
	"""
		Algorithm of source code replacement, all the original_code sequence found in source file will be replaced by replaced code argument.
		The algorithm is efficient for less than one lines sentence.
		To bigger code sequence, please automat via script.

		=============== ============= ==========================================================
		**Parameters**   **Type**      **Description**
		*path_list*      string list   a list of path of the current directory
		*original_code*  string        the original code sentence to replace
		*replaced_code*  string        the replacement code 
		*mode*           int           Representing the type of content of string code sampes :
											* 0 mean single word code
											* 1 mean words sequence code
		=============== ============= ==========================================================

		Returns
		-------
		None
			Void main function

		See Also
		--------
		replace_word_in_string

		Example
		-------
		>>>    # .cpp file before modification
		#include <iostream>
		using namespace std; 
		#define MAX_ARRAY 1000
		>>> path=find_path('cpp')
		>>> print(path)         #the list structure representing the directory tree
		['C:\\Users\\flim-users\\Documents\\Tests install\\test_script', ['TD1.cpp']]
		>>> path_list=rebuild_string(path)
		>>> print(path_list)    #the rebuilt string path_name
		['C:\\Users\\flim-users\\Documents\\Tests install\\test_script\\TD1.cpp']
		>>> replace_code(path_list,'#include <iostream>','#include <oups_i_mistake_my_include_in_253_files>\n',1)
		C:\Users\flim-users\Documents\Tests install\test_script\TD1.cpp
		| opened and treated
		Done, thanks.
		>>>    # .cpp file after modification
		#include <oups_i_mistake_my_include_in_253_files>
		using namespace std; 
		#define MAX_ARRAY 1000		
	"""
	for i in range(0,len(path_list)):
		filename=path_list[i]
		try:
			file=open(filename,"r+")
			print(filename + " \n| opened and treated")
		except:
			pass
		lines=file.readlines()
		file.seek(0,0)
		file.truncate()
		for i in range(0,len(lines)):
			if(original_code in lines[i]):
				if(not mode):
					lines[i]=replace_word_in_string(lines[i],original_code,replaced_code)
				else:
					lines[i]=replaced_code
		file_content=''
		file_content=concat(lines)
		file.write(file_content)
	print("Done, thanks.")

if(len(sys.argv)!=4):
	print("usage : find_and_replace.py <file extension> <code part to replace> <desired replace code>")
	exit(0)

ext=sys.argv[1]
print(ext)
original_code=sys.argv[2]
mode=(0 if (get_nb_words(original_code)==1) else 1)
replaced_code=sys.argv[3]
mode=(0 if (get_nb_words(replaced_code)==1) else 1)
print("mode = "+str(mode))

path=find_path(ext)
path_list=[]
path_list=rebuild_string(path)
for i in range(0,len(path_list)):
	print(path_list[i])
for i in range(0,len(path_list)):
	print(path_list[i])
replace_code(path_list,original_code,replaced_code,mode)

# Used regular expressions
#Tested on https://regex101.com/
# directory
# \C\\*.*$

# py file :
# (\n*.*\s)([a-zA-Z_]*\.\p\y))

# :-) 
