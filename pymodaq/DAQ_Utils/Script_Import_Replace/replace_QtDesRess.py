import sys

# C'est le script pour remplacer les import QtDesigner_ressources_rc dans toute
# l'arborescence du projet si les ui sont modifiés.

# Pour utiliser : 
# placer le script à la racine de l'arborescence
# executer


def concat(liste):
	res=""
	for line in liste:
		res+=line
	return res

if(len(sys.argv)<1):
	print("usage : replace....py file_name")
	exit(0)
filename=sys.argv[1]
print(filename)
file=open(filename,"r+")
lines=file.readlines()
file.seek(0,0)
file.truncate()
for i in range(0,len(lines)):
	if(lines[i]=="import QtDesigner_ressources_rc\n"):
		lines[i]="import PyMoDAQ.QtDesigner_Ressources.QtDesigner_ressources_rc\n"
file_content=''
file_content=concat(lines)
file.write(file_content)
