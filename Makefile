format:
	- autoflake -ri --remove-all-unused-imports pythion/src
	- isort  --profile black .
	- black --target-version py310 .

commit:
	- git add .
	- python3 /media/asaniczka/working/packages/pythion/pythion/__init__.py make-commit -ci "Ignore version bumps. This is done via a precommit hook. Also ignore any import removing. This is done automactially by autoflake. Not worthy of commit mention"
	- git push

bump:
	- python3 pythion/src/increase_version.py