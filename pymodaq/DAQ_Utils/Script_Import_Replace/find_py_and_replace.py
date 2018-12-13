import os
import re

# C'est le script pour remplacer les import QtDesigner_ressources_rc dans toute
# l'arborescence du projet si les ui sont modifiés.
# Pour utiliser : 
# placer le script à la racine de l'arborescence
# executer

# A voir la version plus generale find_and_replace.py
# Faire bien attention à l'endroit ou on l'execute (si necessaire faire une copie locale
# de l'arborescence pour tester le script et verifier) 


# The algorithm replace parts of codes into a source code.
# To treat big packages including differents levels of tree,
# the algorithm is recursive.

# -Create directory list and .py file list from current directory 
# -Rebuild original string path for each source file 
# -Open and replace the part of code givven as an argument by the second part of code guven as an argument
# -Write modified contents in source file

def find_directory(liste):
	#Find directory list from the given string and the regular expression
	regex = re.compile("C.*$",re.MULTILINE)
	ret=[]
	ret=re.findall(regex,liste)
	return ret

def find_py_file(string):
	#Find .py file list from the given list and the regular expression
	regex=re.compile("([a-zA-Z0-9_]*\.py)",re.MULTILINE)
	ret=[]
	ret=re.findall(regex,string)
	return ret

def find_path():
	#find full path list of .py file with their associated directory
	regex_dir = re.compile("C.*$",re.MULTILINE)
	py_files=[]
	liste=''
	liste=os.popen("dir \"*.py\" /s").read()
	dir_liste=find_directory(liste)
	splitted=re.split(regex_dir,liste)

	final_path=[]
	for i in range(2,len(splitted)-1):
		final_path.append(dir_liste[i])
		final_path.append(find_py_file(splitted[i+1]))
	return final_path

def rebuild_string(liste):
	#rebuild string_path from computed list
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
	#concatenate lines_list to rebuild the treated file content
	res=""
	for line in liste:
		res+=line
	return res

def replace_code(path_list):
	#Algorithm of source code replacement, used with static values as a test
	for i in range(0,len(path_list)):
		filename=path_list[i]
		try:
			file=open(filename,"r+")
			print(filename + " \n| opened and treated")
		except:
			pass
		lines=file.readlines()
		for i in range(0,len(lines)):
			if(lines[i]=="import QtDesigner_ressources_rc\n"):
				lines[i]="import PyMoDAQ.QtDesigner_Ressources.QtDesigner_ressources_rc\n"
		file_content=''
		file_content=concat(lines)
		file.write(file_content)
	print("Done, thanks.")

def replace_code_arg(path_list,original_code,replaced_code):
	#Algorithm of source code replacement, all the original_code found in source file will be replaced by replaced code argument
	for i in range(0,len(path_list)):
		filename=path_list[i]
		try:
			file=open(filename,"r+")
			print(filename + " \n| opened and treated")
		except:
			pass
		lines=file.readlines()
		for i in range(0,len(lines)):
			if(lines[i]==original_code):
				lines[i]=replaced_code
		file_content=''
		file_content=concat(lines)
		file.write(file_content)
	print("Done, thanks.")

path=find_path()
path_list=[]
path_list=rebuild_string(path)
for i in range(0,len(path_list)):
	print(path_list[i])
replace_code(path_list)

# Used regular expressions
# directory
# \C\\*.*$

# py file :
# (\n*.*\s)([a-zA-Z_]*\.\p\y))
