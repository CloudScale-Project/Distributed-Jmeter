#!/usr/bin/python
import logging
import sys
import os
import shutil
from cloudscale.distributed_jmeter import run_test
from cloudscale.distributed_jmeter.logger import Logger
from cloudscale.distributed_jmeter.scripts import meet_sla_req

class MyLogger(Logger):

    def log(self, msg, level=logging.DEBUG, append_to_last=False, fin=False):
        print msg


if __name__ == "__main__":

    if len(sys.argv) > 1:
        infrastructure = sys.argv[1]
        config_path = sys.argv[2]
        scenario_path = sys.argv[3]
        logger = MyLogger("distributed_jmeter.log")

        results_path = run_test.run_test(infrastructure, config_path, scenario_path, "%s/results" % os.path.abspath(os.path.dirname(__file__)), logger)

        with open("%s/SLO_violations" % results_path, "w") as fp:
            output = meet_sla_req.check("%s/response-times-over-time.csv" % results_path)
            fp.write(output)

        shutil.copyfile('%s' % config_path, '%s/config.ini' % results_path)
        shutil.copyfile('%s' % scenario_path, '%s/scenario.jmx' % results_path)

        print "See results in %s" % results_path
    else:
        print """Usage: python run.py <aws|openstack> <path_to_config> <path_to_scenario>"""
