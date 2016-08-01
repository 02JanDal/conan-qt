PYTHONCMD=`which python3`

generate:
	${PYTHONCMD} generate.py -g

withouteverything:
	${PYTHONCMD} generate.py -e Qt5Everything

initial:
	${PYTHONCMD} generate.py

all: initial