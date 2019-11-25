.PHONY: build check clean

build:
	echo "Building..."
	python3 setup.py sdist bdist_wheel

check:
	echo "Running tests..."
	python3 -m unittest discover

clean:
	echo "Cleaning..."
	rm -rf __pycache__ *~ build dist *.egg-info
	rm -rf license_scanner/__pycache__
	rm -rf tests/__pycache__
