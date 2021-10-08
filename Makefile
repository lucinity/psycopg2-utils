build:
	python -m build

publish-testpypi:
	twine upload --repository testpypi dist/*

publish-pypi:
	twine upload --repository pypi dist/*