.PHONY: doc

test:
	tox
doc:
	make -C doc html
clean:
	rm -rf build dist aiogreen.egg-info .tox
	make -C doc clean
