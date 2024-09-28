format:
	- autoflake -ri --remove-all-unused-imports pythion/src
	- isort  --profile black .
	- black --target-version py310 .

commit:
	- git add .
	- python3 /media/asaniczka/working/packages/pythion/pythion/__init__.py make-commit
	- git push

bump:
	- python3 pythion/src/increase_version.py