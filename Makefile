format:
	- autoflake -ri --remove-all-unused-imports .
	- isort  --profile black .
	- black --target-version py310 .

commit:
	- git add .
	- python3 /media/WorkShared/packages/pythion/pythion/__init__.py make-commit -p no-version
	- git push

bump:
	- python3 pythion/src/increase_version.py