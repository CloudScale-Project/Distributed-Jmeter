#
#  Copyright (c) 2015 XLAB d.o.o.
#  All rights reserved. This program and the accompanying materials
#  are made available under the terms of the Eclipse Public License v1.0
#  which accompanies this distribution, and is available at
#  http://www.eclipse.org/legal/epl-v10.html
#
import logging

class Logger:

    def __init__(self, filename):
        logging.basicConfig(filename=filename,level=logging.DEBUG)

    def log(self, msg, level=logging.DEBUG, append_to_last=False, fin=False):
        logging.log(level, msg)