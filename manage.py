#!/usr/bin/env python
from migrate.versioning.shell import main

if __name__ == '__main__':
    main(repository='repository', url='postgresql://admin:password@localhost:5432/tophealth', debug='False')
