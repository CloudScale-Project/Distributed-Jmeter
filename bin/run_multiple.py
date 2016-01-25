#
#  Copyright (c) 2015 XLAB d.o.o.
#  All rights reserved. This program and the accompanying materials
#  are made available under the terms of the Eclipse Public License v1.0
#  which accompanies this distribution, and is available at
#  http://www.eclipse.org/legal/epl-v10.html
#
import os
import sys
import boto
import time
from run import run_test

def reboot_aws_frontends(config_path):
    cfg = boto.Config()
    cfg.load_from_path(os.path.abspath(config_path))

    instances_id = cfg.get('SHOWCASE', 'frontend_instances_id')
    access_key = cfg.get('SHOWCASE', 'aws_access_key_id')
    secret_key = cfg.get('SHOWCASE', 'aws_secret_access_key')
    region = cfg.get('AWS', 'region')

    conn = boto.ec2.connect_to_region(
            region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
    )
    reservations = conn.get_all_instances(filters={"tag:Name" : instances_id})
    instances = [i for r in reservations for i in r.instances]
    for instance in instances:
        instance.reboot()

    # wait 5 minutes after reboot so instances come available
    time.sleep(5*60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        infrastructure = sys.argv[1]
        config_path = sys.argv[2]
        scenario_path = sys.argv[3]
        num = sys.argv[4]

        results = []
        for i in xrange(int(num)):
            header = '###################\n' \
                    '# Running test %s #\n' \
                    '###################'

            print header % (i+1)

            results_path = run_test(sys.argv)
            print "Results for this test are in %s\n" % results_path
            results.append(results_path)

            if infrastructure == 'aws':
                reboot_aws_frontends(config_path)

        summary = '#######################' \
                  '# SUMMARY OF TESTS #' \
                  '#######################'
        for i, r in enumerate(results):
            print "Results for test %s are in: %s" % (i, r)

