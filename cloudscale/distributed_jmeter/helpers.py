#
#  Copyright (c) 2015 XLAB d.o.o.
#  All rights reserved. This program and the accompanying materials
#  are made available under the terms of the Eclipse Public License v1.0
#  which accompanies this distribution, and is available at
#  http://www.eclipse.org/legal/epl-v10.html
#
import os
import boto

def read_config(config_file):
    cfg = boto.Config()
    cfg.load_from_path(os.path.abspath(config_file))

    return cfg