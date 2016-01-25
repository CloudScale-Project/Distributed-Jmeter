#
#  Copyright (c) 2015 XLAB d.o.o.
#  All rights reserved. This program and the accompanying materials
#  are made available under the terms of the Eclipse Public License v1.0
#  which accompanies this distribution, and is available at
#  http://www.eclipse.org/legal/epl-v10.html
#
import logging
import sys
import os
import shutil
from cloudscale.distributed_jmeter import run_test as _run_test
from cloudscale.distributed_jmeter.logger import Logger
from cloudscale.distributed_jmeter.scripts import meet_sla_req

class MyLogger(Logger):

    def log(self, msg, level=logging.DEBUG, append_to_last=False, fin=False):
        print msg

def run_test(argv):
    infrastructure = argv[1]
    config_path = argv[2]
    scenario_path = argv[3]
    logger = MyLogger("distributed_jmeter.log")

    results_path = _run_test.run_test(infrastructure, config_path, scenario_path, "%s/results" % os.path.abspath(os.path.dirname(__file__)), logger)

    with open("%s/SLO_violations" % results_path, "w") as fp:
        output = meet_sla_req.check("%s/response-times-over-time.csv" % results_path)
        fp.write(output)

    shutil.copyfile('%s' % config_path, '%s/config.ini' % results_path)
    shutil.copyfile('%s' % scenario_path, '%s/scenario.jmx' % results_path)

    return results_path

if __name__ == "__main__":

    if len(sys.argv) > 1:
        results_path = run_test(sys.argv)
        print "You can see results in %s" % results_path
    else:
        print """Usage: python run.py <aws|openstack> <path_to_config> <path_to_scenario>"""
